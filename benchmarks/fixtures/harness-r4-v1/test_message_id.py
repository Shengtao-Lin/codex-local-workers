import copy

from evaluation_harness.adapters.common import stable_message_id


def test_supplied_precedence_and_fallback():
    assert stable_message_id("s", 2, {"id": "a", "message_id": "b"}) == "a"
    assert stable_message_id("s", 2, {"id": 0, "message_id": 7}) == "7"
    assert stable_message_id("s", 2, {"id": "", "message_id": "b"}) == "b"


def test_stability_order_and_no_mutation():
    payload = {"role": "assistant", "content": {"b": 2, "a": False}}
    before = copy.deepcopy(payload)
    first = stable_message_id("trace", 0, payload)
    assert first == "msg_trace_0_62126583b9e6a9a9"
    assert payload == before
    assert stable_message_id("trace", 1, payload) != first
    assert stable_message_id("other", 0, payload) != first


def test_json_serialization_failure_propagates():
    import pytest

    circular = {}
    circular["cycle"] = circular
    with pytest.raises(ValueError):
        stable_message_id("s", 1, circular)
