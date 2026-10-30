from copy import deepcopy

import pytest

from product.metadata import validate_metadata


def test_valid_metadata_is_returned_without_copy_or_mutation():
    value = {
        "empty": "",
        "zero": 0,
        "false": False,
        "none": None,
        "nested": [1, {"x": "中文"}],
    }
    before = deepcopy(value)
    assert validate_metadata(value) is value
    assert value == before


@pytest.mark.parametrize(
    "value", [{"x": float("nan")}, {"x": [1, {"y": float("inf")}]}]
)
def test_nonfinite_metadata_rejected(value):
    with pytest.raises(ValueError):
        validate_metadata(value)


@pytest.mark.parametrize("value", [{"": 1}, {"x" * 129: 1}, {"x": b"not-json"}])
def test_invalid_metadata_rejected(value):
    with pytest.raises(ValueError):
        validate_metadata(value)


def test_limits_use_encoded_bytes_and_key_count():
    with pytest.raises(ValueError):
        validate_metadata({str(i): i for i in range(65)})
    with pytest.raises(ValueError):
        validate_metadata({"text": "界" * 6000})
    assert len(validate_metadata({str(i): i for i in range(64)})) == 64
