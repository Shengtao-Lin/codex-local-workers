"""Same proposal, repair phase and checks; mechanically include failing test source."""

from failed_test_source import collect
from static_focus_rules import (
    IMPORT_CEILING,
    PROMPT,
    SCHEMA,
    decode,
    diagnostics,
    guard,
    materialize,
    render,
    shape,
)

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

failure_evidence = collect
