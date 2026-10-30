import pytest

from product.core import parse_count
from product.entry import load_count


def test_load_count_negative():
    with pytest.raises(ValueError, match="^count must be nonnegative$"):
        load_count(-1)


def test_load_count_core_negative():
    with pytest.raises(ValueError, match="^count must be nonnegative$"):
        parse_count(-2)


def test_load_count_other_errors():
    for value in (True, "2", None):
        with pytest.raises(TypeError, match="^count must be integer$"):
            load_count(value)


def test_load_count_valid():
    assert load_count(0) == 0
    assert parse_count(7) == 7
