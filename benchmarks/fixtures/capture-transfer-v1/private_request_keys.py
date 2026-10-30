import hashlib

from product.encoding import canonical_json
from product.request_keys import request_hash


def test_only_exact_top_level_transport_keys_are_ignored():
    payload = {
        "request_id": 0,
        "submitted_at": None,
        "Request_id": False,
        "body": {"request_id": 1},
        "zero": 0,
        "none": None,
    }
    kept = {"Request_id": False, "body": {"request_id": 1}, "zero": 0, "none": None}
    assert request_hash(payload) == hashlib.sha256(canonical_json(kept)).hexdigest()
    assert request_hash({"value": False}) != request_hash({"value": 0})
    assert request_hash({"value": None}) != request_hash({})


def test_nested_order_and_unicode():
    first = {"body": {"文": [0, False, None], "a": 1}, "request_id": "old"}
    second = {"submitted_at": "new", "body": {"a": 1, "文": [0, False, None]}}
    assert request_hash(first) == request_hash(second)
