"""MLflow compatibility layer.

All version-sensitive MLflow calls live here. Domain modules consume ``TraceSource`` only.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from evaluation_harness.trace_sources.base import SourceTrace, TracePage, TraceQuery


async def ensure_mlflow_experiment(*, tracking_uri: str, experiment_name: str) -> str:
    """Create or resolve one MLflow experiment without exposing MLflow entities."""
    return await asyncio.to_thread(_ensure_mlflow_experiment_sync, tracking_uri, experiment_name)


def _ensure_mlflow_experiment_sync(tracking_uri: str, experiment_name: str) -> str:
    try:
        from mlflow import MlflowClient
        from mlflow.exceptions import MlflowException
    except ImportError as exc:
        raise RuntimeError("Install the 'mlflow' extra to manage MLflow experiments") from exc
    client = MlflowClient(tracking_uri=tracking_uri)
    existing = client.get_experiment_by_name(experiment_name)
    if existing is not None:
        return str(existing.experiment_id)
    try:
        return str(client.create_experiment(experiment_name))
    except MlflowException:
        existing = client.get_experiment_by_name(experiment_name)
        if existing is None:
            raise
        return str(existing.experiment_id)


class MlflowTraceSource:
    """Adapt the pinned MLflow client to the trace-source protocol."""

    def __init__(self, *, tracking_uri: str, experiment_id: str) -> None:
        self.tracking_uri = tracking_uri
        self.experiment_id = experiment_id

    def _client(self) -> Any:
        try:
            import mlflow
            from mlflow import MlflowClient
        except ImportError as exc:
            raise RuntimeError("Install the 'mlflow' extra to use MlflowTraceSource") from exc
        mlflow.set_tracking_uri(self.tracking_uri)
        return MlflowClient()

    async def search(self, query: TraceQuery) -> TracePage:
        return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, query: TraceQuery) -> TracePage:
        client = self._client()
        search: Callable[..., Any] | None = getattr(client, "search_traces", None)
        if search is None:
            raise RuntimeError("Configured MLflow does not support trace search")
        order_by = ["timestamp_ms ASC"]
        result = search(
            experiment_ids=[self.experiment_id],
            max_results=query.limit,
            page_token=query.cursor,
            order_by=order_by,
        )
        traces = list(result)
        items = [self._convert_trace(trace) for trace in traces if self._matches(trace, query)]
        return TracePage(items=items, next_cursor=getattr(result, "token", None))

    async def get(self, source_trace_id: str) -> SourceTrace:
        return await asyncio.to_thread(self._get_sync, source_trace_id)

    def _get_sync(self, source_trace_id: str) -> SourceTrace:
        trace = self._client().get_trace(source_trace_id)
        return self._convert_trace(trace)

    @staticmethod
    def _matches(trace: Any, query: TraceQuery) -> bool:
        info = getattr(trace, "info", None)
        timestamp_ms = getattr(info, "timestamp_ms", 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=query.start_time.tzinfo)
        if not query.start_time <= timestamp < query.end_time:
            return False
        tags = getattr(info, "tags", {}) or {}
        if all(str(tags.get(key)) == value for key, value in query.attributes.items()):
            return True
        converted = MlflowTraceSource._convert_trace(trace).raw
        if not isinstance(converted, dict):
            return False
        attributes = converted.get("attributes") or {}
        resource = converted.get("resource") or {}
        return all(
            str(attributes.get(key, resource.get(key))) == value
            for key, value in query.attributes.items()
        )

    @staticmethod
    def _convert_trace(trace: Any) -> SourceTrace:
        info = getattr(trace, "info", None)
        trace_id = getattr(info, "trace_id", None) or getattr(trace, "trace_id", None)
        timestamp_ms = getattr(info, "timestamp_ms", 0)
        request_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        to_json = getattr(trace, "to_json", None)
        raw: Any = to_json() if callable(to_json) else trace
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                pass
        raw = MlflowTraceSource._flatten_otel_trace(raw)
        return SourceTrace(
            source_trace_id=str(trace_id),
            source_revision=str(getattr(info, "last_update_time_ms", "")) or None,
            observed_at=request_time,
            raw=raw,
        )

    @staticmethod
    def _flatten_otel_trace(raw: Any) -> Any:
        """Expose OTel span attributes without leaking MLflow entities into adapters."""
        if not isinstance(raw, dict):
            return raw
        data = raw.get("data")
        if not isinstance(data, dict):
            return raw
        spans = data.get("spans")
        if not isinstance(spans, list) or not spans:
            return raw
        root = next(
            (span for span in spans if isinstance(span, dict) and not span.get("parent_id")),
            spans[0],
        )
        if not isinstance(root, dict):
            return raw
        attributes = root.get("attributes")
        decoded_attributes = (
            {
                str(key): MlflowTraceSource._decode_attribute(value)
                for key, value in attributes.items()
            }
            if isinstance(attributes, dict)
            else {}
        )
        info = raw.get("info")
        tags = info.get("tags") if isinstance(info, dict) else {}
        status = root.get("status") or root.get("status_code")
        if isinstance(status, dict):
            status = status.get("code")
        return {
            "attributes": decoded_attributes,
            "span_ids": [
                str(span.get("span_id") or (span.get("context") or {}).get("span_id"))
                for span in spans
                if isinstance(span, dict)
                and (span.get("span_id") or isinstance(span.get("context"), dict))
            ],
            "status": status,
            "resource": root.get("resource") or raw.get("resource") or tags or {},
        }

    @staticmethod
    def _decode_attribute(value: Any) -> Any:
        """Decode the JSON representation used by MLflow trace span attributes."""
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
