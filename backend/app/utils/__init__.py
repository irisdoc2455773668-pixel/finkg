"""Utility helpers."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone, timedelta

from app.config import settings

try:
    from zoneinfo import ZoneInfo

    SHANGHAI_TZ = ZoneInfo(settings.timezone)
except Exception:
    SHANGHAI_TZ = timezone(timedelta(hours=8))


def shanghai_now() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def content_hash(text: str) -> str:
    """SHA-256 hash of text, first 16 hex chars."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def clean_html(text: str) -> str:
    """Strip HTML tags from text."""
    import re

    return re.sub(r"<[^>]+>", "", text).strip()
