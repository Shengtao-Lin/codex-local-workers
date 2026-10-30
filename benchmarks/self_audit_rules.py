"""One Coder contract check before handoff; unchanged source/proposal authority."""

from repair_phase_rules import (
    IMPORT_CEILING,
    PROMPT,
    SCHEMA,
    decode,
    guard,
    materialize,
    shape,
)
from repair_phase_rules import render as phase_render

SELF_AUDIT = True
__all__ = [
    "IMPORT_CEILING",
    "PROMPT",
    "SCHEMA",
    "SELF_AUDIT",
    "decode",
    "guard",
    "materialize",
    "render",
    "shape",
]


def render(facts):
    if (
        facts["resource_ledger"]["edits"] > 0
        and facts["validation_failure"]["status"] == "passed"
    ):
        task = (
            "HOST TASK: Review your CURRENT implementation against every required "
            "behavior, including behavior not established by the passing tests. "
            "If a correction is needed, return the corrected function/module. "
            "If no correction is needed, return the CURRENT function unchanged. "
            "Any change will be checked again. This review is not final acceptance.\n"
        )
        return task + phase_render(facts).split("\n", 1)[1]
    return phase_render(facts)
