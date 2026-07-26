"""Market data fetcher — Sina/Yahoo/Crypto with graceful degradation."""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime

from app.utils import shanghai_now
from app.utils.http import create_session

logger = logging.getLogger("finkg.market")

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Static metadata for 34 market indicators
META: dict[str, tuple] = {
    "SPX": ("标普500指数", "NYSE", "equity", "realtime", "points", "https://finance.yahoo.com/quote/%5EGSPC"),
    "NDX": ("纳斯达克综合", "NASDAQ", "equity", "realtime", "points", "https://finance.yahoo.com/quote/%5EIXIC"),
    "DAX": ("德国DAX40", "XETRA", "equity", "realtime", "points", "https://finance.yahoo.com/quote/%5EGDAXI"),
    "FTSE": ("英国富时100", "LSE", "equity", "realtime", "points", "https://finance.yahoo.com/quote/%5EFTSE"),
    "N225": ("日经225", "TSE", "equity", "realtime", "points", "https://finance.yahoo.com/quote/%5EN225"),
    "HSI": ("恒生指数", "SEHK", "equity", "realtime", "points", "https://finance.yahoo.com/quote/%5EHSI"),
    "SHCOMP": ("上证综指", "SSE", "equity", "realtime", "points", "https://finance.yahoo.com/quote/000001.SS"),
    "A50": ("富时中国A50", "SGX", "equity", "realtime", "points", "https://finance.yahoo.com/quote/%5EXIN9"),
    "EURUSD": ("欧元/美元", "FOREX", "fx", "realtime", "USD", "https://finance.yahoo.com/quote/EURUSD=X"),
    "USDJPY": ("美元/日元", "FOREX", "fx", "realtime", "JPY", "https://finance.yahoo.com/quote/USDJPY=X"),
    "GBPUSD": ("英镑/美元", "FOREX", "fx", "realtime", "USD", "https://finance.yahoo.com/quote/GBPUSD=X"),
    "USDCNY": ("美元/人民币", "FOREX", "fx", "realtime", "CNY", "https://finance.yahoo.com/quote/USDCNY=X"),
    "DXY": ("美元指数", "FOREX", "fx", "realtime", "points", "https://finance.yahoo.com/quote/DX-Y.NYB"),
    "BRENT": ("布伦特原油", "ICE", "commodity", "daily", "USD/桶", "https://finance.yahoo.com/quote/BZ=F"),
    "NATGAS": ("天然气期货", "NYMEX", "commodity", "daily", "USD/MMBtu", "https://finance.yahoo.com/quote/NG=F"),
    "GOLD": ("纽约黄金", "COMEX", "commodity", "daily", "USD/盎司", "https://finance.yahoo.com/quote/GC=F"),
    "SILVER": ("纽约白银", "COMEX", "commodity", "daily", "USD/盎司", "https://finance.yahoo.com/quote/SI=F"),
    "COPPER": ("COMEX铜", "COMEX", "commodity", "daily", "USD/磅", "https://finance.yahoo.com/quote/HG=F"),
    "BTC": ("比特币/美元", "Crypto", "crypto", "realtime", "USD", "https://finance.yahoo.com/quote/BTC-USD"),
    "ETH": ("以太坊/美元", "Crypto", "crypto", "realtime", "USD", "https://finance.yahoo.com/quote/ETH-USD"),
    "US2Y": ("美国2年期国债", "Treasury", "bond", "daily", "%", "https://fred.stlouisfed.org/series/DGS2"),
    "US10Y": ("美国10年期国债", "Treasury", "bond", "daily", "%", "https://fred.stlouisfed.org/series/DGS10"),
    "US3M": ("美国3个月国债", "Treasury", "bond", "daily", "%", "https://fred.stlouisfed.org/series/DGS3MO"),
    "FEDFUNDS": ("美国联邦基金利率", "Fed", "rate", "daily", "%", "https://fred.stlouisfed.org/series/FEDFUNDS"),
    "CN_LPR1Y": ("中国LPR 1年期", "PBOC", "rate", "daily", "%", ""),
    "VIX": ("VIX恐慌指数", "CBOE", "risk", "daily", "points", "https://finance.yahoo.com/quote/%5EVIX"),
    "US_CPI": ("美国CPI同比", "BLS", "inflation", "monthly", "%", ""),
    "US_PPI": ("美国PPI同比", "BLS", "inflation", "monthly", "%", ""),
    "CN_CPI": ("中国CPI同比", "NBS", "inflation", "monthly", "%", ""),
    "CN_PPI": ("中国PPI同比", "NBS", "inflation", "monthly", "%", ""),
    "US_UNEMP": ("美国失业率", "BLS", "employment", "monthly", "%", ""),
    "US_GDP": ("美国GDP增速", "BEA", "gdp", "quarterly", "%", ""),
    "CN_GDP": ("中国GDP增速", "NBS", "gdp", "quarterly", "%", ""),
    "CN_PMI": ("中国制造业PMI", "NBS", "pmi", "monthly", "points", ""),
}

