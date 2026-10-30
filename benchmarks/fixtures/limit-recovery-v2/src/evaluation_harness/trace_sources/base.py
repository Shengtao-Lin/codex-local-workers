"""Vendor-neutral trace discovery contract."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraceQuery(StrictModel):
    application_id: str
    start_time: datetime
    end_time: datetime
    cursor: str | None = None
    limit: int = Field(default=100, ge=1, le=1_000)
    attributes: dict[str, str] = Field(default_factory=dict)


class SourceTrace(StrictModel):
    source_trace_id: str
    source_revision: str | None = None
    observed_at: datetime
    raw: Any


class TracePage(StrictModel):
    items: list[SourceTrace]
    next_cursor: str | None = None


class TraceSource(Protocol):
    async def search(self, query: TraceQuery) -> TracePage: ...

    async def get(self, source_trace_id: str) -> SourceTrace: ...
