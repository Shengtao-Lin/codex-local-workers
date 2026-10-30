"""Scope/protocol/atomicity controls plus installed three-edit check accounting."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
sys.path.insert(0, str(KIT / ".local-agents"))
import host_block_proposal as B
from bounded import compatibility_profile as C
from bounded import static_focus_rules as BASE
from test_installable_bounded import L, S, archive, project

CURRENT = "import json\n\ndef f(x: int) -> int:\n    y = x + 1\n    return y\n\ndef other():\n    return 3\n"


def proposal(*edits):
    return {
        "kind": "edits",
        "edits": [{"find": a, "replace": b} for a, b in edits],
        "reason": "",
    }


def rules():
    return B.adapt(C.proposal_rules({"bounded_compatibility_profile": "flat-v1"}, BASE))


def apply(value, current=CURRENT):
    decoded, _ = B.decode(json.dumps(value))
    return rules().materialize(
        current, decoded["replacement"], "f", BASE.IMPORT_CEILING
    )


def test_atomic_multiple_blocks_and_delete():
    observed = apply(proposal(("    y = x + 1\n", ""), ("return y", "return x + 2")))
    assert observed == CURRENT.replace("    y = x + 1\n", "").replace(
        "return y", "return x + 2"
    )


def test_unchanged_proposal_reaches_existing_noop_counter():
    assert apply(proposal(("return y", "return y"))) == CURRENT


def test_keeps_original_render_guards_and_diagnostic_provider():
    base = C.proposal_rules({"bounded_compatibility_profile": "flat-v1"}, BASE)
    adapted = B.adapt(base)
    for key in ("render", "diagnostics", "guard", "shape", "IMPORT_CEILING"):
        assert getattr(adapted, key) is getattr(base, key)


@pytest.mark.parametrize(
    "value",
    [
        {},
        [],
        {"kind": "edits", "edits": [], "reason": ""},
        proposal(*[("x", "y")] * 4),
        proposal(("", "x")),
        proposal(("\n", "x")),
        proposal(("x", None)),
        proposal(("x", "a" * 12001)),
        proposal(("x\r\n", "z")),
        {**proposal(("x", "z")), "path": "tests/test.py"},
        {**proposal(("x", "z")), "reason": "also change permission"},
        {
            "kind": "blocked",
            "edits": [{"find": "x", "replace": "y"}],
            "reason": "missing",
        },
        {"kind": "blocked", "edits": [], "reason": ""},
        {"kind": "VALIDATE", "edits": [], "reason": ""},
    ],
)
def test_reject_bad_shapes(value):
    with pytest.raises(ValueError):
        B.decode(json.dumps(value))


def test_reject_duplicate_keys():
    with pytest.raises(ValueError, match="Duplicate"):
        B.decode(
            '{"kind":"edits","edits":[{"find":"x","find":"y","replace":"z"}],"reason":""}'
        )


@pytest.mark.parametrize(
    "edits",
    [
        (("not present", "x"),),
        (("x", "y"),),
        (("def other", "def other2"),),
        (("import json", "import os"),),
        (("return y", "return 1"), ("y", "q")),
        (("f(x: int)", "f(x: str)"),),
        (("return y", "return y\n\ndef injected():\n    return 2"),),
        (("return y", "this is not Python !!"),),
    ],
)
def test_reject_missing_ambiguous_overlap_protected_signature_injection(edits):
    with pytest.raises((ValueError, SyntaxError)):
        apply(proposal(*edits))


def test_blocked_is_preserved():
    assert B.decode(
        json.dumps(
            {"kind": "blocked", "edits": [], "reason": "Missing approved dependency"}
        )
    )[0] == {"blocked_reason": "Missing approved dependency"}


def test_installed_three_edits_all_get_complete_checks():
    with tempfile.TemporaryDirectory(prefix="host-block-control-") as directory:
        _three_edits(Path(directory))


def _three_edits(root):
    project(root, "labels", "host-block-offline")
    config = S.read(root / ".agent/config.json")
    config["bounded_compatibility_profile"] = "flat-v1"
    # Test fixture setup only, before archive/run creation.
    (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")
    source = (root / "src/product/code.py").read_text(encoding="utf-8")
    symbol = config["coder_single_function"]["symbol"]
    tree = B.ast.parse(source)
    target = next(
        n for n in tree.body if isinstance(n, B.ast.FunctionDef) and n.name == symbol
    )
    old = "".join(
        source.splitlines(keepends=True)[target.lineno - 1 : target.end_lineno]
    )
    correct = L.TASKS["labels"]["reference"]
    broken = correct.replace(
        "    result = dict(defaults)", "    unused = 1\n    result = dict(defaults)"
    )
    replay = root / ".agent/replay.json"
    S.save(
        replay,
        [
            proposal((old, broken)),
            proposal(("unused = 1", "unused = 2")),
            proposal(("    unused = 2\n", "")),
        ],
    )
    result = subprocess.run(
        [
            S.PYTHON,
            "-B",
            str(KIT / "benchmarks/host_block_proposal.py"),
            "--host-blocks",
            "--mode",
            "unit",
            "--packet",
            ".agent/packet.json",
            "--config",
            ".agent/config.json",
            "--report",
            ".agent/unit-report.json",
            "--review-report",
            ".agent/reviewer-report.json",
            "--summary",
            ".agent/summary.json",
            "--replay",
            str(replay),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = S.read(root / ".agent/unit-report.json")
    actual = report["consolidated_harness"]["actual"]
    assert (
        actual["edits"]
        == actual["post_edit_checks"]
        == actual["scripted_requests"]
        == 3
    )
    assert actual["initial_checks"] == 1
    assert S.read(root / ".agent/summary.json")["reviewer_started"] is False
    assert S.read(root / ".agent/summary.json")["reviewer_input_authenticated"] is True
    assert len(list(archive(root).glob("validation-attempt-*.json"))) == 4
