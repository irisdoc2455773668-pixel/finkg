"""OpenAI-compatible LLM client with token budget tracking."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models import AIConfig

logger = logging.getLogger("finkg.llm")


def get_active_config(db: Session) -> AIConfig | None:
    """Return the active AI config, or None if not configured."""
    cfg = db.query(AIConfig).filter(AIConfig.is_active == True).first()
    if cfg and not cfg.api_key:
        return None
    return cfg


def _reset_daily_tokens(cfg: AIConfig) -> None:
    """Reset daily token counter if it's a new day."""
    today = datetime.utcnow().date()
    last = cfg.last_reset_date.date() if cfg.last_reset_date else today
    if today > last:
        cfg.tokens_used_today = 0
        cfg.last_reset_date = datetime.utcnow()


def chat_completion(
    db: Session,
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, dict] | tuple[None, str]:
    """Send chat completion request to OpenAI-compatible API.

    Returns (content, usage_info) on success, or (None, error_message) on failure.
    """
    cfg = get_active_config(db)
    if not cfg:
        return None, "AI模型未配置。请在设置页面填写API Key。"
    if not cfg.base_url or not cfg.model_name:
        return None, "AI模型配置不完整。请填写Base URL和Model Name。"

    _reset_daily_tokens(cfg)

    if cfg.tokens_used_today >= cfg.daily_token_limit:
        return None, f"今日Token预算已用完 ({cfg.tokens_used_today}/{cfg.daily_token_limit})"

    url = f"{cfg.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": cfg.model_name,
        "messages": messages,
        "temperature": temperature if temperature is not None else cfg.temperature,
        "max_tokens": max_tokens or cfg.max_tokens,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                err = resp.text[:300]
                logger.error(f"LLM API error {resp.status_code}: {err}")
                return None, f"API返回错误 {resp.status_code}: {err}"

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            # Track token usage
            tokens = usage.get("total_tokens", 0)
            cfg.tokens_used_today = (cfg.tokens_used_today or 0) + tokens
            db.commit()

            logger.info(f"LLM call: {tokens} tokens used, {cfg.tokens_used_today}/{cfg.daily_token_limit} today")
            return content, usage

    except httpx.TimeoutException:
        return None, "API请求超时（120秒）。请检查网络或API服务状态。"
    except Exception as e:
        logger.error(f"LLM API exception: {e}")
        return None, f"API请求失败: {str(e)[:200]}"


def test_connection(cfg: AIConfig) -> tuple[bool, str]:
    """Test whether the configured API endpoint is reachable and working."""
    if not cfg.api_key:
        return False, "API Key未设置"
    url = f"{cfg.base_url.rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
                json={
                    "model": cfg.model_name,
                    "messages": [{"role": "user", "content": "Hi, reply with just 'OK'."}],
                    "max_tokens": 10,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                model_used = data.get("model", cfg.model_name)
                return True, f"连接成功！模型: {model_used}，回复: {reply[:50]}"
            return False, f"API返回错误 {resp.status_code}: {resp.text[:200]}"
    except httpx.TimeoutException:
        return False, "连接超时，请检查Base URL是否正确"
    except Exception as e:
        return False, f"连接失败: {str(e)[:200]}"
