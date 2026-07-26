"""Pipeline API — trigger crawl, analysis, report generation."""
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import MarketIndex, MarketSnapshot, PipelineTask, PipelineStage
from app.utils import shanghai_now

router = APIRouter()


def _bg_session():
    """Create a fresh session for background tasks (request-scoped session is closed)."""
    return SessionLocal()


@router.post("/pipeline/crawl/news")
def pipeline_crawl_news(
    bg: BackgroundTasks,
    date_from: str = Query(""),
    date_to: str = Query(""),
    sources: str = Query(""),
    db: Session = Depends(get_db),
):
    task = PipelineTask(task_type="crawl_news")
    db.add(task)
    db.flush()
    task_id = str(task.id)
    db.commit()

    def _run():
        sess = _bg_session()
        try:
            t = sess.query(PipelineTask).filter(PipelineTask.id == task.id).first()
            from app.services.crawler import crawl_all_sources
            source_ids = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
            crawl_all_sources(sess, source_ids=source_ids)
            if t:
                t.status = "done"
                t.finished_at = shanghai_now()
                sess.commit()
        except Exception as e:
            if t:
                t.status = "failed"
                t.error_detail = str(e)
                sess.commit()
        finally:
            sess.close()

    bg.add_task(_run)
    return {"ok": True, "taskId": task_id, "message": "News crawl started"}


@router.post("/pipeline/crawl/market")
def pipeline_crawl_market(db: Session = Depends(get_db)):
    from app.services.market import fetch_all_market_data

    task = PipelineTask(task_type="crawl_market")
    db.add(task)
    db.commit()

    try:
        data = fetch_all_market_data()
        now = shanghai_now()
        updated = 0
        for item in data:
            existing = db.query(MarketIndex).filter(MarketIndex.symbol == item["symbol"]).first()
            if existing:
                existing.price = item["price"]
                existing.change = item["change"]
                existing.change_pct = item["change_pct"]
                existing.unit = item.get("unit") or existing.unit
                existing.source_url = item.get("source_url") or existing.source_url
                existing.updated_at = now
            else:
                db.add(MarketIndex(
                    symbol=item["symbol"], name=item["name"], exchange=item["exchange"],
                    category=item["category"], granularity=item["granularity"],
                    price=item["price"], change=item["change"], change_pct=item["change_pct"],
                    unit=item.get("unit", ""), source_url=item.get("source_url", ""),
                    updated_at=now,
                ))
            db.add(MarketSnapshot(
                symbol=item["symbol"], price=item["price"], change=item["change"],
                change_pct=item["change_pct"], snapshot_time=now, granularity=item["granularity"],
            ))
            updated += 1
        task.status = "done"
        task.total_items = updated
        task.finished_at = now
        db.commit()
        return {"ok": True, "count": updated}
    except Exception as e:
        task.status = "failed"
        task.error_detail = str(e)
        db.commit()
        return {"ok": False, "error": str(e)}


@router.post("/pipeline/analyze")
def pipeline_analyze(
    bg: BackgroundTasks,
    date_from: str = Query(""),
    date_to: str = Query(""),
    db: Session = Depends(get_db),
):
    task = PipelineTask(task_type="analyze")
    db.add(task)
    db.flush()
    task_id = str(task.id)
    db.commit()

    def _run():
        sess = _bg_session()
        try:
            t = sess.query(PipelineTask).filter(PipelineTask.id == task.id).first()
            from app.services.nlp.analyzer import run_analysis_pipeline
            df = datetime.fromisoformat(date_from) if date_from else None
            dt = datetime.fromisoformat(date_to) if date_to else None
            result = run_analysis_pipeline(sess, date_from=df, date_to=dt)
            if t:
                t.status = "done"
                t.total_items = result.get("analyzed", 0)
                t.finished_at = shanghai_now()
                sess.commit()

            # Always generate report — includes already-analyzed articles
            from app.services.report import generate_report
            now = shanghai_now()
            generate_report(sess, now - timedelta(days=1), now)
        except Exception as e:
            if t:
                t.status = "failed"
                t.error_detail = str(e)
                sess.commit()
        finally:
            sess.close()

    bg.add_task(_run)
    return {"ok": True, "taskId": task_id, "message": "Analysis started"}


@router.post("/pipeline/full")
def pipeline_full(
    bg: BackgroundTasks,
    date_from: str = Query(""),
    date_to: str = Query(""),
    sources: str = Query(""),
    db: Session = Depends(get_db),
):
    task = PipelineTask(task_type="full_pipeline")
    db.add(task)
    db.flush()
    task_id = str(task.id)
    db.commit()

    def _run():
        sess = _bg_session()
        try:
            t = sess.query(PipelineTask).filter(PipelineTask.id == task.id).first()
            from app.services.crawler import crawl_all_sources
            from app.services.nlp.analyzer import run_analysis_pipeline
            from app.services.report import generate_report
            source_ids = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
            crawl_all_sources(sess, source_ids=source_ids)
            df = datetime.fromisoformat(date_from) if date_from else None
            dt = datetime.fromisoformat(date_to) if date_to else None
            run_analysis_pipeline(sess, date_from=df, date_to=dt)
            now = shanghai_now()
            generate_report(sess, now - timedelta(days=1), now)
            if t:
                t.status = "done"
                t.finished_at = shanghai_now()
                sess.commit()
        except Exception as e:
            if t:
                t.status = "failed"
                t.error_detail = str(e)
                sess.commit()
        finally:
            sess.close()

    bg.add_task(_run)
    return {"ok": True, "taskId": task_id, "message": "Full pipeline started"}


@router.get("/pipeline/status")
def pipeline_status(db: Session = Depends(get_db)):
    from app.services.crawler import get_crawl_state
    from app.services.nlp.analyzer import get_pipeline_state
    return {"crawl": get_crawl_state(), "pipeline": get_pipeline_state()}


@router.get("/pipeline/tasks")
def pipeline_tasks(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db)):
    total = db.query(PipelineTask).count()
    tasks = db.query(PipelineTask).order_by(PipelineTask.started_at.desc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    return {
        "list": [{
            "id": str(t.id), "taskType": t.task_type, "status": t.status,
            "totalItems": t.total_items, "processedItems": t.processed_items,
            "errorCount": t.error_count,
            "startedAt": t.started_at.isoformat() if t.started_at else None,
            "finishedAt": t.finished_at.isoformat() if t.finished_at else None,
        } for t in tasks],
        "total": total, "page": page, "pageSize": page_size,
    }


@router.post("/pipeline/abort")
def pipeline_abort():
    from app.services.crawler import request_abort
    request_abort()
    return {"ok": True, "message": "Abort signal sent"}
