import json
from pathlib import Path
from .repair_phase_rules import IMPORT_CEILING, PROMPT, SCHEMA, decode, guard, materialize, shape
from .repair_phase_rules import render as phase_render

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
    checks = list(runtime.validation.configured_checks or [])
    focused = runtime.validation.focused_tests
    supplemental = getattr(runtime, "extra_checks", [])
    supplemental_facts = getattr(runtime, "extra_check_input_facts", None)
    # These commands were already executed by the trusted host after a failing
    # pytest run. They are diagnostic evidence only, never validation credit.
    if (
        supplemental
        and supplemental_facts
        and supplemental_facts == focused.get("input_facts")
        and supplemental_facts == runtime._validation_facts()
    ):
        configured_ids = {check.get("id") for check in checks}
        checks.extend(
            check
            for check in supplemental
            if check.get("id") in {"ruff-check", "pyright"} - configured_ids
            and check.get("status") == "failed"
            and type(check.get("exit_code")) is int
            and check["exit_code"] == 1
            and check.get("output_truncated") is False
            and not check.get("timed_out")
        )
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
    fact = (focused.get("input_facts") or {}).get(relative, {})
    lines = binding["source"].splitlines()
    line = hint.get("line")
    if (
        relative != binding["path"]
        or relative not in runtime.packet["scope"]["modify"]
        or fact.get("sha256") != binding["sha256"]
        or (focused.get("inputs_unchanged") is not True)
        or (type(line) is not int)
        or (not 1 <= line <= len(lines))
    ):
        return []
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
