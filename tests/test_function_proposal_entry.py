"""Narrow function wire format safety and real no-network CLI controls."""

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import function_proposal_rules as P
import function_repeat_trial as F
import normal_task_trial as N

BASE = "import hashlib\n\nVALUE=1\n\ndef unit(x):\n    return x\n\ndef other():\n    return 1\n"


@pytest.mark.parametrize(
    "proposed",
    [
        "def unit(x,y):\n    return x\n",
        "import os\ndef unit(x):\n    return x\n",
        "def other(x):\n    return x\n",
        "def unit(x):\n    import os\n    return x\n",
        "def unit(x):\n    return x\n\ndef evil():\n    return 1\n",
        "def unit(x):\n    return x # type: ignore\n",
        "def unit(x):\\n    return x",
        "@decorator\ndef unit(x):\n    return x\n",
    ],
)
def test_no_authority_from_function_output(proposed):
    with pytest.raises((ValueError, SyntaxError)):
        P.materialize(BASE, proposed, "unit", set())


def test_current_module_reconstruction_preserves_every_other_ast():
    result = P.materialize(BASE, "def unit(x):\n    return x+1\n", "unit", set())
    assert "import hashlib" in result and "def other():\n    return 1" in result
    assert ast.parse(result).body[2].name == "unit"


@pytest.mark.parametrize("topic", ["request_keys", "single_content"])
def test_actual_function_cli_full_unit(topic, tmp_path):
    row = N.prepare_cell(topic, tmp_path / topic, "function-offline-" + topic)
    root = Path(row["root"])
    reference = (N.OLD / "private" / topic / "reference.py").read_text(
        encoding="utf-8-sig"
    )
    symbol = S.read(root / ".agent/config.json")["coder_single_function"]["symbol"]
    node = next(
        n
        for n in ast.parse(reference).body
        if isinstance(n, ast.FunctionDef) and n.name == symbol
    )
    function = (
        "\n".join(reference.splitlines()[node.lineno - 1 : node.end_lineno]) + "\n"
    )
    replay = root.parent / "function.json"
    S.save(replay, [{"replacement": function}])
    result = T.run(F.command(root, replay=replay), root, timeout=180)
    S.save(root.parent / "entry-process.json", result)
    assert result["exit_code"] == 0, result
    report = S.read(root / ".agent/unit-report.json")
    actual = report["consolidated_harness"]["actual"]
    assert actual["model_requests"] == 0 and actual["scripted_requests"] == 1
    assert actual["edits"] == actual["post_edit_checks"] == 1
    summary = S.read(root / ".agent/unit-summary.json")
    assert summary["reviewer_input_authenticated"] and not summary["reviewer_started"]
    assert all(
        S.sha(root / p) == digest
        for p, digest in row["files"].items()
        if p != row["target"]
    )


def test_entry_rejects_ambiguous_format_flags(tmp_path):
    row = N.prepare_cell("request_keys", tmp_path / "flags", "bad-flags")
    root = Path(row["root"])
    argv = F.command(root, "preflight") + ["--preserve-existing-imports"]
    result = T.run(argv, root, timeout=30)
    assert result["exit_code"] == 2 and "not allowed" in result["stderr"]
