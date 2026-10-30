"""Versioned trace adapter contract and helpers."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from evaluation_harness.canonical.models import CanonicalSample
from evaluation_harness.contracts import ApplicationSpec
from evaluation_harness.trace_sources.base import SourceTrace


class AdapterContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application: ApplicationSpec
    row_mode: Literal["trace", "turn"]
    schema_version: Literal["1.0"] = "1.0"


class TraceAdapter(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def can_handle(self, trace: SourceTrace) -> bool: ...

    def normalize(
        self, trace: SourceTrace, *, context: AdapterContext
    ) -> list[CanonicalSample]: ...


class AdapterError(ValueError):
    """A structured per-trace rejection that does not abort dataset generation."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
