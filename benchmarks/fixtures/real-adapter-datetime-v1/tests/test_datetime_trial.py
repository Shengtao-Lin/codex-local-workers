"""Primary-owned acceptance for the real adapter's private timestamp helper."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from evaluation_harness.adapters.base import AdapterContext
from evaluation_harness.adapters.common import _datetime
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from tests.conftest import load_trace

DEFAULT = datetime(2000, 1, 1, tzinfo=UTC)


def test_datetime_identity():
    aware = datetime(2026, 1, 1, tzinfo=UTC)
    for value in (aware.replace(tzinfo=None), aware):
        assert _datetime(value, DEFAULT) is value


def test_utc_suffix():
    assert _datetime("2026-01-02T12:00:00Z", DEFAULT) == datetime(
        2026, 1, 2, 12, tzinfo=UTC
    )


def test_offset_preserved():
    parsed = _datetime("2026-01-02T12:00:00+05:30", DEFAULT)
    assert parsed.utcoffset() == timedelta(hours=5, minutes=30)
    assert parsed.hour == 12


def test_naive_string_utc():
    parsed = _datetime("2026-01-02T12:00:00", DEFAULT)
    assert parsed == datetime(2026, 1, 2, 12, tzinfo=UTC)
    assert parsed.tzinfo is UTC


def test_fallback_identity():
    for value in (None, False, 0, {}, [], object()):
        assert _datetime(value, DEFAULT) is DEFAULT


def test_invalid_string():
    for value in ("", "bad", "2026-13-02", " "):
        with pytest.raises(ValueError):
            _datetime(value, DEFAULT)


def test_real_adapter_roundtrip(application):
    adapter = GenericOtelAdapter()
    for row_mode, expected_rows in (("trace", 1), ("turn", 2)):
        context = AdapterContext(application=application, row_mode=row_mode)
        trace = load_trace("generic_multi_turn.json")
        original = adapter.normalize(trace, context=context)
        original_ids = [sample.sample_id for sample in original]
        assert len(original) == expected_rows
        for value, expected in (
            ("2026-01-02T12:00:00", datetime(2026, 1, 2, 12, tzinfo=UTC)),
            ("2026-01-02T12:00:00Z", datetime(2026, 1, 2, 12, tzinfo=UTC)),
            (None, trace.observed_at),
            (0, trace.observed_at),
        ):
            trace.raw["metadata"]["event_time"] = value
            before = deepcopy(trace.raw)
            samples = adapter.normalize(trace, context=context)
            assert trace.raw == before
            assert len(samples) == expected_rows
            assert [sample.sample_id for sample in samples] == original_ids
            for sample in samples:
                assert sample.event_time == expected
                assert sample.event_time.tzinfo is not None
                assert sample.source_trace_id == trace.source_trace_id
                assert sample.runtime.framework == "fictional"
                assert sample.input_messages[0].role == "user"
                assert sample.output_messages[0].role == "assistant"
                serialized = sample.model_dump(mode="json")["event_time"]
                assert (
                    datetime.fromisoformat(serialized.replace("Z", "+00:00"))
                    == expected
                )
        for invalid in ("bad", "2026-13-02"):
            trace.raw["metadata"]["event_time"] = invalid
            before = deepcopy(trace.raw)
            with pytest.raises(ValueError):
                adapter.normalize(trace, context=context)
            assert trace.raw == before
