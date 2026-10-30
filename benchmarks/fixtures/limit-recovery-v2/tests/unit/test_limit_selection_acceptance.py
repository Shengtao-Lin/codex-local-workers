"""Primary-owned compatibility and bounded-selection acceptance tests."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest

from evaluation_harness.contracts import DatasetGenerationRequest, SelectionPolicy
from evaluation_harness.datasets import generator
from evaluation_harness.datasets.selection import select_records
from tests.conftest import load_trace


@dataclass(eq=False)
class Record:
    key: str
    at: datetime


def old_limit(records: list[Record], policy: SelectionPolicy) -> list[Record]:
    ordered = sorted(records, key=lambda item: (item.at, item.key))
    if policy.order == "newest":
        ordered.reverse()
    return ordered[: policy.limit]


@pytest.mark.parametrize("order", ["oldest", "newest"])
@pytest.mark.parametrize("limit", [1, 7, 100])
@pytest.mark.parametrize("size", [0, 1, 40])
def test_limit_preserves_exact_legacy_order_and_identity(order: str, limit: int, size: int):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    records = [Record(str(i % 3), start + timedelta(seconds=i % 4)) for i in range(size)]
    random.Random(73).shuffle(records)
    before = [(id(item), item.key, item.at) for item in records]
    policy = SelectionPolicy.model_validate({"strategy": "limit", "order": order, "limit": limit})

    actual = select_records(records, policy, identity=lambda r: r.key, timestamp=lambda r: r.at)

    assert [id(item) for item in actual] == [id(item) for item in old_limit(records, policy)]
    assert actual is not records
    assert [(id(item), item.key, item.at) for item in records] == before


@pytest.mark.parametrize("failing_callback", ["timestamp", "identity"])
def test_limit_preserves_callback_order_and_original_exception(failing_callback: str):
    records = [Record(str(i), datetime(2026, 1, 1, tzinfo=UTC)) for i in range(4)]
    events: list[tuple[str, str]] = []
    cause = KeyError("original cause")
    failure = ValueError("original callback failure")
    failure.__cause__ = cause

    def timestamp(record: Record) -> datetime:
        events.append(("timestamp", record.key))
        if record.key == "2" and failing_callback == "timestamp":
            raise failure
        return record.at

    def identity(record: Record) -> str:
        events.append(("identity", record.key))
        if record.key == "2" and failing_callback == "identity":
            raise failure
        return record.key

    with pytest.raises(ValueError, match=r"^original callback failure$") as caught:
        select_records(
            records,
            SelectionPolicy(strategy="limit", limit=1),
            timestamp=timestamp,
            identity=identity,
        )

    expected = [(kind, str(i)) for i in range(2) for kind in ("timestamp", "identity")]
    expected.append(("timestamp", "2"))
    if failing_callback == "identity":
        expected.append(("identity", "2"))
    assert events == expected
    assert caught.value is failure and caught.value.__cause__ is cause


class CountedKey(str):
    comparisons: ClassVar[int] = 0
    callbacks: ClassVar[list[tuple[str, str]]] = []
    expected_callbacks: ClassVar[int] = 0

    def __lt__(self, other: str) -> bool:
        # Legacy sorted evaluates every key before any comparisons occur.
        assert len(self.callbacks) == self.expected_callbacks
        type(self).comparisons += 1
        return super().__lt__(other)


@pytest.mark.parametrize("order", ["oldest", "newest"])
def test_small_limit_avoids_full_sort_and_preserves_key_evaluation(order: str):
    records = [Record(CountedKey(f"{i:06}"), datetime(2026, 1, 1, tzinfo=UTC)) for i in range(4096)]
    random.Random(18).shuffle(records)
    policy = SelectionPolicy.model_validate({"strategy": "limit", "limit": 8, "order": order})
    CountedKey.callbacks = []
    CountedKey.expected_callbacks = 8192
    CountedKey.comparisons = 0

    def timestamp(record: Record) -> datetime:
        CountedKey.callbacks.append(("timestamp", record.key))
        return record.at

    def identity(record: Record) -> str:
        CountedKey.callbacks.append(("identity", record.key))
        return record.key

    selected = select_records(records, policy, timestamp=timestamp, identity=identity)

    assert CountedKey.comparisons < 12000
    assert CountedKey.callbacks == [
        (kind, record.key) for record in records for kind in ("timestamp", "identity")
    ]
    assert [id(record) for record in selected] == [
        id(record) for record in old_limit(records, policy)
    ]


def test_serialized_selection_round_trip_preserves_generated_dataset(application, monkeypatch):
    from evaluation_harness.adapters.generic_otel import GenericOtelAdapter

    traces = [load_trace("generic_multi_turn.json", trace_id=f"trace-{i}") for i in range(20)]
    before = [trace.model_dump(mode="json") for trace in traces]
    request = DatasetGenerationRequest(
        application_id=application.application_id,
        name="limited",
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 3, tzinfo=UTC),
        adapter_name="generic-otel",
        adapter_version="1.0.0",
        row_mode="trace",
        selection=SelectionPolicy(strategy="limit", limit=3, order="newest"),
    )
    request = DatasetGenerationRequest.model_validate_json(request.model_dump_json())
    kwargs = dict(
        dataset_id="ds-limit",
        version=1,
        source_name="fixture",
        application=application,
        request=request,
        adapter=GenericOtelAdapter(),
        traces=traces,
        created_at=datetime(2026, 1, 3, tzinfo=UTC),
    )
    actual = generator.generate_dataset(**kwargs)

    def legacy(records, policy, *, identity, timestamp):
        ordered = sorted(records, key=lambda item: (timestamp(item), identity(item)))
        if policy.order == "newest":
            ordered.reverse()
        return ordered[: policy.limit]

    monkeypatch.setattr(generator, "select_records", legacy)
    expected = generator.generate_dataset(**kwargs)
    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
    assert [trace.model_dump(mode="json") for trace in traces] == before
