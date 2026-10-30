"""A new semantic task; no model-visible implementation recipe."""

import asyncio

import pytest
from conftest import make_sample

from evaluation_harness.canonical.models import CanonicalMessage, JsonPart, TextPart
from evaluation_harness.scorers.deterministic import OutputPresentScorer


@pytest.mark.parametrize(
    ("messages", "expected"),
    [
        ([], 0.0),
        ([CanonicalMessage(message_id="a", role="assistant", content=[TextPart(text=" \t")])], 0.0),
        (
            [CanonicalMessage(message_id="a", role="assistant", content=[JsonPart(value=False)])],
            0.0,
        ),
        ([CanonicalMessage(message_id="a", role="user", content=[TextPart(text="hello")])], 0.0),
        (
            [
                CanonicalMessage(
                    message_id="a", role="assistant", content=[TextPart(text="  你好 ")]
                )
            ],
            1.0,
        ),
        (
            [
                CanonicalMessage(message_id="a", role="assistant", content=[TextPart(text=" ")]),
                CanonicalMessage(
                    message_id="b", role="assistant", content=[TextPart(text="later")]
                ),
            ],
            1.0,
        ),
        (
            [
                CanonicalMessage(message_id="a", role="tool", content=[TextPart(text="tool")]),
                CanonicalMessage(message_id="b", role="assistant", content=[TextPart(text=" \n")]),
            ],
            0.0,
        ),
    ],
)
def test_meaningful_assistant_text_across_all_messages(
    messages: list[CanonicalMessage], expected: float
) -> None:
    sample = make_sample(messages)
    before = sample.model_dump()
    result = asyncio.run(OutputPresentScorer().score(sample))
    assert result.score == expected
    assert result.label == ("pass" if expected else "fail")
    assert result.status == "succeeded"
    assert sample.model_dump() == before
