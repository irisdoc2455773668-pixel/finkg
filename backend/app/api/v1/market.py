"""Market data API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MarketIndex, MarketSnapshot

router = APIRouter()

CAT_LABELS = {
    "equity": "全球股指", "fx": "外汇市场", "commodity": "大宗商品", "crypto": "数字货币",
    "bond": "国债利率", "rate": "政策利率", "inflation": "通胀指标", "employment": "就业市场",
    "gdp": "经济增长", "pmi": "景气指数", "risk": "风险指标",
}


@router.get("/market/indicators")
def market_indicators(db: Session = Depends(get_db)):
    indices = db.query(MarketIndex).order_by(MarketIndex.sort_order, MarketIndex.symbol).all()
    by_cat: dict[str, list] = {}
    for idx in indices:
        by_cat.setdefault(idx.category, []).append({
            "symbol": idx.symbol, "name": idx.name, "exchange": idx.exchange,
            "category": idx.category, "granularity": idx.granularity,
            "price": idx.price, "change": idx.change, "changePct": idx.change_pct,
            "volume": idx.volume, "unit": idx.unit or "", "sourceUrl": idx.source_url or "",
            "updatedAt": idx.updated_at.isoformat() if idx.updated_at else None,
        })
    cats = ["equity", "fx", "commodity", "crypto", "bond", "rate", "inflation", "employment", "gdp", "pmi", "risk"]
    return {
        "categories": {CAT_LABELS.get(c, c): by_cat.get(c, []) for c in cats if c in by_cat},
        "total": len(indices),
    }


@router.get("/market/snapshots")
def market_snapshots(
    symbols: str = Query("SPX"), days: int = Query(30),
    granularity: str = Query(""),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timedelta
    sym_list = [x.strip() for x in symbols.split(",")]
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = db.query(MarketSnapshot).filter(
        MarketSnapshot.symbol.in_(sym_list),
        MarketSnapshot.snapshot_time >= cutoff,
    )
    if granularity:
        q = q.filter(MarketSnapshot.granularity == granularity)
    rows = q.order_by(MarketSnapshot.snapshot_time.asc()).all()
    return {
        "list": [{"symbol": r.symbol, "price": r.price, "change": r.change,
                   "changePct": r.change_pct, "granularity": r.granularity,
                   "snapshotTime": r.snapshot_time.isoformat() if r.snapshot_time else None}
                  for r in rows],
    }


@router.get("/market/summary")
def market_summary(db: Session = Depends(get_db)):
    """Market breadth summary."""
    eq_symbols = ["SPX", "NDX", "DAX", "FTSE", "N225", "HSI", "SHCOMP", "A50"]
    eq = db.query(MarketIndex).filter(MarketIndex.symbol.in_(eq_symbols)).all()
    up = sum(1 for r in eq if r.change_pct and r.change_pct > 0)
    down = sum(1 for r in eq if r.change_pct and r.change_pct < 0)
    vix = db.query(MarketIndex).filter(MarketIndex.symbol == "VIX").first()
    return {
        "breadth": {"up": up, "down": down, "total": len(eq)},
        "vix": vix.price if vix else None,
    }
