from copy import deepcopy

import pytest

from evaluation_harness.adapters.base import AdapterError
from evaluation_harness.adapters.common import parse_message


def test_dictionary_and_list_roundtrip_with_optional_message_fields():
    value = {
        "message_id": "legacy-id",
        "role": "tool",
        "name": "worker",
        "tool_call_id": "outer",
        "content": {
            "type": "tool_result",
            "call_id": "inner",
            "result": {"x": [False, 0, None]},
        },
    }
    before = deepcopy(value)
    actual = parse_message("trace", 2, value)
    expected = parse_message("trace", 2, {**value, "content": [value["content"]]})
    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
    assert actual.message_id == "legacy-id" and actual.name == "worker"
    assert value == before


def test_legacy_multipart_and_invalid_nested_part():
    actual = parse_message(
        "trace",
        0,
        {
            "role": "assistant",
            "content": [{"text": "one"}, {"type": "text", "text": "two"}],
        },
    )
    assert len(actual.content) == 2
    with pytest.raises(AdapterError):
        parse_message("trace", 0, {"role": "assistant", "content": [None]})
