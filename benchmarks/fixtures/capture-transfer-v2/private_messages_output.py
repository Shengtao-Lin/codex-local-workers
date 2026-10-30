"""Withheld protection of metadata and real canonical type interactions."""

from collections import UserDict
from copy import deepcopy
from uuid import UUID

import pytest

from agent_runtime.adapters.mapping import messages_output
from agent_runtime.models import InvocationInput, Message, RuntimeContext


def req():
    return InvocationInput(
        context=RuntimeContext(run_id=UUID(int=2), thread_id=UUID(int=3)),
        messages=[Message(role="user", content=[{"type": "text", "text": "x"}])],
    )


def raw_message():
    return {
        "id": str(UUID(int=1)),
        "role": "assistant",
        "content": [
            {
                "type": "tool_call",
                "tool_call": {
                    "id": "call",
                    "name": "tool",
                    "arguments": {"falsy": [None, False, 0, "", [], {}]},
                },
            }
        ],
    }


def test_custom_mappings_metadata_coercion_and_arguments():
    raw = UserDict(
        {
            "messages": UserDict(raw_message()),
            "metadata": UserDict({7: False, "empty": [], "nil": None}),
        }
    )
    before = deepcopy(raw)
    actual = messages_output(raw, req())
    assert actual.metadata == {"7": False, "empty": [], "nil": None}
    part = actual.messages[0].content[0]
    assert part.type == "tool_call"
    assert part.tool_call.arguments == {"falsy": [None, False, 0, "", [], {}]}
    assert raw == before


def test_sequence_metadata_is_not_discarded():
    raw = {"messages": [raw_message()], "metadata": {"keep": False}}
    assert messages_output(raw, req()).metadata == {"keep": False}


def test_unknown_fields_still_forbidden():
    raw = raw_message()
    raw["unknown"] = True
    with pytest.raises(ValueError):
        messages_output({"messages": raw}, req())


def test_metadata_bounds_still_enforced():
    with pytest.raises(ValueError):
        messages_output(
            {"messages": raw_message(), "metadata": {"k": "x" * 16384}}, req()
        )
