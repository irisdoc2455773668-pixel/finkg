"""Database engine and session management."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Build connection args based on database type
_db_url = settings.database_url
_is_sqlite = _db_url.startswith("sqlite")

_connect_args: dict = {}
_engine_kwargs: dict = {"echo": settings.debug}

if _is_sqlite:
    _connect_args = {"check_same_thread": False}
else:
    _db_url = _db_url.replace("+asyncpg", "").replace("+psycopg2", "")
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True)

engine = create_engine(_db_url, connect_args=_connect_args, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Session:
    """FastAPI dependency: yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
