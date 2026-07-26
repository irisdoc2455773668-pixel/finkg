"""News API — CRUD, search, by-entity."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NewsAnalysis, NewsArticle
from app.schemas import PaginatedResponse

router = APIRouter()


@router.get("/news")
def news_list(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200, alias="pageSize"),
    category: str = Query(""), source_name: str = Query("", alias="source"),
    sentiment: str = Query(""), risk_level: str = Query("", alias="riskLevel"),
    date_from: str = Query("", alias="dateFrom"), date_to: str = Query("", alias="dateTo"),
    region: str = Query(""),
    db: Session = Depends(get_db),
):
    q = db.query(NewsArticle)
    if category:
        q = q.filter(NewsArticle.category == category)
    if source_name:
        q = q.filter(NewsArticle.source_name == source_name)
    if region:
        q = q.filter(NewsArticle.region == region)
    if sentiment or risk_level:
        sub = db.query(NewsAnalysis.article_id)
        if sentiment:
            sub = sub.filter(NewsAnalysis.sentiment == sentiment)
        if risk_level:
            sub = sub.filter(NewsAnalysis.risk_level == risk_level)
        aid_list = [r[0] for r in sub.all()]
        if aid_list:
            q = q.filter(NewsArticle.id.in_(aid_list))
        else:
            q = q.filter(NewsArticle.id == None)
    if date_from:
        from datetime import datetime
        try:
            q = q.filter(NewsArticle.crawled_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        from datetime import datetime
        try:
            q = q.filter(NewsArticle.crawled_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    total = q.count()
    rows = q.order_by(NewsArticle.crawled_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    article_list = []
    for r in rows:
        analysis = db.query(NewsAnalysis).filter(NewsAnalysis.article_id == r.id).first()
        article_list.append({
            "id": str(r.id), "title": r.title, "sourceName": r.source_name, "category": r.category,
            "url": r.url, "region": r.region,
            "publishedAt": r.published_at.isoformat() if r.published_at else None,
            "isAnalyzed": r.is_analyzed,
            "sentiment": analysis.sentiment if analysis else None,
            "sentimentScore": analysis.sentiment_score if analysis else None,
            "riskLevel": analysis.risk_level if analysis else None,
            "summary": (analysis.summary or "")[:200] if analysis else None,
            "tags": analysis.tags if analysis else None,
        })

    return {"list": article_list, "total": total, "page": page, "pageSize": page_size}


@router.get("/news/{article_id}")
def news_detail(article_id: str, db: Session = Depends(get_db)):
    article = db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
    if not article:
        return {"found": False}
    analysis = db.query(NewsAnalysis).filter(NewsAnalysis.article_id == article.id).first()
    return {"found": True, "article": {
        "id": str(article.id), "title": article.title, "content": article.content,
        "sourceName": article.source_name, "category": article.category,
        "url": article.url, "region": article.region, "language": article.language,
        "publishedAt": article.published_at.isoformat() if article.published_at else None,
        "crawledAt": article.crawled_at.isoformat() if article.crawled_at else None,
        "analysis": {
            "sentiment": analysis.sentiment, "sentimentScore": analysis.sentiment_score,
            "riskLevel": analysis.risk_level, "summary": analysis.summary,
            "tags": analysis.tags, "entities": analysis.entities,
            "engine": analysis.analysis_engine,
        } if analysis else None,
    }}


@router.delete("/news/{article_id}")
def delete_article(article_id: str, db: Session = Depends(get_db)):
    """Delete a news article and its associated analysis (cascade)."""
    article = db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
    if not article:
        return {"deleted": False, "detail": "Article not found"}
    db.delete(article)
    db.commit()
    return {"deleted": True, "id": article_id}


@router.get("/news/by-entity")
def news_by_entity(entity: str = Query(""), limit: int = Query(20), db: Session = Depends(get_db)):
    rows = db.query(NewsArticle).filter(
        (NewsArticle.title.contains(entity)) | (NewsArticle.content.contains(entity))
    ).order_by(NewsArticle.crawled_at.desc()).limit(limit).all()
    return {"entity": entity, "list": [
        {"id": str(r.id), "title": r.title, "sourceName": r.source_name, "category": r.category, "url": r.url}
        for r in rows
    ]}
