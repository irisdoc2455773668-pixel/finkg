"""News crawler — RSS + web scraping from Chinese and international sources."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import feedparser
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models import NewsArticle, NewsSource, SourceFetchLog
from app.utils import content_hash, shanghai_now
from app.utils.http import create_session

logger = logging.getLogger("finkg.crawler")

# Category inference
_CAT_KEYWORDS: dict[str, re.Pattern] = {
    "politics": re.compile(r'(政治|政府|外交|国会|选举|政党|政策|监管|制裁|关税|法律|法院|立法|行政|国务院|习近平|特朗普|拜登)'),
    "economy": re.compile(r'(经济|GDP|CPI|PPI|通胀|利率|央行|消费|进出口|贸易|财政|税收|就业|失业|制造业|服务业)'),
    "technology": re.compile(r'(科技|AI|人工智能|芯片|半导体|5G|量子|航天|卫星|机器人|自动驾驶|新能源|电池|光伏|储能)'),
    "business": re.compile(r'(上市|IPO|股价|涨停|跌停|A股|港股|美股|基金|期货|黄金|原油|比特币|特斯拉|苹果|微软|谷歌|腾讯|阿里|字节|美团|比亚迪|宁德)'),
    "culture": re.compile(r'(文化|艺术|电影|音乐|文学|教育|学术|哲学|历史|考古|博物馆|非遗|传统|节日)'),
    "society": re.compile(r'(社会|民生|医疗|健康|环境|气候|灾害|交通|城市|农村|人口|养老|教育|住房|慈善)'),
}


def infer_category(title: str, default: str = "economy") -> str:
    for cat, pat in _CAT_KEYWORDS.items():
        if pat.search(title):
            return cat
    return default


# Crawl state for progress tracking
_crawl_state: dict = {
    "active": False, "total_sources": 0, "completed_sources": 0,
    "current_source": None, "articles_found": 0, "errors": [],
}
_crawl_lock = threading.Lock()
_abort_flag = threading.Event()


def get_crawl_state() -> dict:
    with _crawl_lock:
        return dict(_crawl_state)


def request_abort() -> None:
    _abort_flag.set()


# ── Fetch individual source ──

def fetch_rss_source(source: NewsSource) -> list[dict]:
    """Fetch articles from an RSS feed source."""
    articles: list[dict] = []
    try:
        session = create_session()
        resp = session.get(source.url, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            link = entry.get("link") or ""
            if not title or not link:
                continue
            text = entry.get("summary") or entry.get("description") or ""
            text = re.sub(r'<[^>]+>', '', text).strip()
            published = _shanghai_now()
            if entry.get("published_parsed"):
                from time import mktime
                published = datetime.fromtimestamp(mktime(entry["published_parsed"]))
            articles.append({
                "title": title[:500],
                "content": text[:5000],
                "content_hash": content_hash(title + (text or "")[:200]),
                "url": link[:2000],
                "source_name": source.name,
                "source_id": source.id,
                "language": source.language,
                "region": source.region,
                "category": infer_category(title, source.category),
                "published_at": published,
            })
    except Exception as e:
        logger.warning(f"RSS fetch failed {source.name}: {e}")
    return articles


def fetch_web_source(source: NewsSource) -> list[dict]:
    """Scrape headlines from a web page source."""
    articles: list[dict] = []
    try:
        session = create_session()
        resp = session.get(source.url, timeout=15)
        if resp.status_code != 200:
            return articles
        # Decode with configured encoding
        enc = source.encoding or "utf-8"
        try:
            text = resp.content.decode(enc)
        except Exception:
            text = resp.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        seen = set()
        for a in soup.find_all(source.selector or "a", href=True):
            link_text = a.get_text(strip=True)
            href = a["href"]
            if not link_text or len(link_text) < source.min_len or len(link_text) > 200:
                continue
            # Must contain CJK or Latin characters
            if not re.search(r'[一-鿿a-zA-Z]', link_text):
                continue
            # Filter noise
            if re.search(r'(注册|登录|广告|关于|联系|版权|备案|ICP|更多|首页|搜索|返回|取消|确定|share|comment)', link_text):
                continue
            key = link_text[:30]
            if key in seen:
                continue
            seen.add(key)

            from urllib.parse import urljoin
            full_url = urljoin(source.base_url or source.url, href)
            articles.append({
                "title": link_text[:500],
                "content": "",
                "content_hash": content_hash(link_text),
                "url": full_url[:2000],
                "source_name": source.name,
                "source_id": source.id,
                "language": source.language,
                "region": source.region,
                "category": infer_category(link_text, source.category),
                "published_at": _shanghai_now(),
            })
            if len(articles) >= 100:
                break
    except Exception as e:
        logger.warning(f"Scrape failed {source.name}: {e}")
    return articles


# ── Orchestrator ──

def crawl_all_sources(db: Session, source_ids: list[str] | None = None) -> dict:
    """Fetch all enabled sources in parallel, dedup, and insert into DB."""
    t0 = time.time()
    # Get enabled sources
    q = db.query(NewsSource).filter(NewsSource.is_active == True)
    if source_ids:
        q = q.filter(NewsSource.id.in_(source_ids))
    sources = q.all()

    if not sources:
        return {"ok": True, "count": 0, "sources": 0, "errors": [], "elapsed": 0}

    _abort_flag.clear()
    with _crawl_lock:
        _crawl_state.update(active=True, total_sources=len(sources),
                           completed_sources=0, current_source=None,
                           articles_found=0, errors=[])

    all_articles: list[dict] = []
    errors: list[str] = []
    try:
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {}
            for src in sources:
                if _abort_flag.is_set():
                    break
                if src.source_type == "rss":
                    futures[ex.submit(fetch_rss_source, src)] = src
                else:
                    futures[ex.submit(fetch_web_source, src)] = src

            for fut in as_completed(futures):
                if _abort_flag.is_set():
                    for f in futures:
                        f.cancel()
                    break
                src = futures[fut]
                with _crawl_lock:
                    _crawl_state["current_source"] = src.name
                try:
                    result = fut.result()
                    if result:
                        all_articles.extend(result)
                        with _crawl_lock:
                            _crawl_state["articles_found"] += len(result)
                except Exception as e:
                    errors.append(f"{src.name}: {e}")
                finally:
                    with _crawl_lock:
                        _crawl_state["completed_sources"] += 1
    finally:
        with _crawl_lock:
            _crawl_state["active"] = False

    # Dedup
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    unique: list[dict] = []
    for a in all_articles:
        if a["url"] in seen_urls or a["content_hash"] in seen_hashes:
            continue
        seen_urls.add(a["url"])
        seen_hashes.add(a["content_hash"])
        unique.append(a)

    if not unique:
        return {"ok": True, "count": 0, "sources": len(sources), "errors": errors, "elapsed": round(time.time() - t0, 1)}

    # Batch insert
    existing_urls = {r[0] for r in db.query(NewsArticle.url).filter(NewsArticle.url.in_([a["url"] for a in unique])).all()}
    existing_hashes = {r[0] for r in db.query(NewsArticle.content_hash).filter(NewsArticle.content_hash.in_([a["content_hash"] for a in unique])).all()}

    inserted = 0
    now = _shanghai_now()
    for a in unique:
        if a["url"] in existing_urls or a["content_hash"] in existing_hashes:
            continue
        db.add(NewsArticle(
            source_id=a.get("source_id"),
            title=a["title"], content=a["content"], content_hash=a["content_hash"],
            url=a["url"], source_name=a["source_name"],
            language=a.get("language", "zh"), region=a.get("region", "cn"),
            category=a["category"], published_at=a["published_at"], crawled_at=now,
        ))
        inserted += 1
    db.commit()

    elapsed = round(time.time() - t0, 1)
    logger.info(f"Crawl done: {inserted} new from {len(unique)} unique across {len(sources)} sources in {elapsed}s")
    return {"ok": True, "count": inserted, "raw": len(all_articles),
            "sources": len(sources), "errors": errors, "elapsed": elapsed}


def _shanghai_now() -> datetime:
    from app.utils import shanghai_now as _sn
    return _sn()
