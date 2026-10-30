"""Primary-owned held-out selection and actual dataset caller acceptance."""

import hashlib
import random
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from evaluation_harness.contracts import DatasetGenerationRequest, SelectionPolicy
from evaluation_harness.datasets.generator import generate_dataset
from evaluation_harness.datasets.selection import select_records
from tests.conftest import load_trace

AT = datetime(2026, 1, 2, tzinfo=UTC)


@dataclass
class Record:
    key: str
    at: datetime = AT


def records():
    return [Record(f"k{i:02}") for i in (7, 1, 10, 3, 0, 9, 4, 11, 2, 8, 6, 5)]


def select(values, policy):
    return select_records(values, policy, identity=lambda r: r.key, timestamp=lambda r: r.at)


@pytest.mark.parametrize("order", ("oldest", "newest"))
def test_tie_break(order):
    values = records()
    before = list(values)
    expected = sorted(values, key=lambda r: r.key, reverse=order == "newest")[:3]
    policy = SelectionPolicy(strategy="limit", limit=3, order=order)
    assert select(values, policy) == expected
    assert select(list(reversed(values)), policy) == expected
    assert values == before


@pytest.mark.parametrize("seed", (0, 7, 42))
def test_random_permutation_replay(seed):
    values = records()
    before = list(values)
    global_state = random.getstate()
    expected = sorted(values, key=lambda r: r.key)
    random.Random(seed).shuffle(expected)
    policy = SelectionPolicy(strategy="random", limit=4, seed=seed)
    actual = select(values, policy)
    assert actual == expected[:4]
    assert select(list(reversed(values)), policy) == actual
    assert all(any(item is original for original in values) for item in actual)
    assert values == before
    assert random.getstate() == global_state


@pytest.mark.parametrize("values", ([], records()))
def test_all_returns_new_list(values):
    result = select(values, SelectionPolicy())
    assert result == values
    assert result is not values


@pytest.mark.parametrize("percentage", (25, 100))
def test_percentage_membership_and_order(percentage):
    values = records()
    policy = SelectionPolicy(strategy="percentage", percentage=percentage, seed=7)
    expected = [
        item
        for item in values
        if int.from_bytes(hashlib.sha256(f"7:{item.key}".encode()).digest()[:8], "big") % 10_000
        < percentage * 100
    ]
    assert select(values, policy) == expected


@pytest.mark.parametrize("size", (0, 1, 12))
def test_limit_boundaries(size):
    values = records()[:size]
    result = select(values, SelectionPolicy(strategy="limit", limit=20, order="oldest"))
    assert result == sorted(values, key=lambda r: (r.at, r.key))


def test_callback_error_propagates():
    error = ValueError("bad timestamp callback")

    def broken(item):
        raise error

    with pytest.raises(ValueError) as caught:
        select_records(
            records(),
            SelectionPolicy(strategy="limit", limit=1),
            identity=lambda r: r.key,
            timestamp=broken,
        )
    assert caught.value is error
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("strategy", ("limit", "random"))
def test_actual_dataset_selection_roundtrip(application, strategy):
    traces = [load_trace("generic_multi_turn.json", trace_id=r.key) for r in records()]
    policy = SelectionPolicy(strategy=strategy, limit=4, order="newest", seed=7)
    # The exact policy input form crosses the real request/generator boundary.
    request = DatasetGenerationRequest(
        application_id=application.application_id,
        name="selection-trial",
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        end_time=datetime(2026, 1, 3, tzinfo=UTC),
        row_mode="trace",
        selection=policy.model_dump(mode="json"),
        adapter_name="generic-otel",
        adapter_version="1.0.0",
    )
    kwargs = dict(
        dataset_id="selection-trial",
        version=1,
        source_name="fixture",
        application=application,
        request=request,
        adapter=GenericOtelAdapter(),
        created_at=AT,
    )
    before = [trace.model_dump(mode="json") for trace in traces]
    first = generate_dataset(traces=traces, **kwargs)
    second = generate_dataset(traces=list(reversed(traces)), **kwargs)
    assert first.manifest.manifest_hash == second.manifest.manifest_hash
    assert first.manifest.selection == policy
    assert first.manifest.accepted_count == 4
    assert first.manifest.rejected_count == 0
    assert first.manifest.sample_ids == second.manifest.sample_ids
    assert [trace.model_dump(mode="json") for trace in traces] == before


@pytest.mark.parametrize("payload", ({"strategy": "random"}, {"strategy": "limit", "limit": 0}))
def test_invalid_policy_is_rejected(payload):
    with pytest.raises(ValidationError):
        SelectionPolicy.model_validate(payload)
