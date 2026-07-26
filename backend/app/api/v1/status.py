"""Health check and global status."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KGEdge, KGNode, MarketIndex, NewsArticle, Report

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        total = db.query(MarketIndex).count()
        return {"status": "healthy", "db": "connected", "marketCount": total}
    except Exception:
        return {"status": "unhealthy", "db": "disconnected"}


@router.get("/status")
def status(db: Session = Depends(get_db)):
    cat_counts = {}
    for row in db.query(NewsArticle.category, func.count(NewsArticle.id)).group_by(NewsArticle.category).all():
        cat_counts[row[0]] = row[1]
    return {
        "marketCount": db.query(MarketIndex).count(),
        "articleCount": db.query(NewsArticle).count(),
        "analyzedCount": db.query(NewsArticle).filter(NewsArticle.is_analyzed == True).count(),
        "nodeCount": db.query(KGNode).count(),
        "edgeCount": db.query(KGEdge).count(),
        "reportCount": db.query(Report).count(),
        "categoryCounts": cat_counts,
    }
