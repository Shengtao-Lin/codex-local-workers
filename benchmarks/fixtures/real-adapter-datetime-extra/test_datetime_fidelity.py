"""Protected semantic equivalence checks for the original private helper."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from evaluation_harness.adapters import common
from evaluation_harness.adapters.base import AdapterContext
from evaluation_harness.adapters.generic_otel import GenericOtelAdapter
from tests.conftest import load_trace

DEFAULT = datetime(2000, 1, 1, tzinfo=UTC)
INVALID = ("", "bad", "2026-13-02", "2026-02-29", "2024-02-30", " ")
VALID = (
    "2024-02-29",
    "2024-02-29T23:59:59.123456Z",
    "2026-01-02T12:00:00-03:30",
    "2026-01-02T12:00:00+00:00",
    "2026-01-02 12:00:00",
    "2026-01-02T12:00:00+14:00",
)


def native_error(value):
    with pytest.raises(ValueError) as caught:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    return caught.value


def assert_original_error(actual, expected):
    assert type(actual) is type(expected)
    assert actual.args == expected.args
    assert str(actual) == str(expected)
    assert actual.__cause__ is None
    assert actual.__context__ is None


@pytest.mark.parametrize("value", INVALID)
def test_error_fidelity(value):
    expected = native_error(value)
    with pytest.raises(ValueError) as caught:
        common._datetime(value, DEFAULT)
    assert_original_error(caught.value, expected)


def test_exception_identity(monkeypatch):
    original = ValueError("sentinel parse error")

    class Parser(datetime):
        @classmethod
        def fromisoformat(cls, value):
            raise original

    monkeypatch.setattr(common, "datetime", Parser)
    with pytest.raises(ValueError) as caught:
        common._datetime("bad", DEFAULT)
    assert caught.value is original


@pytest.mark.parametrize("value", VALID)
def test_additional_timestamp_forms(value):
    expected = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if expected.tzinfo is None:
        expected = expected.replace(tzinfo=UTC)
    actual = common._datetime(value, DEFAULT)
    assert actual.isoformat() == expected.isoformat()


@pytest.mark.parametrize("row_mode", ("trace", "turn"))
@pytest.mark.parametrize("value", INVALID)
def test_adapter_error_fidelity(application, row_mode, value):
    trace = load_trace("generic_multi_turn.json")
    trace.raw["metadata"]["event_time"] = value
    before = deepcopy(trace.raw)
    with pytest.raises(ValueError) as caught:
        GenericOtelAdapter().normalize(
            trace, context=AdapterContext(application=application, row_mode=row_mode)
        )
    assert_original_error(caught.value, native_error(value))
    assert trace.raw == before


@pytest.mark.parametrize("row_mode", ("trace", "turn"))
@pytest.mark.parametrize("value", VALID)
def test_adapter_additional_timestamp_forms(application, row_mode, value):
    trace = load_trace("generic_multi_turn.json")
    trace.raw["metadata"]["event_time"] = value
    before = deepcopy(trace.raw)
    expected = common._datetime(value, DEFAULT)
    samples = GenericOtelAdapter().normalize(
        trace, context=AdapterContext(application=application, row_mode=row_mode)
    )
    assert len(samples) == (1 if row_mode == "trace" else 2)
    assert trace.raw == before
    for sample in samples:
        assert sample.event_time.isoformat() == expected.isoformat()
        assert sample.model_dump(mode="json")["event_time"]
