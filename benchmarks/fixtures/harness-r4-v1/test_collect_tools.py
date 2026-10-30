import copy

from evaluation_harness.adapters.common import collect_tools
from evaluation_harness.canonical.models import (
    CanonicalMessage,
    TextPart,
    ToolCallPart,
    ToolResultPart,
)


def message(*parts):
    return CanonicalMessage(message_id="m", role="assistant", content=list(parts))


def test_requested_and_false_result_preserve_input():
    messages = [
        message(ToolCallPart(call_id="a", name="tool", arguments={"x": 0})),
        message(ToolResultPart(call_id="a", result=False)),
    ]
    before = copy.deepcopy(messages)
    result = collect_tools(messages)
    assert len(result) == 1
    assert result[0].status == "succeeded"
    assert result[0].result is False
    assert result[0].arguments == {"x": 0}
    assert messages == before


def test_unmatched_results_empty_and_non_tools():
    assert collect_tools([]) == []
    assert (
        collect_tools(
            [message(TextPart(text="x"), ToolResultPart(call_id="missing", result=1))]
        )
        == []
    )


def test_repeated_request_replaces_value_without_reordering():
    messages = [
        message(
            ToolCallPart(call_id="a", name="old", arguments={}),
            ToolCallPart(call_id="b", name="second", arguments={}),
            ToolResultPart(call_id="a", result=0),
            ToolCallPart(call_id="a", name="new", arguments={"fresh": True}),
        )
    ]
    result = collect_tools(messages)
    assert [item.call_id for item in result] == ["a", "b"]
    assert result[0].name == "new"
    assert result[0].status == "requested"
    assert result[0].result is None
