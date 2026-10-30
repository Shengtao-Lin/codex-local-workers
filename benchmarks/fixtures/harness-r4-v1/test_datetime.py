from datetime import UTC, datetime, timedelta, timezone

import pytest
from evaluation_harness.adapters.common import _datetime


def test_datetime_identity_and_missing_values():
    default = datetime(2000, 1, 1, tzinfo=UTC)
    existing = datetime(2020, 1, 1)  # noqa: DTZ001 - naive identity is the contract
    assert _datetime(existing, default) is existing
    for value in (None, 0, False, [], {}):
        assert _datetime(value, default) is default


def test_string_timezone_semantics():
    default = datetime(2000, 1, 1, tzinfo=UTC)
    assert _datetime("2020-01-02T03:04:05Z", default).tzinfo == UTC
    assert _datetime("2020-01-02T03:04:05", default).tzinfo == UTC
    offset = timezone(timedelta(hours=3))
    assert _datetime("2020-01-02T03:04:05+03:00", default).tzinfo == offset


@pytest.mark.parametrize("value", ["", "nonsense", "2020-02-31"])
def test_invalid_string_is_not_silently_defaulted(value):
    with pytest.raises(ValueError):
        _datetime(value, datetime(2000, 1, 1, tzinfo=UTC))
