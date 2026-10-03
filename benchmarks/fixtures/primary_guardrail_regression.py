"""Primary-owned broader checks for disposable guardrail snapshots."""

import asyncio
from uuid import uuid4

import pytest
from agent_runtime.hooks.guardrails import MessageLengthGuardrail, PhraseBlockGuardrail
from agent_runtime.models import (
    Message,
    RuntimeContext,
    TextContent,
    ToolCall,
    ToolCallContent,
)


def text_message(text):
    return Message(role="user", content=[TextContent(text=text)])


def evaluate(guardrail, messages):
    context = RuntimeContext(run_id=uuid4(), thread_id=uuid4())
    return asyncio.run(guardrail.evaluate(messages, context=context))


def test_unicode_casefold_not_just_ascii_lower():
    result = evaluate(PhraseBlockGuardrail(["STRASSE"]), [text_message("Die Straße")])
    assert not result.allowed
    assert result.reason_code == "configured_phrase"


def test_configuration_normalizes_only_nonempty_phrases():
    guardrail = PhraseBlockGuardrail([" ", "  BLOCK  ", "block"])
    assert not evaluate(guardrail, [text_message("has bLoCk here")]).allowed


def test_multiple_messages_are_inspected_without_mutation():
    messages = [text_message("safe"), text_message("BLOCK")]
    before = [message.model_dump(mode="json") for message in messages]
    assert not evaluate(PhraseBlockGuardrail(["block"]), messages).allowed
    assert [message.model_dump(mode="json") for message in messages] == before


def test_repeated_evaluation_does_not_change_message_or_decision():
    message = text_message("BlOcK")
    guardrail = PhraseBlockGuardrail(["block"])
    assert not evaluate(guardrail, [message]).allowed
    assert not evaluate(guardrail, [message]).allowed
    assert message.content[0].text == "BlOcK"


def test_non_text_content_is_not_scanned_as_text():
    message = Message(
        role="assistant",
        content=[
            ToolCallContent(tool_call=ToolCall(id="one", name="block", arguments={}))
        ],
    )
    assert evaluate(PhraseBlockGuardrail(["block"]), [message]).allowed


def test_allowed_messages_and_empty_collection_stay_allowed():
    guardrail = PhraseBlockGuardrail(["block"])
    assert evaluate(guardrail, []).allowed
    result = evaluate(guardrail, [text_message("ordinary")])
    assert result.allowed and result.reason_code is None


def test_empty_phrase_configuration_still_fails():
    with pytest.raises(ValueError, match="non-empty"):
        PhraseBlockGuardrail(["", " \t "])


@pytest.mark.parametrize("text,allowed", [("abcde", True), ("abcdef", False)])
def test_neighboring_length_guardrail_keeps_boundary(text, allowed):
    result = evaluate(MessageLengthGuardrail(5), [text_message(text)])
    assert result.allowed is allowed
    assert result.reason_code == (None if allowed else "message_too_long")
