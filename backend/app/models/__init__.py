"""SQLAlchemy ORM models for FinKG v5 (PostgreSQL/SQLite compatible)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship

# Database-agnostic types (work with both PostgreSQL and SQLite)
# PostgreSQL optimization with native UUID/JSONB can be added later via Alembic
IDType = String(36)
JSONType = JSON


def _newid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════════
# News Sources
# ═══════════════════════════════════════════════════════════════

class NewsSource(Base):
    __tablename__ = "news_sources"

    id = Column(IDType, primary_key=True, default=_newid)
    name = Column(String(100), nullable=False, unique=True)
    url = Column(String(500), nullable=False)
    source_type = Column(String(20), nullable=False, default="rss")  # rss, web, api
    language = Column(String(10), nullable=False, default="zh")
    region = Column(String(50), nullable=False, default="cn")  # cn, us, eu, jp, hk, sg
    category = Column(String(50), nullable=False, default="economy")
    political_leaning = Column(String(30), default="center")  # state_media, independent, western_mainstream, financial_press
    reliability_score = Column(Float, default=0.7)
    selector = Column(String(100), default="a")
    base_url = Column(String(500), default="")
    encoding = Column(String(20), default="utf-8")
    min_len = Column(Integer, default=12)
    fetch_body = Column(Boolean, default=False)
    fetch_interval = Column(Integer, default=3600)
    is_active = Column(Boolean, default=True)
    extra_config = Column(JSONType, default=dict)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    fetch_logs = relationship("SourceFetchLog", back_populates="source", cascade="all, delete-orphan")


class SourceFetchLog(Base):
    __tablename__ = "source_fetch_logs"

    id = Column(IDType, primary_key=True, default=_newid)
    source_id = Column(IDType, ForeignKey("news_sources.id", ondelete="CASCADE"), nullable=False)
    articles_found = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_detail = Column(Text, default="")
    status = Column(String(20), default="running")  # running, done, failed
    started_at = Column(DateTime, default=_utcnow)
    finished_at = Column(DateTime, nullable=True)

    source = relationship("NewsSource", back_populates="fetch_logs")


# ═══════════════════════════════════════════════════════════════
# News
# ═══════════════════════════════════════════════════════════════

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(IDType, primary_key=True, default=_newid)
    source_id = Column(IDType, ForeignKey("news_sources.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, default="")
    content_hash = Column(String(64), unique=True, nullable=False)
    url = Column(String(2000), nullable=False)
    source_name = Column(String(100), default="")
    language = Column(String(10), default="zh")
    region = Column(String(50), default="cn")
    category = Column(String(50), default="economy")
    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=_utcnow)
    is_analyzed = Column(Boolean, default=False)

    analysis = relationship("NewsAnalysis", back_populates="article", uselist=False, cascade="all, delete-orphan")
    source = relationship("NewsSource")


class NewsAnalysis(Base):
    __tablename__ = "news_analyses"

    id = Column(IDType, primary_key=True, default=_newid)
    article_id = Column(IDType, ForeignKey("news_articles.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary = Column(Text, default="")
    sentiment = Column(String(20), default="neutral")  # bullish, bearish, neutral
    sentiment_score = Column(Float, default=0.0)  # [-1, 1] continuous
    risk_level = Column(String(20), default="low")  # high, medium, low
    risk_weight = Column(Float, default=0.2)
    tags = Column(Text, default="")
    entities = Column(JSONType, default=dict)  # {"Company": [...], "Person": [...], "Location": [...], "FinanceTerm": [...]}
    narrative_frames = Column(JSONType, default=list)  # ["decoupling", "tech_war", ...]
    analysis_engine = Column(String(20), default="rule")  # rule, ml, dify, openai
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    article = relationship("NewsArticle", back_populates="analysis")


# ═══════════════════════════════════════════════════════════════
# Market
# ═══════════════════════════════════════════════════════════════

class MarketIndex(Base):
    __tablename__ = "market_indices"

    id = Column(IDType, primary_key=True, default=_newid)
    symbol = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    exchange = Column(String(50), default="")
    category = Column(String(30), nullable=False)
    granularity = Column(String(20), default="daily")
    unit = Column(String(20), default="")
    source_url = Column(String(500), default="")
    price = Column(Float, default=0.0)
    change = Column(Float, default=0.0)
    change_pct = Column(Float, default=0.0)
    volume = Column(Float, default=0.0)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=_utcnow)


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id = Column(IDType, primary_key=True, default=_newid)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, default=0.0)
    change = Column(Float, default=0.0)
    change_pct = Column(Float, default=0.0)
    volume = Column(Float, default=0.0)
    snapshot_time = Column(DateTime, nullable=False, index=True)
    granularity = Column(String(20), default="daily")


# ═══════════════════════════════════════════════════════════════
# Knowledge Graph
# ═══════════════════════════════════════════════════════════════

class KGNode(Base):
    __tablename__ = "kg_nodes"

    id = Column(IDType, primary_key=True, default=_newid)
    node_type = Column(String(30), nullable=False, index=True)
    canonical_name = Column(String(300), nullable=False)
    mention_count = Column(Integer, default=1)
    importance_score = Column(Float, default=0.5)
    first_seen_at = Column(DateTime, default=_utcnow)
    last_seen_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    aliases = Column(JSONType, default=list)
    properties = Column(JSONType, default=dict)

    __table_args__ = (
        UniqueConstraint("node_type", "canonical_name", name="uq_kg_node_type_name"),
    )


class KGEdge(Base):
    __tablename__ = "kg_edges"

    id = Column(IDType, primary_key=True, default=_newid)
    source_node_id = Column(IDType, ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id = Column(IDType, ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(30), nullable=False)
    weight = Column(Float, default=0.5)
    direction = Column(String(15), default="directed")
    first_observed_at = Column(DateTime, default=_utcnow)
    last_observed_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    observation_count = Column(Integer, default=1)
    evidence_article_ids = Column(JSONType, default=list)


class KGEntityTimeline(Base):
    __tablename__ = "kg_entity_timelines"

    id = Column(IDType, primary_key=True, default=_newid)
    node_id = Column(IDType, ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(DateTime, nullable=False, index=True)
    mention_count = Column(Integer, default=0)
    avg_sentiment = Column(Float, default=0.0)
    source_regions = Column(JSONType, default=dict)  # {"cn": 5, "us": 3, ...}

    __table_args__ = (
        UniqueConstraint("node_id", "week_start", name="uq_entity_week"),
    )


class KGEdgeTimeline(Base):
    __tablename__ = "kg_edge_timelines"

    id = Column(IDType, primary_key=True, default=_newid)
    edge_id = Column(IDType, ForeignKey("kg_edges.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(DateTime, nullable=False, index=True)
    cooccurrence_count = Column(Integer, default=0)
    weight = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("edge_id", "week_start", name="uq_edge_week"),
    )


# ═══════════════════════════════════════════════════════════════
# Narrative Analysis (core differentiator)
# ═══════════════════════════════════════════════════════════════

class NarrativeTheme(Base):
    __tablename__ = "narrative_themes"

    id = Column(IDType, primary_key=True, default=_newid)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, default="")
    keywords = Column(JSONType, default=list)  # ["keyword1", "keyword2", ...]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class NarrativeSentiment(Base):
    __tablename__ = "narrative_sentiments"

    id = Column(IDType, primary_key=True, default=_newid)
    theme_id = Column(IDType, ForeignKey("narrative_themes.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(DateTime, nullable=False, index=True)
    region = Column(String(50), nullable=False, default="cn")  # cn, us, eu, ...
    avg_sentiment = Column(Float, default=0.0)
    article_count = Column(Integer, default=0)
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("theme_id", "week_start", "region", name="uq_narrative_week_region"),
    )


# ═══════════════════════════════════════════════════════════════
# Reports
# ═══════════════════════════════════════════════════════════════

class Report(Base):
    __tablename__ = "reports"

    id = Column(IDType, primary_key=True, default=_newid)
    report_type = Column(String(20), default="daily")  # daily, weekly, custom
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    headline = Column(String(500), default="")
    executive_summary = Column(Text, default="")
    sections = Column(JSONType, default=dict)  # {"economy": "...", "markets": "...", "geopolitics": "...", ...}
    market_sentiment = Column(String(20), default="neutral")
    article_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    engine = Column(String(20), default="rule")
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("report_type", "period_start", name="uq_report_period"),
    )


# ═══════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════

class PipelineTask(Base):
    __tablename__ = "pipeline_tasks"

    id = Column(IDType, primary_key=True, default=_newid)
    task_type = Column(String(30), nullable=False)  # crawl_news, crawl_market, analyze, full_pipeline
    status = Column(String(20), default="running")  # running, done, failed, aborted
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    source_ids = Column(JSONType, default=list)
    engine = Column(String(20), default="rule")
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_detail = Column(Text, default="")
    started_at = Column(DateTime, default=_utcnow)
    finished_at = Column(DateTime, nullable=True)

    stages = relationship("PipelineStage", back_populates="task", cascade="all, delete-orphan")


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id = Column(IDType, primary_key=True, default=_newid)
    task_id = Column(IDType, ForeignKey("pipeline_tasks.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, done, failed
    message = Column(Text, default="")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    task = relationship("PipelineTask", back_populates="stages")


# ═══════════════════════════════════════════════════════════════
# AI Configuration
# ═══════════════════════════════════════════════════════════════

class AIConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(IDType, primary_key=True, default=_newid)
    provider = Column(String(20), default="openai")  # openai, anthropic
    base_url = Column(String(500), default="https://api.deepseek.com/v1")
    api_key = Column(String(200), default="")
    model_name = Column(String(100), default="deepseek-chat")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    is_active = Column(Boolean, default=True)
    daily_token_limit = Column(Integer, default=100000)
    tokens_used_today = Column(Integer, default=0)
    last_reset_date = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
