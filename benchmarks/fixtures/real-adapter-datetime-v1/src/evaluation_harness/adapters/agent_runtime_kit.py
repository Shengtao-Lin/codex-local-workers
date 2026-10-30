"""Adapter for public ``agent-runtime-kit`` OpenTelemetry attributes."""

from __future__ import annotations

import json
from typing import Any

from evaluation_harness.adapters.base import AdapterContext, AdapterError
from evaluation_harness.adapters.common import build_samples, mapping_raw
from evaluation_harness.canonical.models import CanonicalSample
from evaluation_harness.trace_sources.base import SourceTrace


class AgentRuntimeKitAdapter:
    name = "agent-runtime-kit"
    version = "1.0.0"

    def can_handle(self, trace: SourceTrace) -> bool:
        try:
            raw = mapping_raw(trace)
        except ValueError:
            return False
        attributes = raw.get("attributes") or raw.get("metadata") or {}
        return "agent.runtime.version" in attributes

    def normalize(self, trace: SourceTrace, *, context: AdapterContext) -> list[CanonicalSample]:
        raw = mapping_raw(trace)
        attributes = dict(raw.get("attributes") or raw.get("metadata") or {})
        raw_messages = raw.get("messages") or attributes.pop("agent.message.content", None)
        if isinstance(raw_messages, str):
            raw_messages = [raw_messages]
        if not isinstance(raw_messages, list):
            raise AdapterError(
                "content_not_captured",
                "runtime-kit trace has no captured messages; enable content capture for evaluation",
            )
        messages: list[dict[str, Any]] = []
        for value in raw_messages:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError as exc:
                    raise AdapterError(
                        "invalid_message_json", "captured message is invalid JSON"
                    ) from exc
            if not isinstance(value, dict):
                raise AdapterError("invalid_message", "captured message must be an object")
            messages.append(value)
        metadata: dict[str, Any] = {
            "framework": attributes.get("agent.framework"),
            "agent_id": attributes.get("agent.id"),
            "agent_version": attributes.get("agent.version"),
            "session_id": attributes.get("agent.thread.id"),
            "status": raw.get("status"),
            "span_ids": raw.get("span_ids", []),
            "tags": {"runtime_version": str(attributes.get("agent.runtime.version"))},
        }
        return build_samples(
            trace,
            context=context,
            adapter_name=self.name,
            adapter_version=self.version,
            messages=messages,
            metadata=metadata,
        )
