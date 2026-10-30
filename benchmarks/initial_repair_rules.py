"""Label a failed existing start as repair, without claiming prior Worker edits."""

from failure_source_rules import (
    IMPORT_CEILING,
    PROMPT,
    SCHEMA,
    decode,
    diagnostics,
    failure_evidence,
    guard,
    materialize,
    shape,
)
from failure_source_rules import render as original_render

__all__ = [
    "IMPORT_CEILING",
    "PROMPT",
    "SCHEMA",
    "decode",
    "diagnostics",
    "failure_evidence",
    "guard",
    "materialize",
    "render",
    "shape",
]


def render(facts):
    text = original_render(facts)
    if (
        facts["resource_ledger"]["edits"] == 0
        and facts["validation_failure"]["status"] == "failed"
    ):
        _, body = text.split("\n", 1)
        return (
            "HOST TASK: Repair the CURRENT starting implementation against the supplied failed checks and hard contract. No Worker edit has yet occurred.\n"
            + body
        )
    return text