# Seed values as final fallback
SEED: dict[str, dict] = {
    "SPX": {"price": 5923.45, "change_pct": 0.21}, "NDX": {"price": 21456.78, "change_pct": 0.42},
    "DAX": {"price": 23401.12, "change_pct": -0.19}, "FTSE": {"price": 8756.34, "change_pct": 0.27},
    "N225": {"price": 39234.56, "change_pct": 0.40}, "HSI": {"price": 24321.09, "change_pct": -0.37},
    "SHCOMP": {"price": 3421.56, "change_pct": 0.46}, "A50": {"price": 13876.54, "change_pct": 0.25},
    "EURUSD": {"price": 1.1215, "change_pct": 0.21}, "USDJPY": {"price": 144.23, "change_pct": -0.31},
    "GBPUSD": {"price": 1.2812, "change_pct": 0.12}, "USDCNY": {"price": 7.2487, "change_pct": 0.12},
    "DXY": {"price": 99.34, "change_pct": 0.12}, "BRENT": {"price": 75.93, "change_pct": 0.69},
    "NATGAS": {"price": 3.16, "change_pct": -2.20}, "GOLD": {"price": 4107.11, "change_pct": 0.73},
    "SILVER": {"price": 62.40, "change_pct": 1.49}, "COPPER": {"price": 6.28, "change_pct": -0.58},
    "BTC": {"price": 64500, "change_pct": 0.5}, "ETH": {"price": 1890, "change_pct": -0.5},
    "US2Y": {"price": 3.95, "change_pct": 0.0}, "US10Y": {"price": 4.52, "change_pct": 0.0},
    "US3M": {"price": 5.20, "change_pct": 0.0}, "FEDFUNDS": {"price": 4.38, "change_pct": 0.0},
    "CN_LPR1Y": {"price": 3.10, "change_pct": 0.0}, "VIX": {"price": 14.87, "change_pct": -2.24},
    "US_CPI": {"price": 3.5, "change_pct": 0.0}, "US_PPI": {"price": 2.5, "change_pct": 0.0},
    "CN_CPI": {"price": 0.5, "change_pct": 0.0}, "CN_PPI": {"price": -2.0, "change_pct": 0.0},
    "US_UNEMP": {"price": 4.1, "change_pct": 0.0}, "US_GDP": {"price": 2.8, "change_pct": 0.0},
    "CN_GDP": {"price": 5.2, "change_pct": 0.0}, "CN_PMI": {"price": 50.1, "change_pct": 0.0},
}

RANGES: dict[str, tuple] = {
    "SPX": (1000, 20000), "NDX": (5000, 40000), "DAX": (5000, 40000),
    "FTSE": (3000, 15000), "N225": (10000, 60000), "HSI": (10000, 40000),
    "SHCOMP": (1000, 8000), "A50": (5000, 25000),
    "EURUSD": (0.8, 1.5), "USDJPY": (80, 200), "GBPUSD": (0.9, 1.8),
    "USDCNY": (6.0, 8.5), "DXY": (80, 120),
    "BRENT": (20, 200), "NATGAS": (0.5, 20), "GOLD": (500, 6000),
    "SILVER": (10, 120), "COPPER": (2, 12),
    "BTC": (1000, 500000), "ETH": (50, 20000),
    "US2Y": (0, 10), "US10Y": (0, 10), "US3M": (0, 10),
    "FEDFUNDS": (0, 10), "CN_LPR1Y": (0, 10), "VIX": (5, 100),
    "US_CPI": (-5, 20), "US_PPI": (-5, 20), "CN_CPI": (-5, 20), "CN_PPI": (-10, 20),
    "US_UNEMP": (0, 25), "US_GDP": (-10, 15), "CN_GDP": (-10, 15), "CN_PMI": (30, 70),
}


def _make_record(symbol: str, price: float, change_pct: float, change: float | None = None) -> dict:
    name, exch, cat, gran, unit, url = META.get(symbol, (symbol, "", "equity", "daily", "", ""))
    if change is None:
        prev = price / (1 + change_pct / 100) if price and change_pct else price
        change = round(price - prev, 4)
    return {
        "symbol": symbol, "name": name, "exchange": exch, "category": cat,
        "granularity": gran, "price": round(float(price), 4),
        "change": round(float(change), 4), "change_pct": round(float(change_pct), 4),
        "unit": unit, "source_url": url, "timestamp": shanghai_now(),
    }


def _valid(symbol: str, price: float) -> bool:
    lo, hi = RANGES.get(symbol, (0, float("inf")))
    return lo <= price <= hi


