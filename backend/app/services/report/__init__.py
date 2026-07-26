"""Report generator — market-data-aware daily/weekly synthesis."""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import MarketIndex, NewsAnalysis, NewsArticle, Report
from app.utils import shanghai_now

logger = logging.getLogger("finkg.report")


def generate_report(db: Session, date_from: datetime, date_to: datetime,
                    report_type: str = "daily") -> dict:
    """Generate a structured report for the given time period."""
    # Load analyzed articles in period
    articles = (
        db.query(NewsArticle, NewsAnalysis)
        .join(NewsAnalysis, NewsArticle.id == NewsAnalysis.article_id)
        .filter(NewsArticle.crawled_at >= date_from, NewsArticle.crawled_at <= date_to)
        .all()
    )
    if not articles:
        articles = (
            db.query(NewsArticle, NewsAnalysis)
            .join(NewsAnalysis, NewsArticle.id == NewsAnalysis.article_id)
            .order_by(NewsArticle.crawled_at.desc())
            .limit(80)
            .all()
        )

    if not articles:
        return {"ok": False, "reason": "No analyzed articles found"}

    article_list = [{"article": a, "analysis": n} for a, n in articles]

    # Sentiment stats
    sentiments = [x["analysis"].sentiment for x in article_list if x["analysis"].sentiment]
    bullish = sentiments.count("bullish")
    bearish = sentiments.count("bearish")
    news_sentiment = "bullish" if bullish > bearish else ("bearish" if bearish > bullish else "neutral")

    # Market data
    indices = db.query(MarketIndex).order_by(MarketIndex.category, MarketIndex.symbol).all()
    market_snap: dict[str, list] = {}
    for idx in indices:
        market_snap.setdefault(idx.category, []).append({
            "symbol": idx.symbol, "name": idx.name, "price": idx.price,
            "change": idx.change, "change_pct": idx.change_pct, "unit": idx.unit,
        })

    # Market breadth
    eq = market_snap.get("equity", [])
    up = sum(1 for r in eq if r["change_pct"] > 0)
    down = sum(1 for r in eq if r["change_pct"] < 0)

    # Markets section
    markets_section = _build_markets_section(market_snap, up, down)

    # Category sections
    by_cat: dict[str, list] = {}
    for item in article_list:
        cat = item["article"].category or "economy"
        by_cat.setdefault(cat, []).append(item)

    sections = {}
    for cat in ["economy", "politics", "business", "technology", "culture", "society"]:
        items = by_cat.get(cat, [])
        sections[cat] = _build_section(items)

    # Top entities
    tags_list = [x["analysis"].tags for x in article_list]
    counter: Counter = Counter()
    for tags in tags_list:
        if tags:
            for t in str(tags).split(","):
                t = t.strip()
                if t:
                    counter[t] += 1
    top_entities = counter.most_common(8)

    # Headline
    headline = f"{date_from.strftime('%m/%d')}-{date_to.strftime('%m/%d')} 宏观{report_type}报告"
    if top_entities:
        headline += f" | {'·'.join(e for e,_ in top_entities[:3])}"

    # Executive summary
    exec_summary = _build_exec_summary(article_list, market_snap, up, down, news_sentiment, top_entities)

    # Upsert report
    day_start = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
    existing = db.query(Report).filter(
        Report.report_type == report_type,
        Report.period_start == day_start,
    ).first()

    report_data = {
        "report_type": report_type, "period_start": day_start, "period_end": date_to,
        "headline": headline[:500], "executive_summary": exec_summary,
        "sections": {**sections, "markets": markets_section},
        "market_sentiment": news_sentiment, "article_count": len(article_list),
        "engine": "rule",
    }

    if existing:
        for k, v in report_data.items():
            setattr(existing, k, v)
    else:
        db.add(Report(**report_data))
    db.commit()

    return {"ok": True, "headline": headline[:100], "articles": len(article_list),
            "sentiment": news_sentiment, "breadth": {"up": up, "down": down}}


def _build_markets_section(snap: dict, up: int, down: int) -> str:
    lines = [f"全球股指{up}涨{down}跌。"]
    eq = snap.get("equity", [])
    if eq:
        sorted_eq = sorted(eq, key=lambda x: abs(x["change_pct"]), reverse=True)
        lines.append("主要变动：" + "；".join(
            f"{r['name']} {r['price']:,.2f} {'▲' if r['change_pct']>=0 else '▼'}{r['change_pct']:+.2f}%"
            for r in sorted_eq[:5]))
    fx = snap.get("fx", [])
    if fx:
        lines.append("【外汇】" + "；".join(f"{r['name']} {r['price']:.4f}" for r in fx[:4]))
    comm = snap.get("commodity", [])
    if comm:
        lines.append("【大宗商品】" + "；".join(f"{r['name']} {r['price']:.2f}" for r in comm))
    vix = next((r for r in snap.get("risk", []) if r["symbol"] == "VIX"), None)
    if vix:
        label = "低位平稳" if vix["price"] < 15 else ("温和波动" if vix["price"] < 20 else "恐慌升温")
        lines.append(f"VIX {vix['price']:.2f}（{label}）")
    return "\n".join(lines)


def _build_section(items: list[dict]) -> str:
    if not items:
        return ""
    lines = []
    seen = set()
    for it in items[:15]:
        summary = (it["analysis"].summary or it["article"].title or "").strip()[:200]
        key = summary[:30]
        if key not in seen and summary:
            seen.add(key)
            sentiment = it["analysis"].sentiment or "neutral"
            emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}.get(sentiment, "")
            lines.append(f"{emoji} {summary}")
    return "\n".join(lines)


def _build_exec_summary(articles: list, snap: dict, up: int, down: int,
                         sentiment: str, top_entities: list) -> str:
    parts = []
    eq = snap.get("equity", [])
    if eq:
        parts.append(f"全球股指{up}涨{down}跌。")
    if top_entities:
        parts.append(f"资讯焦点集中在{'、'.join(e for e,_ in top_entities[:4])}等主题。")
    parts.append(f"综合情绪{'偏多' if sentiment == 'bullish' else ('偏空' if sentiment == 'bearish' else '中性')}。")
    vix = next((r for r in snap.get("risk", []) if r["symbol"] == "VIX"), None)
    if vix:
        parts.append(f"VIX {vix['price']:.1f}，{'市场波动温和' if vix['price'] < 20 else '避险情绪升温'}。")
    return " ".join(parts)
