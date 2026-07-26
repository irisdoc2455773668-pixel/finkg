"""Shared Pydantic schemas for API requests/responses."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


class TimeRangeParams(BaseModel):
    date_from: str | None = Field(default=None, alias="dateFrom")
    date_to: str | None = Field(default=None, alias="dateTo")


class PaginatedResponse(BaseModel):
    list: list[Any]
    total: int
    page: int
    page_size: int
