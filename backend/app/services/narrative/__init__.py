"""Narrative sentiment computation — keyword-based theme matching with regional aggregation."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import NarrativeTheme, NarrativeSentiment, NewsArticle, NewsAnalysis

logger = logging.getLogger("finkg.narrative")


def _week_start(dt: datetime) -> datetime:
    """Truncate a datetime to Monday 00:00:00 of its ISO week."""
    if dt is None:
        return None
    # Convert to naive for consistency (SQLite stores naive datetimes)
    if dt.tzinfo is not None:
        from datetime import timezone as _tz
        dt = dt.astimezone(_tz.utc).replace(tzinfo=None)
    day_of_week = dt.weekday()  # Monday=0
    ws = dt - timedelta(days=day_of_week)
    return ws.replace(hour=0, minute=0, second=0, microsecond=0)


def normalize_region(raw: str | None) -> str:
    """Normalize region strings to standardized codes: cn, us, eu, hk, jp, sg."""
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
        "gb": "eu", "uk": "eu", "united kingdom": "eu", "英国": "eu", "britain": "eu",
        "de": "eu", "germany": "eu", "德国": "eu",
        "fr": "eu", "france": "eu", "法国": "eu",
        "kr": "jp", "south korea": "jp", "korea": "jp", "韩国": "jp",
        "tw": "cn", "taiwan": "cn", "台湾": "cn",
    }
    return mapping.get(r, r)


def _build_match_text(article: NewsArticle, analysis: NewsAnalysis | None = None) -> str:
    """Build a single searchable text blob from article + analysis for keyword matching."""
    parts = [
        article.title or "",
        article.content or "",
    ]
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


def compute_narrative_sentiment(db: Session) -> dict[str, Any]:
    """
    Compute narrative sentiment by matching active theme keywords against analyzed articles.

    For each active NarrativeTheme:
      1. Filter NewsArticles + NewsAnalyses whose combined text matches any theme keyword.
      2. Group matches by ISO week-start and normalized region.
      3. Compute avg sentiment_score, positive/negative/neutral counts per group.
      4. Upsert results into the NarrativeSentiment table.

    Returns a stats dict.
    """
    themes = db.query(NarrativeTheme).filter(NarrativeTheme.is_active == True).all()
    if not themes:
        return {"ok": True, "themes_processed": 0, "rows_upserted": 0, "message": "No active themes"}

    # Load all analyzed articles with their analysis in one shot
    rows = (
        db.query(NewsArticle, NewsAnalysis)
        .join(NewsAnalysis, NewsArticle.id == NewsAnalysis.article_id)
        .filter(NewsArticle.is_analyzed == True)
        .all()
    )

    if not rows:
        return {"ok": True, "themes_processed": 0, "rows_upserted": 0, "message": "No analyzed articles found — run the analysis pipeline first"}

    # Pre-compute match texts so we don't rebuild them per theme
    article_data: list[tuple[NewsArticle, NewsAnalysis, str]] = []
    for article, analysis in rows:
        match_text = _build_match_text(article, analysis)
        article_data.append((article, analysis, match_text))

    total_upserted = 0

    for theme in themes:
        keywords: list[str] = theme.keywords or []
        if not keywords:
            continue

        # Normalize keywords to lowercase for case-insensitive matching
        kw_lower = [kw.lower() for kw in keywords]

        # Collect scores per (week_start, region)
        groups: dict[tuple[datetime, str], list[float]] = {}
        groups_labels: dict[tuple[datetime, str], list[str]] = {}

        for article, analysis, match_text in article_data:
            # Check if any keyword is present in the combined text
            text_lower = match_text.lower()
            if not any(kw in text_lower for kw in kw_lower):
                continue

            ts = article.published_at or article.crawled_at
            if ts is None:
                continue

            ws = _week_start(ts)
            region = normalize_region(article.region)

            key = (ws, region)
            if key not in groups:
                groups[key] = []
                groups_labels[key] = []

            groups[key].append(analysis.sentiment_score or 0.0)
            groups_labels[key].append(analysis.sentiment or "neutral")

        if not groups:
            continue

        # Upsert into NarrativeSentiment
        for (ws, region), scores in groups.items():
            avg_s = sum(scores) / len(scores) if scores else 0.0
            labels = groups_labels.get((ws, region), [])
            positive_count = sum(1 for lb in labels if lb == "bullish")
            negative_count = sum(1 for lb in labels if lb == "bearish")
            neutral_count = sum(1 for lb in labels if lb == "neutral")
            article_count = len(scores)

            existing = db.query(NarrativeSentiment).filter(
                NarrativeSentiment.theme_id == theme.id,
                NarrativeSentiment.week_start == ws,
                NarrativeSentiment.region == region,
            ).first()

            if existing:
                existing.avg_sentiment = round(avg_s, 4)
                existing.article_count = article_count
                existing.positive_count = positive_count
                existing.negative_count = negative_count
                existing.neutral_count = neutral_count
            else:
                db.add(NarrativeSentiment(
                    theme_id=theme.id,
                    week_start=ws,
                    region=region,
                    avg_sentiment=round(avg_s, 4),
                    article_count=article_count,
                    positive_count=positive_count,
                    negative_count=negative_count,
                    neutral_count=neutral_count,
                ))
            total_upserted += 1

    db.commit()
    logger.info(f"Narrative sentiment computed: {total_upserted} rows across {len(themes)} themes")

    return {
        "ok": True,
        "themes_processed": len(themes),
        "rows_upserted": total_upserted,
        "articles_total": len(article_data),
    }
