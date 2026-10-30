from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from evaluation_harness.contracts import ApplicationSpec
from evaluation_harness.trace_sources.base import SourceTrace

FIXTURES = Path(__file__).parent / "fixtures" / "synthetic_traces"


@pytest.fixture
def application() -> ApplicationSpec:
    return ApplicationSpec(
        application_id="synthetic-support",
        display_name="Synthetic Support",
        environment="test",
        trace_source_id="mlflow",
        adapter_name="generic-otel",
        adapter_version="1.0.0",
        source_filter={},
    )


def load_trace(name: str, *, trace_id: str = "trace-1") -> SourceTrace:
    return SourceTrace(
        source_trace_id=trace_id,
        source_revision="1",
        observed_at=datetime(2026, 1, 2, 12, tzinfo=UTC),
        raw=json.loads((FIXTURES / name).read_text(encoding="utf-8")),
    )
