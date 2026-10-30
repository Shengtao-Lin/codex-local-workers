"""Same static-focused proposal and permissions, plus bounded host continuity."""

from execution_memory import ExecutionMemory
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
    "guard",
    "materialize",
    "memory_factory",
    "render",
    "shape",
]

memory_factory = ExecutionMemory
