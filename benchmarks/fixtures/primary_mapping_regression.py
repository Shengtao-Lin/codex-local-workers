"""Primary-owned wider adapter contract checks for disposable snapshots."""

from uuid import uuid4

import pytest
from agent_runtime.adapters.mapping import messages_input, messages_output
from agent_runtime.models import (
    InvocationInput,
    InvocationOutput,
    Message,
    RuntimeContext,
    TextContent,
)
from pydantic import ValidationError


def message(text, role="assistant"):
    return Message(role=role, content=[TextContent(text=text)])


def test_input_to_output_round_trip_preserves_exact_serialized_messages():
    request = InvocationInput(
        context=RuntimeContext(run_id=uuid4(), thread_id=uuid4()),
        messages=[message("one", "user"), message("two")],
        metadata={"trace": {"number": 7}},
    )
    payload = messages_input(request)
    assert payload["context"] == request.context.model_dump(mode="json")
    result = messages_output(payload, request)
    assert [item.model_dump(mode="json") for item in result.messages] == payload[
        "messages"
    ]
    assert result.metadata == request.metadata


def test_existing_canonical_objects_keep_identity():
    item = message("direct")
    output = InvocationOutput(messages=[item], metadata={"valid": True})
    assert messages_output(output, None) is output
    assert messages_output(item, None).messages[0] is item


def test_tuple_messages_keep_order_and_metadata():
    first, second = message("first"), message("second")
    result = messages_output(
        {
            "messages": (first.model_dump(mode="json"), second.model_dump(mode="json")),
            "metadata": {"round": 2},
        },
        None,
    )
    assert [item.id for item in result.messages] == [first.id, second.id]
    assert result.metadata == {"round": 2}


@pytest.mark.parametrize("container", [None, 42, "text", b"text"])
def test_invalid_container_uses_type_error(container):
    with pytest.raises(TypeError):
        messages_output({"messages": container}, None)


def test_empty_valid_sequence_still_fails_output_contract():
    with pytest.raises(ValidationError):
        messages_output({"messages": []}, None)


def test_invalid_element_and_metadata_remain_errors():
    valid = message("valid").model_dump(mode="json")
    with pytest.raises(ValidationError):
        messages_output({"messages": [valid, {"role": "invalid"}]}, None)
    with pytest.raises(TypeError, match="metadata"):
        messages_output({"messages": [valid], "metadata": ["not", "mapping"]}, None)


def test_explicit_none_metadata_is_not_omitted_metadata():
    valid = message("valid").model_dump(mode="json")
    assert messages_output({"messages": [valid]}, None).metadata == {}
    with pytest.raises(TypeError, match="metadata"):
        messages_output({"messages": [valid], "metadata": None}, None)
