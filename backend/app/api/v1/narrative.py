"""Narrative analysis API — theme tracking, sentiment divergence, computation."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NarrativeTheme, NarrativeSentiment, NewsArticle, NewsAnalysis

router = APIRouter()


class ThemeCreate(BaseModel):
    name: str
    description: str = ""
    keywords: list[str] = []


# ── Helpers ──

def _normalize_region(raw: str | None) -> str:
    """Normalize region to standard code: cn, us, eu, hk, jp, sg."""
    if not raw:
        return "cn"
    r = raw.lower().strip()
    mapping = {
        "cn": "cn", "china": "cn", "中国": "cn",
        "us": "us", "usa": "us", "united states": "us", "美国": "us", "america": "us",
        "eu": "eu", "europe": "eu", "european union": "eu", "欧洲": "eu", "欧盟": "eu",
        "hk": "hk", "hong kong": "hk", "香港": "hk",
        "jp": "jp", "japan": "jp", "日本": "jp",
        "sg": "sg", "singapore": "sg", "新加坡": "sg",
        "gb": "eu", "uk": "eu", "united kingdom": "eu", "英国": "eu",
        "de": "eu", "germany": "eu", "德国": "eu",
        "fr": "eu", "france": "eu", "法国": "eu",
        "kr": "jp", "south korea": "jp", "korea": "jp", "韩国": "jp",
        "tw": "cn", "taiwan": "cn", "台湾": "cn",
    }
    return mapping.get(r, r)


def _build_match_text(article: NewsArticle, analysis: NewsAnalysis | None = None) -> str:
    """Build a text blob from article and its analysis for keyword searching."""
    parts = [article.title or "", article.content or ""]
    if analysis is not None:
        parts.append(analysis.tags or "")
        if analysis.entities:
            ent = analysis.entities
            if isinstance(ent, dict):
                for vals in ent.values():
                    if isinstance(vals, list):
                        parts.append(" ".join(str(v) for v in vals))
            elif isinstance(ent, list):
                parts.append(" ".join(str(v) for v in ent))
    return " ".join(parts)


def _compute_divergence_from_analyses(db: Session) -> list[dict[str, Any]]:
    """
    Fallback: compute sentiment divergence directly from NewsAnalysis + NewsArticle
    when NarrativeSentiment table has no data yet.

    Returns the same list shape as the normal divergence endpoint.
    """
    themes = db.query(NarrativeTheme).filter(NarrativeTheme.is_active == True).all()
    if not themes:
        return []

    rows = (
        db.query(NewsArticle, NewsAnalysis)
        .join(NewsAnalysis, NewsArticle.id == NewsAnalysis.article_id)
        .filter(NewsArticle.is_analyzed == True)
        .all()
    )

    if not rows:
        return []

    # Pre-build match texts
    match_data: list[tuple[NewsArticle, NewsAnalysis, str]] = []
    for article, analysis in rows:
        match_data.append((article, analysis, _build_match_text(article, analysis)))

    result: list[dict[str, Any]] = []

    for theme in themes:
        keywords: list[str] = theme.keywords or []
        if not keywords:
            continue

        kw_lower = [kw.lower() for kw in keywords]

        # Collect scores by normalized region
        region_scores: dict[str, list[float]] = {}

        for article, analysis, match_text in match_data:
            text_lower = match_text.lower()
            if not any(kw in text_lower for kw in kw_lower):
                continue

            region = _normalize_region(article.region)
            if region not in region_scores:
                region_scores[region] = []
            region_scores[region].append(analysis.sentiment_score or 0.0)

        # Build per-region stats
        by_region: dict[str, dict[str, Any]] = {}
        for region, scores in region_scores.items():
            avg_s = sum(scores) / len(scores) if scores else 0.0
            by_region[region] = {
                "avg_sentiment": round(avg_s, 4),
                "article_count": len(scores),
            }

        cn_sentiment = by_region.get("cn", {}).get("avg_sentiment", 0)
        us_sentiment = by_region.get("us", {}).get("avg_sentiment", 0)
        divergence = abs(cn_sentiment - us_sentiment) if "cn" in by_region and "us" in by_region else 0

        result.append({
            "themeId": str(theme.id),
            "themeName": theme.name,
            "cnSentiment": cn_sentiment,
            "usSentiment": us_sentiment,
            "divergence": round(divergence, 3),
            "regions": by_region,
        })

    result.sort(key=lambda x: -x["divergence"])
    return result


# ── Theme CRUD ──

@router.get("/narrative/themes")
def narrative_themes(db: Session = Depends(get_db)):
    themes = db.query(NarrativeTheme).filter(NarrativeTheme.is_active == True).all()
    return {"list": [{
        "id": str(t.id), "name": t.name, "description": t.description,
        "keywords": t.keywords, "createdAt": t.created_at.isoformat() if t.created_at else None,
    } for t in themes]}


@router.post("/narrative/themes")
def narrative_theme_create(body: ThemeCreate, db: Session = Depends(get_db)):
    existing = db.query(NarrativeTheme).filter(NarrativeTheme.name == body.name).first()
    if existing:
        return {"ok": False, "error": f"Theme '{body.name}' already exists"}
    theme = NarrativeTheme(name=body.name, description=body.description, keywords=body.keywords)
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return {"ok": True, "theme": {"id": str(theme.id), "name": theme.name}}


@router.delete("/narrative/themes/{theme_id}")
def narrative_theme_delete(theme_id: str, db: Session = Depends(get_db)):
    theme = db.query(NarrativeTheme).filter(NarrativeTheme.id == theme_id).first()
    if not theme:
        return {"ok": False}
    theme.is_active = False
    db.commit()
    return {"ok": True}


# ── Sentiment & Divergence ──

@router.get("/narrative/themes/{theme_id}/sentiment")
def narrative_theme_sentiment(theme_id: str, db: Session = Depends(get_db)):
    sentiments = db.query(NarrativeSentiment).filter(
        NarrativeSentiment.theme_id == theme_id
    ).order_by(NarrativeSentiment.week_start.asc()).all()
    return {
        "list": [{
            "weekStart": s.week_start.isoformat() if s.week_start else None,
            "region": s.region, "avgSentiment": s.avg_sentiment,
            "articleCount": s.article_count,
            "positiveCount": s.positive_count,
            "negativeCount": s.negative_count,
            "neutralCount": s.neutral_count,
        } for s in sentiments],
    }


@router.get("/narrative/divergence")
def narrative_divergence(db: Session = Depends(get_db)):
    """
    Compute CN vs non-CN sentiment divergence per theme.

    Uses pre-computed NarrativeSentiment rows when available (fast path);
    falls back to direct NewsAnalysis query when the table is empty so the
    frontend chart shows data immediately after running the analysis pipeline.
    """
    from sqlalchemy import func

    # Check whether pre-computed sentiment data exists
    sentiment_count = db.query(NarrativeSentiment).count()

    if sentiment_count > 0:
        # ── Fast path: use NarrativeSentiment table ──
        themes = db.query(NarrativeTheme).filter(NarrativeTheme.is_active == True).all()
        result = []
        for theme in themes:
            rows = db.query(
                NarrativeSentiment.region,
                func.avg(NarrativeSentiment.avg_sentiment).label("avg_s"),
                func.sum(NarrativeSentiment.article_count).label("total"),
            ).filter(NarrativeSentiment.theme_id == theme.id).group_by(
                NarrativeSentiment.region
            ).all()
            by_region = {r[0]: {"avg_sentiment": float(r[1] or 0), "article_count": int(r[2] or 0)} for r in rows}
            cn_sentiment = by_region.get("cn", {}).get("avg_sentiment", 0)
            us_sentiment = by_region.get("us", {}).get("avg_sentiment", 0)
            divergence = abs(cn_sentiment - us_sentiment) if by_region.get("cn") and by_region.get("us") else 0
            result.append({
                "themeId": str(theme.id), "themeName": theme.name,
                "cnSentiment": cn_sentiment, "usSentiment": us_sentiment,
                "divergence": round(divergence, 3),
                "regions": by_region,
            })
        result.sort(key=lambda x: -x["divergence"])
        return {"list": result, "source": "computed"}
    else:
        # ── Fallback: compute directly from news_analyses ──
        return {"list": _compute_divergence_from_analyses(db), "source": "fallback"}


# ── Computation ──

@router.post("/narrative/compute")
def narrative_compute(db: Session = Depends(get_db)):
    """
    Trigger narrative sentiment computation.

    Matches all active theme keywords against analyzed articles, groups by
    week and region, then upserts results into the NarrativeSentiment table.
    Call this after running the analysis pipeline to populate sentiment data.
    """
    from app.services.narrative import compute_narrative_sentiment
    try:
        stats = compute_narrative_sentiment(db)
        return stats
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/narrative/compute/run")
def narrative_compute_run(db: Session = Depends(get_db)):
    """Alias for POST /narrative/compute (used by the frontend Run button)."""
    from app.services.narrative import compute_narrative_sentiment
    try:
        stats = compute_narrative_sentiment(db)
        return stats
    except Exception as e:
        return {"ok": False, "error": str(e)}
