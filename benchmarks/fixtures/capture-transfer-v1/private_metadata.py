import pytest

from product.metadata import MAX_METADATA_BYTES, validate_metadata


def test_exact_byte_boundary_and_late_failure_nonmutation():
    text = "x" * (MAX_METADATA_BYTES - len('{"k":""}'))
    value = {"k": text}
    assert validate_metadata(value) is value
    value["k"] += "x"
    before = dict(value)
    with pytest.raises(ValueError):
        validate_metadata(value)
    assert value == before


@pytest.mark.parametrize("invalid", [float("-inf"), float("nan"), float("inf")])
def test_nested_nonfinite(invalid):
    with pytest.raises(ValueError):
        validate_metadata({"deep": [{"x": [invalid]}]})


def test_json_values_are_not_filtered_as_falsy():
    value = {"nested": {"no": False, "zero": 0, "empty": [], "none": None}}
    assert validate_metadata(value) is value
