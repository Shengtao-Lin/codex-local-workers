"""Primary-owned acceptance tests for an additive real-project slice."""

import ast
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluation_harness.trace_sources.base import SourceTrace
from evaluation_harness.trace_sources.mlflow import MlflowTraceSource


def trace(trace_id: str, raw: object) -> SourceTrace:
    return SourceTrace(
        source_trace_id=trace_id, observed_at=datetime(2026, 1, 1, tzinfo=UTC), raw=raw
    )


@pytest.mark.parametrize("raw", [None, False, 0, ""])
def test_batch_preserves_order_duplicates_and_identity(raw: object) -> None:
    source = MlflowTraceSource(tracking_uri="unused", experiment_id="unused")
    events: list[tuple[str, str]] = []
    outputs = [trace("b", raw), trace("a", {"nested": [1]}), trace("b", raw)]

    async def get(trace_id: str) -> SourceTrace:
        index = len([item for item in events if item[0] == "start"])
        events.append(("start", trace_id))
        await asyncio.sleep(0)
        events.append(("end", trace_id))
        return outputs[index]

    source.get = get
    ids = ["b", "a", "b"]
    result = asyncio.run(source.get_many(ids))
    assert ids == ["b", "a", "b"]
    assert len(result) == 3
    assert all(actual is expected for actual, expected in zip(result, outputs, strict=True))
    assert events == [(phase, key) for key in ids for phase in ("start", "end")]
    assert result[0].raw is raw


def test_empty_batch_does_not_get_and_returns_fresh_list() -> None:
    source = MlflowTraceSource(tracking_uri="unused", experiment_id="unused")

    async def unexpected(trace_id: str) -> SourceTrace:
        raise AssertionError(f"Unexpected get: {trace_id}")

    source.get = unexpected
    first = asyncio.run(source.get_many([]))
    second = asyncio.run(source.get_many([]))
    assert first == second == []
    assert first is not second


@pytest.mark.parametrize("error_type", [RuntimeError, asyncio.CancelledError])
def test_batch_stops_and_propagates_identical_exception(
    error_type: type[BaseException],
) -> None:
    source = MlflowTraceSource(tracking_uri="unused", experiment_id="unused")
    seen: list[str] = []
    error = error_type("same instance")

    async def get(trace_id: str) -> SourceTrace:
        seen.append(trace_id)
        await asyncio.sleep(0)
        if trace_id == "fail":
            raise error
        return trace(trace_id, False)

    source.get = get
    ids = ["ok", "fail", "unvisited"]
    with pytest.raises(error_type) as caught:
        asyncio.run(source.get_many(ids))
    assert caught.value is error
    assert seen == ["ok", "fail"]
    assert ids == ["ok", "fail", "unvisited"]


def test_batch_roundtrip_uses_real_get_and_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = MlflowTraceSource(tracking_uri="unused", experiment_id="experiment")
    seen: list[str] = []

    def get_trace(trace_id: str) -> SimpleNamespace:
        seen.append(trace_id)
        return SimpleNamespace(
            info=SimpleNamespace(trace_id=trace_id, timestamp_ms=1000, last_update_time_ms=2),
            to_json=lambda: json.dumps({"value": trace_id, "data": {"spans": []}}),
        )

    monkeypatch.setattr(source, "_client", lambda: SimpleNamespace(get_trace=get_trace))
    ids = ["b", "a", "b"]
    result = asyncio.run(source.get_many(ids))
    assert seen == ids
    assert [item.source_trace_id for item in result] == ids
    assert all(item.source_revision == "2" for item in result)
    assert all(item.observed_at == datetime.fromtimestamp(1, tz=UTC) for item in result)
    assert [item.raw for item in result] == [{"value": key, "data": {"spans": []}} for key in ids]


def test_legacy_members_are_unchanged() -> None:
    path = Path("src/evaluation_harness/trace_sources/mlflow.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    expected = json.loads(Path("tests/legacy_members.json").read_text(encoding="utf-8"))
    actual = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MlflowTraceSource":
            for member in node.body:
                if (
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name != "get_many"
                ):
                    actual["MlflowTraceSource." + member.name] = hashlib.sha256(
                        ast.dump(member, include_attributes=False).encode()
                    ).hexdigest()
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            actual[node.name] = hashlib.sha256(
                ast.dump(node, include_attributes=False).encode()
            ).hexdigest()
    assert actual == expected
