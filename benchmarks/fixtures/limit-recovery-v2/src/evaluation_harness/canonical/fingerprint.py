"""Stable sample identities and content fingerprints."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from evaluation_harness.canonical.models import CanonicalSample

VOLATILE_CONTENT_FIELDS = {"sample_id", "labels", "source_metadata"}


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def make_sample_id(
    *,
    workspace_id: str = "default",
    application_id: str,
    environment: str,
    source_trace_id: str,
    source_revision: str | None,
    row_mode: str,
    turn_index: int | None,
    adapter_name: str,
    adapter_version: str,
    schema_version: str = "1.0",
) -> str:
    identity = {
        "adapter_name": adapter_name,
        "adapter_version": adapter_version,
        "application_id": application_id,
        "environment": environment,
        "row_mode": row_mode,
        "schema_version": schema_version,
        "workspace_id": workspace_id,
        "source_revision": source_revision,
        "source_trace_id": source_trace_id,
        "turn_index": turn_index,
    }
    return "smp_" + hashlib.sha256(canonical_json(identity)).hexdigest()[:32]


def content_fingerprint(sample: CanonicalSample) -> str:
    content = sample.model_dump(mode="json", exclude=VOLATILE_CONTENT_FIELDS)
    return hashlib.sha256(canonical_json(content)).hexdigest()
