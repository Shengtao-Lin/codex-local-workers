from copy import deepcopy

import pytest

from evaluation_harness.adapters.base import AdapterError
from evaluation_harness.adapters.common import parse_message


def test_single_text_part_matches_legacy_list():
    value = {
        "id": "message-1",
        "role": "assistant",
        "content": {"type": "text", "text": "hi"},
    }
    before = deepcopy(value)
    actual = parse_message("trace", 0, value)
    legacy = parse_message("trace", 0, {**value, "content": [value["content"]]})
    assert actual.model_dump(mode="json") == legacy.model_dump(mode="json")
    assert value == before


@pytest.mark.parametrize("result", [None, False, 0, "", [], {}])
def test_single_result_keeps_falsy_values(result):
    actual = parse_message(
        "trace",
        0,
        {
            "role": "tool",
            "content": {
                "type": "tool_result",
                "tool_call_id": "call-1",
                "result": result,
            },
        },
    )
    assert actual.content[0].model_dump(mode="json")["result"] == result


def test_tool_call_and_legacy_string_still_work():
    actual = parse_message(
        "trace",
        1,
        {
            "role": "assistant",
            "content": {
                "type": "tool_call",
                "tool_call": {"id": "a", "name": "lookup", "arguments": {"n": 0}},
            },
        },
    )
    assert actual.content[0].model_dump(mode="json")["arguments"] == {"n": 0}
    assert (
        parse_message("trace", 0, {"role": "user", "content": "hello"}).content[0].type
        == "text"
    )


@pytest.mark.parametrize(
    "value",
    [
        {"role": "bad", "content": "x"},
        {"role": "user", "content": {"type": "unknown"}},
        {"role": "user", "content": 0},
    ],
)
def test_invalid_shapes_still_reject(value):
    with pytest.raises(AdapterError):
        parse_message("trace", 0, value)
