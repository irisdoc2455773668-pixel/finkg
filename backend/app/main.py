"""FinKG v5 — Financial Narrative Intelligence Platform."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base
from app.api.v1.router import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("finkg")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, seed default sources."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    # Seed default market data if empty
    from app.models import MarketIndex
    with SessionLocal() as db:
        if db.query(MarketIndex).count() == 0:
            _seed_market_data(db)
            logger.info("Market data seeded")
        # Seed default sources
        from app.models import NewsSource
        if db.query(NewsSource).count() == 0:
            _seed_sources(db)
            logger.info("News sources seeded")
        # Seed default narrative themes
        from app.models import NarrativeTheme
        if db.query(NarrativeTheme).count() == 0:
            _seed_themes(db)
            logger.info("Narrative themes seeded")

    yield
    logger.info("FinKG shutting down")


app = FastAPI(
    title="FinKG",
    version="5.0.0",
    description="Financial Narrative Intelligence Platform",
    lifespan=lifespan,
)

# CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def index():
    """SPA entry point for production (served by nginx in dev, this is fallback)."""
    return {"name": "FinKG API", "version": "5.0.0", "docs": "/docs"}


# ── Seed helpers ──

def _seed_market_data(db):
    """Seed 34 market indicators with initial values."""
    from datetime import datetime
    from app.utils import shanghai_now
    from app.services.market import META

    GRANULARITY_MAP = {
        "equity": "realtime", "fx": "realtime", "crypto": "realtime",
        "commodity": "daily", "bond": "daily", "rate": "daily",
        "inflation": "monthly", "employment": "monthly", "gdp": "quarterly",
        "pmi": "monthly", "risk": "daily",
    }
    indices = [
        ("SPX", "标普500指数", "NYSE", "equity", 5923.45, 12.30, 0.21),
        ("NDX", "纳斯达克综合", "NASDAQ", "equity", 21456.78, 89.45, 0.42),
        ("DAX", "德国DAX40", "XETRA", "equity", 23401.12, -45.67, -0.19),
        ("FTSE", "英国富时100", "LSE", "equity", 8756.34, 23.45, 0.27),
        ("N225", "日经225", "TSE", "equity", 39234.56, 156.78, 0.40),
        ("HSI", "恒生指数", "SEHK", "equity", 24321.09, -89.12, -0.37),
        ("SHCOMP", "上证综指", "SSE", "equity", 3421.56, 15.78, 0.46),
        ("A50", "富时中国A50", "SGX", "equity", 13876.54, 34.21, 0.25),
        ("EURUSD", "欧元/美元", "FOREX", "fx", 1.1215, 0.0023, 0.21),
        ("USDJPY", "美元/日元", "FOREX", "fx", 144.23, -0.45, -0.31),
        ("GBPUSD", "英镑/美元", "FOREX", "fx", 1.2812, 0.0015, 0.12),
        ("USDCNY", "美元/人民币", "FOREX", "fx", 7.2487, 0.0089, 0.12),
        ("DXY", "美元指数", "FOREX", "fx", 99.34, 0.12, 0.12),
        ("BRENT", "布伦特原油", "ICE", "commodity", 75.93, 0.45, 0.69),
        ("NATGAS", "天然气期货", "NYMEX", "commodity", 3.16, -0.08, -2.20),
        ("GOLD", "纽约黄金", "COMEX", "commodity", 4107.11, 23.40, 0.73),
        ("SILVER", "纽约白银", "COMEX", "commodity", 62.40, 0.56, 1.49),
        ("COPPER", "COMEX铜", "COMEX", "commodity", 6.28, -0.03, -0.58),
        ("BTC", "比特币/美元", "Crypto", "crypto", 64500.00, 500.00, 0.78),
        ("ETH", "以太坊/美元", "Crypto", "crypto", 1890.00, -30.00, -1.56),
        ("US2Y", "美国2年期国债", "Treasury", "bond", 3.95, -0.02, -0.50),
        ("US10Y", "美国10年期国债", "Treasury", "bond", 4.52, 0.01, 0.22),
        ("US3M", "美国3个月国债", "Treasury", "bond", 5.20, 0.00, 0.00),
        ("FEDFUNDS", "美国联邦基金利率", "Fed", "rate", 4.38, 0.00, 0.00),
        ("CN_LPR1Y", "中国LPR 1年期", "PBOC", "rate", 3.10, 0.00, 0.00),
        ("VIX", "VIX恐慌指数", "CBOE", "risk", 14.87, -0.34, -2.24),
        ("US_CPI", "美国CPI同比", "BLS", "inflation", 3.5, 0.00, 0.00),
        ("US_PPI", "美国PPI同比", "BLS", "inflation", 2.5, 0.00, 0.00),
        ("CN_CPI", "中国CPI同比", "NBS", "inflation", 0.5, 0.00, 0.00),
        ("CN_PPI", "中国PPI同比", "NBS", "inflation", -2.0, 0.00, 0.00),
        ("US_UNEMP", "美国失业率", "BLS", "employment", 4.1, 0.00, 0.00),
        ("US_GDP", "美国GDP增速", "BEA", "gdp", 2.8, 0.00, 0.00),
        ("CN_GDP", "中国GDP增速", "NBS", "gdp", 5.2, 0.00, 0.00),
        ("CN_PMI", "中国制造业PMI", "NBS", "pmi", 50.1, 0.00, 0.00),
    ]

    from app.models import MarketIndex
    now = shanghai_now()
    for i, (sym, name, exch, cat, price, chg, chg_pct) in enumerate(indices):
        gran = GRANULARITY_MAP.get(cat, "daily")
        # Read source_url and unit from the authoritative META dict
        meta = META.get(sym, (name, exch, cat, gran, "", ""))
        unit_from_meta = meta[4] if len(meta) > 4 else ""
        url_from_meta = meta[5] if len(meta) > 5 else ""
        db.add(MarketIndex(
            symbol=sym, name=name, exchange=exch, category=cat,
            granularity=gran, price=price, change=chg, change_pct=chg_pct,
            unit=unit_from_meta or "", source_url=url_from_meta or "",
            sort_order=i, updated_at=now,
        ))
    db.commit()


def _seed_sources(db):
    """Seed default news sources."""
    import json, os
    from app.models import NewsSource

    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "sources.json")
    if not os.path.exists(config_path):
        return
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for s in data.get("rss_sources", []):
        if not s.get("enabled", True):
            continue
        db.add(NewsSource(
            name=s["name"], url=s["url"], source_type="rss",
            language=s.get("lang", "zh"), region=s.get("region", "cn"),
            category=s.get("cat", "economy"),
            political_leaning=s.get("political_leaning", "state_media"),
            reliability_score=s.get("reliability", 0.7),
        ))
    for s in data.get("web_sources", []):
        if not s.get("enabled", True):
            continue
        db.add(NewsSource(
            name=s["name"], url=s["url"], source_type="web",
            language=s.get("lang", "zh"), region=s.get("region", "cn"),
            category=s.get("cat", "economy"),
            political_leaning=s.get("political_leaning", "financial_press"),
            reliability_score=s.get("reliability", 0.7),
            selector=s.get("selector", "a"), base_url=s.get("base_url", ""),
            encoding=s.get("encoding", "utf-8"), min_len=s.get("min_len", 12),
        ))
    db.commit()


def _seed_themes(db):
    """Seed default narrative themes."""
    from app.models import NarrativeTheme

    themes = [
        ("中美科技脱钩", "US-China technology decoupling narrative tracking",
         ["科技脱钩", "芯片制裁", "decoupling", "chip ban", "技术封锁", "CHIPS Act", "实体清单"]),
        ("中国房地产风险", "China real estate sector risk narrative",
         ["房地产", "恒大", "碧桂园", "万科", "保交楼", "去库存", "real estate", "property crisis"]),
        ("全球通胀与央行政策", "Global inflation and central bank policy divergence",
         ["通胀", "加息", "降息", "CPI", "inflation", "Fed", "ECB", "央行", "monetary policy"]),
        ("台海地缘政治", "Taiwan Strait geopolitical risk",
         ["台海", "台湾", "Taiwan", "两岸", "统一", "军演", "地缘"]),
        ("人工智能产业竞争", "AI industry competition and regulation",
         ["AI", "人工智能", "大模型", "ChatGPT", "DeepSeek", "GPU", "算力", "AGI"]),
        ("全球供应链重构", "Global supply chain restructuring",
         ["供应链", "近岸外包", "友岸外包", "supply chain", "reshoring", "制造业回流"]),
        ("能源转型与碳中和", "Energy transition and carbon neutrality",
         ["碳中和", "新能源", "光伏", "风电", "电动车", "EV", "carbon neutral", "green energy"]),
        ("人民币国际化", "RMB internationalization",
         ["人民币国际化", "跨境结算", "RMB", "SWIFT替代", "CIPS", "石油人民币"]),
    ]
    for name, desc, keywords in themes:
        db.add(NarrativeTheme(name=name, description=desc, keywords=keywords))
    db.commit()
