"""Reuse the prior small evidence wire protocol on the consolidated safety base."""

from approved_evidence import ApprovedEvidence
from bounded_evidence_candidate import B_PROMPT, schema
from bounded_evidence_candidate import decode as decode_action
from static_focus_rules import (
    IMPORT_CEILING,
    diagnostics,
    guard,
    materialize,
    render,
    shape,
)
from static_focus_rules import (
    PROMPT as BASE_PROMPT,
)
from static_focus_rules import (
    SCHEMA as BASE_SCHEMA,
)
from static_focus_rules import (
    decode as decode_proposal,
)

__all__ = [
    "IMPORT_CEILING",
    "PROMPT",
    "SCHEMA",
    "decode",
    "diagnostics",
    "evidence_factory",
    "guard",
    "materialize",
    "render",
    "shape",
]

PROMPT = BASE_PROMPT + "\n" + B_PROMPT
SCHEMA = schema(BASE_SCHEMA, "B")
evidence_factory = ApprovedEvidence


def decode(raw):
    try:
        return decode_proposal(raw)
    except ValueError:
        pass
    action = decode_action(raw)
    if set(action) <= {"read", "search"}:
        return action, []
    raise ValueError("Only a bounded proposal or evidence action is permitted")
