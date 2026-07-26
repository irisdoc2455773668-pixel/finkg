"""Application configuration via pydantic-settings."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──
    database_url: str = "postgresql://finkg:finkg@localhost:5432/finkg"
    database_url_async: str = "postgresql+asyncpg://finkg:finkg@localhost:5432/finkg"

    # ── Redis / Celery ──
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    # ── Server ──
    host: str = "0.0.0.0"
    port: int = 8765
    debug: bool = False

    # ── NLP Engine ──
    nlp_engine: Literal["rule", "ml", "dify", "openai"] = "rule"
    nlp_ml_enabled: bool = False

    # ── LLM / Dify ──
    dify_enabled: bool = False
    dify_base_url: str = "http://127.0.0.1:5001"
    dify_wf_article_key: str = ""
    dify_wf_report_key: str = ""
    dify_timeout: int = 120

    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"
    openai_model: str = "deepseek-chat"
    llm_daily_token_budget: int = 100_000

    # ── Market Data ──
    market_update_interval: int = 5

    # ── Proxy (OPT-IN) ──
    use_proxy: bool = False
    socks_proxy_host: str = "127.0.0.1"
    socks_proxy_port: str = "9674"

    # ── Timezone ──
    timezone: str = "Asia/Shanghai"

    # ── Paths ──
    project_root: Path = Path(__file__).resolve().parent.parent
    sources_config: Path = Path("sources.json")


settings = Settings()
