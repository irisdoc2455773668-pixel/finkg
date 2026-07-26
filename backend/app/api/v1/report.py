"""Reports API."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Report

router = APIRouter()


@router.get("/reports")
def report_list(
    report_type: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Report)
    if report_type:
        q = q.filter(Report.report_type == report_type)
    if date_from:
        try:
            q = q.filter(Report.period_start >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(Report.period_end <= datetime.fromisoformat(date_to))
        except ValueError:
            pass
    total = q.count()
    rows = q.order_by(Report.period_start.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "list": [{
            "id": str(r.id), "reportType": r.report_type,
            "periodStart": r.period_start.isoformat() if r.period_start else None,
            "periodEnd": r.period_end.isoformat() if r.period_end else None,
            "headline": r.headline, "marketSentiment": r.market_sentiment,
            "articleCount": r.article_count, "createdAt": r.created_at.isoformat() if r.created_at else None,
        } for r in rows],
        "total": total, "page": page, "pageSize": page_size,
    }


@router.get("/reports/latest")
def report_latest(db: Session = Depends(get_db)):
    """Must be BEFORE /reports/{report_id} to avoid 'latest' being treated as an ID."""
    r = db.query(Report).order_by(Report.period_start.desc()).first()
    if not r:
        return {"found": False}
    return {"found": True, "report": {
        "id": str(r.id), "reportType": r.report_type,
        "periodStart": r.period_start.isoformat() if r.period_start else None,
        "periodEnd": r.period_end.isoformat() if r.period_end else None,
        "headline": r.headline, "executiveSummary": r.executive_summary,
        "sections": r.sections, "marketSentiment": r.market_sentiment,
        "articleCount": r.article_count,
    }}


@router.get("/reports/{report_id}")
def report_detail(report_id: str, db: Session = Depends(get_db)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        return {"found": False}
    return {"found": True, "report": {
        "id": str(r.id), "reportType": r.report_type,
        "periodStart": r.period_start.isoformat() if r.period_start else None,
        "periodEnd": r.period_end.isoformat() if r.period_end else None,
        "headline": r.headline, "executiveSummary": r.executive_summary,
        "sections": r.sections, "marketSentiment": r.market_sentiment,
        "articleCount": r.article_count, "engine": r.engine,
    }}


@router.post("/reports/generate-ai")
def report_generate_ai(
    date_from: str = Query(""),
    date_to: str = Query(""),
    db: Session = Depends(get_db),
):
    """Generate a professional AI-powered report using multi-agent LLM synthesis."""
    from datetime import datetime, timedelta
    from app.models import NewsAnalysis, NewsArticle, MarketIndex
    from app.services.llm.report_agent import generate_ai_report
    from app.services.graph import get_graph_stats

    # Parse date range
    df = datetime.fromisoformat(date_from) if date_from else datetime.utcnow() - timedelta(days=7)
    dt = datetime.fromisoformat(date_to) if date_to else datetime.utcnow()

    # Load articles
    articles = (
        db.query(NewsArticle, NewsAnalysis)
        .join(NewsAnalysis, NewsArticle.id == NewsAnalysis.article_id)
        .filter(NewsArticle.crawled_at >= df, NewsArticle.crawled_at <= dt)
        .order_by(NewsArticle.crawled_at.desc())
        .limit(60)
        .all()
    )
    if not articles:
        articles = (
            db.query(NewsArticle, NewsAnalysis)
            .join(NewsAnalysis, NewsArticle.id == NewsAnalysis.article_id)
            .order_by(NewsArticle.crawled_at.desc())
            .limit(60)
            .all()
        )

    if not articles:
        return {"ok": False, "error": "没有可分析的资讯数据，请先抓取新闻"}

    articles_json = [{
        "title": a.title, "category": a.category, "source": a.source_name,
        "region": a.region, "sentiment": n.sentiment, "tags": n.tags,
        "summary": (n.summary or "")[:200],
    } for a, n in articles]

    # Market data
    indices = db.query(MarketIndex).order_by(MarketIndex.category, MarketIndex.symbol).all()
    market_snapshot: dict[str, list] = {}
    for idx in indices:
        market_snapshot.setdefault(idx.category, []).append({
            "symbol": idx.symbol, "name": idx.name, "price": idx.price,
            "change": idx.change, "change_pct": idx.change_pct,
        })

    # KG summary
    kg_summary = get_graph_stats(db)
    date_range = f"{df.strftime('%Y-%m-%d')} 至 {dt.strftime('%Y-%m-%d')}"

    # Call AI
    result, error = generate_ai_report(db, articles_json, market_snapshot, kg_summary, date_range)

    if error:
        return {"ok": False, "error": error}

    # Save report
    report = Report(
        report_type="daily",
        period_start=df, period_end=dt,
        headline=result["headline"],
        executive_summary=result["executive_summary"],
        sections=result["sections"],
        market_sentiment="ai",
        article_count=len(articles),
        total_tokens=result.get("tokens_used", 0),
        engine="ai",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "ok": True,
        "report": {
            "id": str(report.id), "reportType": report.report_type,
            "periodStart": report.period_start.isoformat() if report.period_start else None,
            "periodEnd": report.period_end.isoformat() if report.period_end else None,
            "headline": report.headline, "executiveSummary": report.executive_summary,
            "sections": report.sections, "marketSentiment": report.market_sentiment,
            "articleCount": report.article_count, "engine": "ai",
        },
    }
