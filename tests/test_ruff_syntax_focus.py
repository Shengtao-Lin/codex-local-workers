"""Ruff syntax diagnostics receive the same version-bound facts as lint rules."""

import copy
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / ".local-agents"))
from bounded import static_focus_rules as R
from test_supplemental_static_focus import W, material

MESSAGE = "Cannot use an escape sequence (backslash) in f-strings on Python 3.11 (syntax was added in Python 3.12)"


@pytest.mark.parametrize(
    "output",
    [
        f"invalid-syntax: {MESSAGE}\n  --> src/space name.py:22:32\n",
        f"invalid-syntax: {MESSAGE}\r\n  --> src\\space name.py:22:32\r\n",
        f"\x1b[31minvalid-syntax\x1b[0m: {MESSAGE}\n  --> src/space name.py:22:32\n",
        f"src/space name.py:22:32: invalid-syntax: {MESSAGE}\n",
        f"invalid-syntax: {MESSAGE}\n  --> F:\\repo\\space name.py:22:32\n",
    ],
)
def test_syntax_location_is_parsed_without_inventing_repair(output):
    hint = W.WorkerRuntime._configured_check_repair_hint(
        [{"id": "ruff-check", "status": "failed", "output": output}]
    )
    assert hint["rule"] == "invalid-syntax"
    assert hint["message"] == MESSAGE
    assert hint["line"] == 22 and hint["column"] == 32
    assert hint["path"].endswith("space name.py") and "\\" not in hint["path"]


@pytest.mark.parametrize("supplemental", [False, True])
def test_syntax_focus_is_bound_to_current_source(tmp_path, supplemental):
    runtime, binding, _ = material(tmp_path)
    check = runtime.extra_checks[0]
    check["output"] = f"invalid-syntax: {MESSAGE}\n  --> {binding['path']}:2:5\n"
    if not supplemental:
        runtime.validation.configured_checks = [copy.deepcopy(check)]
        runtime.extra_checks = []
    focus = R.diagnostics(runtime, binding)
    assert len(focus) == 1
    assert focus[0]["rule"] == "invalid-syntax"
    assert focus[0]["message"] == MESSAGE
    assert focus[0]["current_line"] == binding["source"].splitlines()[1]
    assert focus[0]["source_sha256"] == binding["sha256"]
    assert "instruction" not in focus[0]


@pytest.mark.parametrize(
    "bad", ["unknown_rule", "zero_line", "missing_location", "unrelated", "passed"]
)
def test_no_location_credit_for_malformed_or_unrelated_diagnostic(bad):
    check = {
        "id": "ruff-check",
        "status": "failed",
        "output": f"invalid-syntax: {MESSAGE}\n  --> src/code.py:2:5\n",
    }
    if bad == "unknown_rule":
        check["output"] = check["output"].replace("invalid-syntax", "model-instruction")
    elif bad == "zero_line":
        check["output"] = check["output"].replace(":2:5", ":0:5")
    elif bad == "missing_location":
        check["output"] = check["output"].split("\n")[0]
    elif bad == "unrelated":
        check["id"] = "model-generated"
    else:
        check["status"] = "passed"
    hint = W.WorkerRuntime._configured_check_repair_hint([check])
    assert not hint or "path" not in hint


@pytest.mark.parametrize("bad", ["stale", "readonly", "changed", "outside", "line"])
def test_syntax_focus_keeps_existing_source_guards(tmp_path, bad):
    runtime, binding, _ = material(tmp_path)
    check = runtime.extra_checks[0]
    check["output"] = f"invalid-syntax: {MESSAGE}\n  --> {binding['path']}:2:5\n"
    if bad == "stale":
        binding["sha256"] = "different"
    elif bad == "readonly":
        runtime.packet["scope"]["modify"] = []
    elif bad == "changed":
        runtime.validation.focused_tests["inputs_unchanged"] = False
    elif bad == "outside":
        check["output"] = check["output"].replace(binding["path"], "../outside.py")
    else:
        check["output"] = check["output"].replace(":2:5", ":99:5")
    assert R.diagnostics(runtime, binding) == []
