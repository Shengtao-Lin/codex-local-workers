"""Real CanonicalSample construction for isolated scorer transfer checks."""

from datetime import UTC, datetime

from evaluation_harness.canonical.models import (
    CanonicalMessage,
    CanonicalSample,
    Expectations,
    TextPart,
)


def make_sample(
    messages: list[CanonicalMessage] | None = None,
    facts: list[str] | None = None,
) -> CanonicalSample:
    return CanonicalSample(
        sample_id="sample-a",
        application_id="demo",
        environment="test",
        source_trace_id="trace-a",
        event_time=datetime(2026, 10, 12, tzinfo=UTC),
        input_messages=[],
        output_messages=messages
        if messages is not None
        else [
            CanonicalMessage(
                message_id="out", role="assistant", content=[TextPart(text="STRASSE hit")]
            )
        ],
        expectations=Expectations(reference_facts=facts) if facts is not None else None,
    )
