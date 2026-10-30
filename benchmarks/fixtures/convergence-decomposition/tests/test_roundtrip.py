from product.consumer import lookup
from product.producer import normalize_key


def test_exact_whitespace_roundtrip():
    assert normalize_key("  item \t") == "item"
    assert lookup({"item": 0}, "  item \t") == 0


def test_rejection_and_mapping_not_mutated():
    import pytest

    mapping = {"item": None}
    assert lookup(mapping, "item") is None
    assert mapping == {"item": None}
    for key in (None, 4, "   "):
        with pytest.raises((TypeError, ValueError)):
            normalize_key(key)
