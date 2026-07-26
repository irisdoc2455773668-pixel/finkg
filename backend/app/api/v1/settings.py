"""Settings API — AI config, sources management."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AIConfig, NewsSource

router = APIRouter()


# ── Pydantic Schemas ──

class AIConfigUpdate(BaseModel):
    provider: str = "openai"
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    model_name: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    is_active: bool = True
    daily_token_limit: int = 100000


class NewsSourceUpdate(BaseModel):
    name: str
    url: str
    source_type: str = "rss"
    language: str = "zh"
    region: str = "cn"
    category: str = "economy"
    is_active: bool = True


# ── AI Config ──

@router.get("/settings/ai")
def get_ai_config(db: Session = Depends(get_db)):
    cfg = db.query(AIConfig).filter(AIConfig.is_active == True).first()
    if not cfg:
        return {"configured": False}
    return {
        "configured": True,
        "id": str(cfg.id),
        "provider": cfg.provider,
        "base_url": cfg.base_url,
        "api_key": cfg.api_key[:8] + "..." if cfg.api_key else "",  # Masked
        "model_name": cfg.model_name,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "is_active": cfg.is_active,
        "daily_token_limit": cfg.daily_token_limit,
        "tokens_used_today": cfg.tokens_used_today or 0,
    }


@router.put("/settings/ai")
def update_ai_config(body: AIConfigUpdate, db: Session = Depends(get_db)):
    cfg = db.query(AIConfig).filter(AIConfig.is_active == True).first()
    if not cfg:
        cfg = AIConfig()
        db.add(cfg)

    cfg.provider = body.provider
    cfg.base_url = body.base_url
    if body.api_key and body.api_key != "***":
        cfg.api_key = body.api_key  # Only update if not masked
    cfg.model_name = body.model_name
    cfg.temperature = body.temperature
    cfg.max_tokens = body.max_tokens
    cfg.is_active = body.is_active
    cfg.daily_token_limit = body.daily_token_limit
    db.commit()

    return {"ok": True, "message": "AI配置已更新"}


@router.post("/settings/ai/test")
def test_ai_connection(db: Session = Depends(get_db)):
    cfg = db.query(AIConfig).filter(AIConfig.is_active == True).first()
    if not cfg or not cfg.api_key:
        return {"ok": False, "message": "请先配置AI模型"}

    from app.services.llm.openai_client import test_connection
    ok, msg = test_connection(cfg)
    return {"ok": ok, "message": msg}


# ── Sources Management ──

@router.get("/settings/sources")
def get_all_sources(db: Session = Depends(get_db)):
    sources = db.query(NewsSource).order_by(NewsSource.region, NewsSource.name).all()
    return {
        "list": [{
            "id": str(s.id),
            "name": s.name,
            "url": s.url,
            "sourceType": s.source_type,
            "language": s.language,
            "region": s.region,
            "category": s.category,
            "isActive": s.is_active,
            "reliabilityScore": s.reliability_score,
            "politicalLeaning": s.political_leaning,
        } for s in sources],
        "total": len(sources),
    }


@router.put("/settings/sources/{source_id}")
def update_source(source_id: str, body: NewsSourceUpdate, db: Session = Depends(get_db)):
    s = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not s:
        return {"ok": False, "error": "Source not found"}
    for key, value in body.model_dump().items():
        setattr(s, key, value)
    db.commit()
    return {"ok": True}


@router.post("/settings/sources")
def add_source(body: NewsSourceUpdate, db: Session = Depends(get_db)):
    existing = db.query(NewsSource).filter(NewsSource.name == body.name).first()
    if existing:
        return {"ok": False, "error": f"Source '{body.name}' already exists"}
    s = NewsSource(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"ok": True, "id": str(s.id)}


@router.delete("/settings/sources/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    s = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not s:
        return {"ok": False, "error": "Source not found"}
    db.delete(s)
    db.commit()
    return {"ok": True, "message": f"Source '{s.name}' deleted"}


@router.post("/settings/sources/{source_id}/toggle")
def toggle_source(source_id: str, db: Session = Depends(get_db)):
    s = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not s:
        return {"ok": False}
    s.is_active = not s.is_active
    db.commit()
    return {"ok": True, "isActive": s.is_active}