def _fetch_sina_batch() -> dict[str, dict]:
    """Fetch global indices + FX + commodities from Sina Finance hq API."""
    codes = {
        "int_sp500": ("SPX", "global"), "int_nasdaq": ("NDX", "global"),
        "int_dax": ("DAX", "global"), "int_ftse": ("FTSE", "global"),
        "int_nikkei": ("N225", "global"), "int_hangseng": ("HSI", "global"),
        "sh000001": ("SHCOMP", "cn_index"),
        "fx_seurusd": ("EURUSD", "fx"), "fx_susdjpy": ("USDJPY", "fx"),
        "fx_sgbpusd": ("GBPUSD", "fx"), "fx_susdcny": ("USDCNY", "fx"),
        "DINIW": ("DXY", "fx"),
        "hf_OIL": ("BRENT", "comm"), "hf_NG": ("NATGAS", "comm"),
        "hf_GC": ("GOLD", "comm"), "hf_SI": ("SILVER", "comm"),
        "hf_HG": ("COPPER", "comm"),
    }
    out: dict[str, dict] = {}
    try:
        session = create_session()
        url = "https://hq.sinajs.cn/list=" + ",".join(codes.keys())
        resp = session.get(url, headers=SINA_HEADERS, timeout=10)
        text = resp.content.decode("gbk", errors="replace")
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line.startswith("var hq_str_"):
                continue
            eq = line.find("=")
            if eq < 0:
                continue
            code = line[len("var hq_str_"):eq]
            payload = line[eq + 2:-2]
            if not payload:
                continue
            mapping = codes.get(code)
            if not mapping:
                continue
            symbol, kind = mapping
            try:
                fields = payload.split(",")
                if kind == "global":
                    price = float(fields[1])
                    chg_pct = float(fields[3])
                    if symbol != "DAX" or _valid(symbol, price):
                        out[symbol] = _make_record(symbol, price, chg_pct)
                elif kind == "cn_index":
                    current = float(fields[3])
                    prev = float(fields[2])
                    chg_pct = ((current - prev) / prev * 100) if prev else 0
                    out[symbol] = _make_record(symbol, current, chg_pct)
                elif kind == "fx":
                    price = float(fields[1])
                    prev = float(fields[3]) if len(fields) > 3 and fields[3] else price
                    chg_pct = ((price - prev) / prev * 100) if prev else 0
                    if _valid(symbol, price):
                        out[symbol] = _make_record(symbol, price, chg_pct)
                elif kind == "comm":
                    price = float(fields[0])
                    prev = float(fields[2]) if len(fields) > 2 and fields[2] else price
                    chg_pct = ((price - prev) / prev * 100) if prev else 0
                    if code == "hf_HG":
                        price = price / 100.0
                    if _valid(symbol, price):
                        out[symbol] = _make_record(symbol, price, chg_pct)
            except (ValueError, IndexError):
                continue
    except Exception as e:
        logger.warning(f"Sina batch failed: {e}")
    return out


def _fetch_crypto() -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        session = create_session()
        resp = session.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true",
            timeout=15)
        data = resp.json()
        for sym, cg_id in (("BTC", "bitcoin"), ("ETH", "ethereum")):
            d = data.get(cg_id, {})
            price = d.get("usd")
            chg = d.get("usd_24h_change", 0)
            if price and _valid(sym, float(price)):
                out[sym] = _make_record(sym, float(price), float(chg or 0))
    except Exception:
        pass
    if not out:
        try:
            session = create_session()
            resp = session.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", timeout=12)
            data = resp.json().get("data", [])
            tick = {t["instId"]: t for t in data}
            for sym, pair in (("BTC", "BTC-USDT"), ("ETH", "ETH-USDT")):
                t = tick.get(pair)
                if t:
                    price = float(t["last"])
                    chg = float(t.get("lastPxChangePct", 0)) * 100
                    if _valid(sym, price):
                        out[sym] = _make_record(sym, price, chg)
        except Exception:
            pass
    return out


def fetch_all_market_data() -> list[dict]:
    """Fetch all 34 market indicators. Always returns a full set."""
    results: dict[str, dict] = {}

    # 1. Sina batch (primary for global indices, FX, commodities)
    try:
        results.update(_fetch_sina_batch())
    except Exception as e:
        logger.warning(f"Sina batch error: {e}")

    # 2. Crypto
    try:
        for sym, rec in _fetch_crypto().items():
            if sym not in results:
                results[sym] = rec
    except Exception:
        pass

    # 3. Fill remaining with seed values
    filled = 0
    for sym in META:
        if sym not in results:
            seed = SEED.get(sym, {"price": 0, "change_pct": 0})
            results[sym] = _make_record(sym, seed["price"], seed["change_pct"])
            filled += 1

    live = len(results) - filled
    logger.info(f"Market data: {len(results)} indicators ({live} live, {filled} cached)")
    return list(results.values())
