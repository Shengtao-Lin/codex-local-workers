import hashlib
from copy import deepcopy

from product.encoding import canonical_json
from product.request_keys import request_hash


def test_top_level_transport_metadata_does_not_change_identity():
    payload = {"task": "score", "inputs": [False, 0, None]}
    assert request_hash(payload) == request_hash(
        {**payload, "request_id": "new", "submitted_at": "later"}
    )
    assert request_hash(payload) == hashlib.sha256(canonical_json(payload)).hexdigest()


def test_nested_values_remain_significant_and_input_unchanged():
    payload = {
        "request_id": "drop",
        "nested": {"request_id": "keep", "submitted_at": 0},
    }
    before = deepcopy(payload)
    value = request_hash(payload)
    assert payload == before
    assert value != request_hash(
        {"nested": {"request_id": "changed", "submitted_at": 0}}
    )
    assert len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def test_order_and_empty_payload_are_stable():
    assert request_hash({"b": 2, "a": 1}) == request_hash({"a": 1, "b": 2})
    assert request_hash({}) == request_hash({"request_id": None, "submitted_at": False})
