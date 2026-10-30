"""Protected public behavior for the real runtime output mapping slice."""

from copy import deepcopy
from uuid import UUID

import pytest

from agent_runtime.adapters.mapping import messages_output
from agent_runtime.models import (
    InvocationInput,
    Message,
    RuntimeContext,
)


def message(role="assistant", content=None):
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "role": role,
        "content": content or [{"type": "text", "text": "hello"}],
    }


def request():
    return InvocationInput(
        context=RuntimeContext(run_id=UUID(int=2), thread_id=UUID(int=3)),
        messages=[Message.model_validate(message("user"))],
    )


def test_mapping_singleton_matches_sequence_and_does_not_mutate():
    raw = {"messages": message()}
    before = deepcopy(raw)
    req = request()
    req_before = req.model_dump()
    actual = messages_output(raw, req)
    expected = messages_output({"messages": [message()]}, req)
    assert actual.model_dump() == expected.model_dump()
    assert raw == before and req.model_dump() == req_before


def test_typed_singleton_and_direct_identity():
    typed = Message.model_validate(message())
    output = messages_output({"messages": typed}, request())
    assert output.messages[0] is typed
    assert messages_output(typed, request()).messages[0] is typed
    assert messages_output(output, request()) is output


@pytest.mark.parametrize("constructor", [list, tuple])
def test_existing_sequences_keep_order(constructor):
    first = message("user")
    second = message()
    second["id"] = "00000000-0000-0000-0000-000000000004"
    value = constructor([first, second])
    actual = messages_output({"messages": value}, request())
    assert [item.role for item in actual.messages] == ["user", "assistant"]
    assert str(actual.messages[1].id) == second["id"]


@pytest.mark.parametrize("result", [None, False, 0, "", [], {}])
def test_singleton_tool_result_preserves_falsy_values(result):
    raw = {
        "messages": message(
            "tool", [{"type": "tool_result", "tool_call_id": "call", "result": result}]
        )
    }
    before = deepcopy(raw)
    actual = messages_output(raw, request())
    part = actual.messages[0].content[0]
    assert part.type == "tool_result" and part.result == result
    assert type(part.result) is type(result)
    assert raw == before


@pytest.mark.parametrize("value", [None, False, 0, "text", b"text"])
def test_unsupported_message_scalars_keep_type_error(value):
    with pytest.raises(TypeError):
        messages_output({"messages": value}, request())


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        {"role": "unknown"},
        message("user", [{"type": "tool_result", "tool_call_id": "a", "result": None}]),
    ],
)
def test_invalid_canonical_messages_rejected_without_mutation(value):
    raw = {"messages": value}
    before = deepcopy(raw)
    with pytest.raises(ValueError):
        messages_output(raw, request())
    assert raw == before


def test_invalid_metadata_still_rejected():
    with pytest.raises(TypeError):
        messages_output({"messages": message(), "metadata": []}, request())


def test_missing_messages_key_not_alias_of_message():
    with pytest.raises(TypeError):
        messages_output({"message": message()}, request())
