"""Adapter for a documented, framework-neutral OTel message representation."""

from __future__ import annotations

from typing import Any

from evaluation_harness.adapters.base import AdapterContext
from evaluation_harness.adapters.common import build_samples, mapping_raw
from evaluation_harness.canonical.models import CanonicalSample
from evaluation_harness.trace_sources.base import SourceTrace


class GenericOtelAdapter:
    name = "generic-otel"
    version = "1.0.0"

    def can_handle(self, trace: SourceTrace) -> bool:
        try:
            raw = mapping_raw(trace)
        except ValueError:
            return False
        return isinstance(raw.get("messages"), list)

    def normalize(self, trace: SourceTrace, *, context: AdapterContext) -> list[CanonicalSample]:
        raw = mapping_raw(trace)
        messages: list[dict[str, Any]] = raw.get("messages") or []
        metadata = dict(raw.get("metadata") or {})
        return build_samples(
            trace,
            context=context,
            adapter_name=self.name,
            adapter_version=self.version,
            messages=messages,
            metadata=metadata,
        )
