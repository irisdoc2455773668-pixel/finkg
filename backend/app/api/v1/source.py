"""News source CRUD API."""
import json
import os

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NewsSource

router = APIRouter()


class SourceCreate(BaseModel):
    name: str
    url: str
    source_type: str = "rss"
    language: str = "zh"
    region: str = "cn"
    category: str = "economy"
    political_leaning: str = "center"
    reliability_score: float = 0.7
    selector: str = "a"
    base_url: str = ""
    encoding: str = "utf-8"
    min_len: int = 12
    fetch_body: bool = False
    fetch_interval: int = 3600
    is_active: bool = True


@router.get("/sources")
def source_list(
    language: str = Query(""), region: str = Query(""),
    is_active: bool = Query(None, alias="isActive"),
    db: Session = Depends(get_db),
):
    q = db.query(NewsSource)
    if language:
        q = q.filter(NewsSource.language == language)
    if region:
        q = q.filter(NewsSource.region == region)
    if is_active is not None:
        q = q.filter(NewsSource.is_active == is_active)
    sources = q.all()
    return {"list": [_source_to_dict(s) for s in sources]}


@router.post("/sources")
def source_create(body: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(NewsSource).filter(NewsSource.name == body.name).first()
    if existing:
        return {"ok": False, "error": f"Source '{body.name}' already exists"}
    src = NewsSource(**body.model_dump())
    db.add(src)
    db.commit()
    db.refresh(src)
    return {"ok": True, "source": _source_to_dict(src)}


@router.put("/sources/{source_id}")
def source_update(source_id: str, body: SourceCreate, db: Session = Depends(get_db)):
    src = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not src:
        return {"ok": False, "error": "Source not found"}
    for key, value in body.model_dump().items():
        setattr(src, key, value)
    db.commit()
    return {"ok": True, "source": _source_to_dict(src)}


@router.delete("/sources/{source_id}")
def source_delete(source_id: str, db: Session = Depends(get_db)):
    src = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not src:
        return {"ok": False, "error": "Source not found"}
    src.is_active = False
    db.commit()
    return {"ok": True, "message": f"Source '{src.name}' deactivated"}


@router.post("/sources/{source_id}/test")
def source_test(source_id: str, db: Session = Depends(get_db)):
    src = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not src:
        return {"ok": False, "error": "Source not found"}
    from app.services.crawler import fetch_rss_source, fetch_web_source
    try:
        if src.source_type == "rss":
            articles = fetch_rss_source(src)
        else:
            articles = fetch_web_source(src)
        return {"ok": True, "articles_found": len(articles),
                "sample": articles[0]["title"][:100] if articles else None}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/sources/seed")
def source_seed_defaults(db: Session = Depends(get_db)):
    """Seed default news sources from JSON config."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sources.json")
    if not os.path.exists(config_path):
        return {"ok": False, "error": "sources.json not found"}
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for s in data.get("rss_sources", []) + data.get("web_sources", []):
        if not s.get("enabled", True):
            continue
        existing = db.query(NewsSource).filter(NewsSource.name == s["name"]).first()
        if existing:
            continue
        db.add(NewsSource(
            name=s["name"], url=s["url"],
            source_type="rss" if s in data.get("rss_sources", []) else "web",
            language=s.get("lang", "zh"), region=s.get("region", "cn"),
            category=s.get("cat", "economy"),
            selector=s.get("selector", "a"), base_url=s.get("base_url", ""),
            encoding=s.get("encoding", "utf-8"), min_len=s.get("min_len", 12),
            fetch_body=s.get("fetch_body", False),
        ))
        count += 1
    db.commit()
    return {"ok": True, "seeded": count}


def _source_to_dict(s: NewsSource) -> dict:
    return {
        "id": str(s.id), "name": s.name, "url": s.url,
        "sourceType": s.source_type, "language": s.language, "region": s.region,
        "category": s.category, "politicalLeaning": s.political_leaning,
        "reliabilityScore": s.reliability_score,
        "isActive": s.is_active, "createdAt": s.created_at.isoformat() if s.created_at else None,
    }
