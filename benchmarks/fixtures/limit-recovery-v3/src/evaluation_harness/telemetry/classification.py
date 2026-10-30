"""Defense-in-depth classification for evaluator-owned traces."""

from __future__ import annotations

from typing import Any


def is_internal_trace(raw: Any, *, service_names: set[str] | None = None) -> bool:
    if not isinstance(raw, dict):
        return False
    attributes = raw.get("attributes") or raw.get("metadata") or {}
    resource = raw.get("resource") or {}
    service_name = resource.get("service.name") or attributes.get("service.name")
    internal_services = service_names or {"evaluation-api", "evaluation-worker"}
    return bool(
        attributes.get("evaluation.internal") is True
        or attributes.get("evaluation.source") in {"evaluator", "worker", "api"}
        or service_name in internal_services
    )
