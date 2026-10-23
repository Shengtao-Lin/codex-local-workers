from .bounded_source_rules import IMPORT_CEILING, PROMPT, SCHEMA, decode, guard, materialize, shape
from .literal_check_feedback import render as literal_render

__all__ = [
    "IMPORT_CEILING",
    "PROMPT",
    "SCHEMA",
    "decode",
    "guard",
    "materialize",
    "render",
    "shape",
]


def render(facts):
    repairing = (
        facts["resource_ledger"]["edits"] > 0 and facts["validation_failure"]["status"] == "failed"
    )
    phase = (
        "HOST TASK: Repair the failed checks on the CURRENT implementation. Use the current failure evidence to make the needed correction while preserving the required behavior and already passing checks. Return an updated replacement or a concrete blocked_reason.\n"
        if repairing
        else "HOST TASK: Implement the required behavior against the current source.\n"
    )
    return phase + literal_render(facts)
