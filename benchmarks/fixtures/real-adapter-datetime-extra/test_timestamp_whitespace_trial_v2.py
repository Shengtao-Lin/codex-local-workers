"""Primary-owned isolated feature acceptance; not a production change request."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from evaluation_harness.adapters.base import AdapterContext
from evaluation_harness.adapters.common import _datetime
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from tests.conftest import load_trace

DEFAULT = datetime(2000, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" \t2026-01-02T12:00:00Z\r\n", datetime(2026, 1, 2, 12, tzinfo=UTC)),
        ("\n2026-01-02T12:00:00\t", datetime(2026, 1, 2, 12, tzinfo=UTC)),
        (
            " 2026-01-02T12:00:00+05:30 ",
            datetime.fromisoformat("2026-01-02T12:00:00+05:30"),
        ),
    ],
)
def test_padded_timestamp(value, expected):
    actual = _datetime(value, DEFAULT)
    assert actual == expected
    assert actual.hour == 12
    assert actual.utcoffset() == expected.utcoffset()


@pytest.mark.parametrize("value", ["", " \t\r\n", " bad ", " 2026-13-02 ", "2026-01-02T12:0 0:00Z"])
def test_invalid_padded_timestamp_raises(value):
    with pytest.raises(ValueError):
        _datetime(value, DEFAULT)


@pytest.mark.parametrize("row_mode", ["trace", "turn"])
def test_padded_timestamp_adapter_roundtrip(application, row_mode):
    adapter = GenericOtelAdapter()
    context = AdapterContext(application=application, row_mode=row_mode)
    trace = load_trace("generic_multi_turn.json")
    trace.raw["metadata"]["event_time"] = "2026-01-02T12:00:00+05:30"
    expected = adapter.normalize(trace, context=context)
    trace.raw["metadata"]["event_time"] = " \t2026-01-02T12:00:00+05:30\r\n"
    before = deepcopy(trace.raw)
    actual = adapter.normalize(trace, context=context)
    assert trace.raw == before
    assert len(actual) == (1 if row_mode == "trace" else 2)
    for sample, original in zip(actual, expected, strict=True):
        assert sample.model_dump(
            exclude={"source_metadata": {"event_time"}}
        ) == original.model_dump(exclude={"source_metadata": {"event_time"}})
        assert sample.source_metadata["event_time"] == before["metadata"]["event_time"]
        assert sample.sample_id == original.sample_id
        assert sample.event_time.hour == 12
        assert sample.event_time.utcoffset() == timedelta(hours=5, minutes=30)
        serialized = sample.model_dump(mode="json")["event_time"]
        assert datetime.fromisoformat(serialized) == original.event_time


def test_existing_identity_and_fallback():
    aware = datetime(2026, 1, 1, tzinfo=UTC)
    for value in (aware.replace(tzinfo=None), aware):
        assert _datetime(value, DEFAULT) is value
    for value in (None, False, 0, {}, [], object()):
        assert _datetime(value, DEFAULT) is DEFAULT
