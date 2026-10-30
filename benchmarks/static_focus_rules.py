"""Version-bound structured static diagnostics from the existing trusted parser."""

import json
from pathlib import Path

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

__all__ = [
    "IMPORT_CEILING",
    "PROMPT",
    "SCHEMA",
    "decode",
    "diagnostics",
    "guard",
    "materialize",
    "render",
    "shape",
]


def diagnostics(runtime, binding):
    checks = runtime.validation.configured_checks or []
    hint = runtime._configured_check_repair_hint(checks)
    if not hint or hint.get("check_id") not in {"pyright", "ruff-check"}:
        return []
    try:
        path = Path(hint["path"])
        relative = (
            path.relative_to(runtime.repo_root).as_posix()
            if path.is_absolute()
            else path.as_posix()
        )
    except (KeyError, ValueError):
        return []
    focused = runtime.validation.focused_tests
    fact = (focused.get("input_facts") or {}).get(relative, {})
    lines = binding["source"].splitlines()
    line = hint.get("line")
    if (
        relative != binding["path"]
        or relative not in runtime.packet["scope"]["modify"]
        or fact.get("sha256") != binding["sha256"]
        or focused.get("inputs_unchanged") is not True
        or type(line) is not int
        or not 1 <= line <= len(lines)
    ):
        return []
    # Omit the old action instructions (SAFE_REPLACE/VALIDATE) entirely.
    return [
        {
            **{
                key: hint[key]
                for key in ("check_id", "rule", "line", "column", "message")
                if key in hint
            },
            "path": relative,
            "source_sha256": binding["sha256"],
            "current_line": lines[line - 1],
            "provenance": "existing configured-check parser plus current validation/source binding",
        }
    ]


def render(facts):
    text = phase_render(facts)
    focus = facts["validation_failure"]["diagnostics"]
    if not focus:
        return text
    phase, rest = text.split("\n", 1)
    return (
        phase
        + "\nCURRENT_STATIC_DIAGNOSTIC\n"
        + json.dumps(focus, ensure_ascii=False)
        + "\n"
        + rest
    )
