"""Protect the existing JSON rejection behavior and noncyclic aliases."""

import pytest

from product.metadata import validate_metadata


def test_mapping_self_cycle_preserves_value_error_and_input():
    value = {}
    value["self"] = value
    with pytest.raises(ValueError):
        validate_metadata(value)
    assert value["self"] is value
    assert list(value) == ["self"]


def test_list_self_cycle_preserves_value_error_and_input():
    child = []
    child.append(child)
    value = {"child": child}
    with pytest.raises(ValueError):
        validate_metadata(value)
    assert value["child"] is child
    assert child[0] is child


def test_mutual_mapping_cycle_preserves_value_error():
    first = {}
    second = {"first": first}
    first["second"] = second
    with pytest.raises(ValueError):
        validate_metadata(first)
    assert first["second"]["first"] is first


def test_shared_noncyclic_mapping_is_not_a_cycle():
    child = {"ok": [False, 0, None, ""]}
    value = {"first": child, "second": child}
    assert validate_metadata(value) is value
    assert value["first"] is value["second"]
    assert child == {"ok": [False, 0, None, ""]}


def test_shared_noncyclic_list_is_not_a_cycle():
    child = [False, 0, None, ""]
    value = {"first": child, "second": child}
    assert validate_metadata(value) is value
    assert value["first"] is value["second"]
    assert child == [False, 0, None, ""]


def test_valid_call_after_cyclic_rejection_is_unaffected():
    invalid = {}
    invalid["self"] = invalid
    with pytest.raises(ValueError):
        validate_metadata(invalid)
    valid = {"ok": [False, 0, None, ""]}
    assert validate_metadata(valid) is valid
    assert invalid["self"] is invalid
