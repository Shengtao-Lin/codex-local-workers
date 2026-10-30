"""Frozen-source representation controls, no model calls or acceptance claims."""

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import repair_representation_diagnostic as D


@pytest.fixture
def sample(tmp_path):
    fixture = D.T.read(D.BATCH / "fixture.json")
    root = tmp_path / "isolated"
    path = root / fixture["binding"]["path"]
    path.parent.mkdir(parents=True)
    shutil.copyfile(D.BATCH / "snapshot.py", path)
    return root, fixture


def proposal(fixture, arm="span", annotation="Any"):
    replacement = fixture["span"]["source"].replace("(obj)", f"(obj: {annotation})")
    if arm == "whole":
        replacement = fixture["binding"]["source"].replace(
            fixture["span"]["source"], replacement
        )
    return json.dumps({"replacement": replacement}, ensure_ascii=False)


@pytest.mark.parametrize("arm", ["whole", "span"])
def test_actual_safeeditor_roundtrip_and_no_implicit_repair(sample, arm):
    root, fixture = sample
    before = (root / fixture["binding"]["path"]).read_text(encoding="utf-8")
    outcome = D.apply(root, proposal(fixture, arm), arm, fixture)
    after = (root / fixture["binding"]["path"]).read_text(encoding="utf-8")
    assert outcome["applied"] is True
    assert after == before.replace(
        "def check_finite(obj):", "def check_finite(obj: Any):"
    )


@pytest.mark.parametrize(
    "replacement",
    [
        "",
        "    def check_finite(obj: Any):\n",
        "    def check_finite(obj: Any):\n        pass",
        "```python\n    def check_finite(obj: Any):\n```",
        "    def other(obj: Any):",
        "    def check_finite(other: Any):",
        "    def check_finite(obj: Any = None):",
        "    def check_finite(obj: Any): pass",
        "def check_finite(obj: Any):",
        "        def check_finite(obj: Any):",
        "    async def check_finite(obj: Any):",
        "    def check_finite(obj: Any):; x = 1",
        None,
        ["    def check_finite(obj: Any):"],
    ],
)
def test_reject_malformed_or_out_of_span_proposal(sample, replacement):
    root, fixture = sample
    path = root / fixture["binding"]["path"]
    before = path.read_bytes()
    with pytest.raises((ValueError, SyntaxError)):
        D.apply(root, json.dumps({"replacement": replacement}), "span", fixture)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "raw",
    [
        '{"replacement":"a", "replacement":"b"}',
        "{}",
        "[]",
        '{"replacement":"    def check_finite(obj: Any):", "path":"other.py"}',
        '{"replacement":"    def check_finite(obj: Any):", "expected_sha256":"forged"}',
        '{"replacement":"    def check_finite(obj: Any):", "blocked_reason":"both"}',
    ],
)
def test_invalid_envelopes_are_not_reconstructed(sample, raw):
    root, fixture = sample
    before = (root / fixture["binding"]["path"]).read_bytes()
    with pytest.raises((ValueError, SyntaxError)):
        D.apply(root, raw, "span", fixture)
    assert (root / fixture["binding"]["path"]).read_bytes() == before


@pytest.mark.parametrize("tamper", ["hash", "location", "source", "wrong_file"])
def test_binding_negatives_fail_closed(sample, tamper):
    root, fixture = sample
    changed = copy.deepcopy(fixture)
    path = root / fixture["binding"]["path"]
    if tamper == "hash":
        changed["binding"]["sha256"] = "0" * 64
    elif tamper == "location":
        changed["span"]["line"] += 1
    elif tamper == "source":
        path.write_bytes(path.read_bytes() + b"\n# external edit\n")
    else:
        changed["span"]["path"] = "tests/protected.py"
    before = path.read_bytes()
    with pytest.raises(ValueError):
        D.apply(root, proposal(fixture), "span", changed)
    assert path.read_bytes() == before


@pytest.mark.parametrize("arm", ["whole", "span"])
def test_blocked_is_not_changed_or_accepted(sample, arm):
    root, fixture = sample
    before = (root / fixture["binding"]["path"]).read_bytes()
    assert (
        D.apply(root, '{"blocked_reason":"needs contract revision"}', arm, fixture)[
            "applied"
        ]
        is False
    )
    assert (root / fixture["binding"]["path"]).read_bytes() == before


@pytest.mark.parametrize("arm", ["whole", "span"])
def test_real_cli_serialization_and_negative_config(sample, tmp_path, arm):
    root, fixture = sample
    payload = tmp_path / "proposal.json"
    payload.write_text(proposal(fixture, arm), encoding="utf-8")
    command = [
        sys.executable,
        "-B",
        D.KIT / "benchmarks/repair_representation_diagnostic.py",
        "apply",
        "--root",
        root,
        "--proposal",
        payload,
        "--arm",
        arm,
    ]
    result = D.S.O.M.command(command, root)
    assert result["exit_code"] == 0, result
    assert json.loads(result["stdout"])["applied"] is True
    before = (root / fixture["binding"]["path"]).read_bytes()
    # Same frozen hash is stale after that edit, so replay cannot write again.
    result = D.S.O.M.command(command, root)
    assert result["exit_code"] != 0 and "frozen hash" in result["stderr"]
    assert (root / fixture["binding"]["path"]).read_bytes() == before


def test_same_user_input_and_snapshot_for_all_nine():
    fixture = D.T.read(D.BATCH / "fixture.json")
    assert D.INTERFACE.restore_literal(fixture["user_message"]) == fixture["facts"]
    assert len(D.ORDER) == 9 and len(set(D.ORDER)) == 9
    rows = D.T.read(D.BATCH / "cells.json")
    for row in rows.values():
        assert (
            D.T.sha(Path(row["root"]) / fixture["binding"]["path"])
            == fixture["binding"]["sha256"]
        )
    assert len({json.dumps(r["files"], sort_keys=True) for r in rows.values()}) == 1


@pytest.mark.parametrize("annotation", ["Any", "str"])
def test_correct_and_wrong_repair_under_actual_fixed_checks(tmp_path, annotation):
    fixture = D.T.read(D.BATCH / "fixture.json")
    seed = Path(D.T.read(D.BATCH / "cells.json")["span-1"]["root"])
    root = tmp_path / "isolated"
    shutil.copytree(seed, root)
    D.apply(root, proposal(fixture, annotation=annotation), "span", fixture)
    env = {
        **D.os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(root / "src"),
    }
    tests = D.S.O.M.command(
        [
            D.S.O.M.PYTHON,
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_metadata.py",
            D.S.O.M.BATCH / "private/metadata/test_private_metadata.py",
        ],
        root,
        env,
    )
    checks = [
        D.S.O.M.command(
            [D.S.O.M.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            root,
        ),
        D.S.O.M.command(
            [D.S.O.M.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root
        ),
        D.S.O.M.command(
            [D.S.O.M.PYTHON, "-B", "-m", "pyright", "--pythonpath", D.S.O.M.PYTHON],
            root,
        ),
    ]
    assert tests["exit_code"] == 0 and "12 passed" in tests["stdout"]
    assert checks[0]["exit_code"] == checks[1]["exit_code"] == 0
    assert checks[2]["exit_code"] == (0 if annotation == "Any" else 1)


@pytest.mark.parametrize("raw", ['{"cause":"a","cause":"b"}', "[]", '{"cause":NaN}'])
def test_diagnosis_parser_does_not_hide_invalid_json(raw):
    with pytest.raises(ValueError):
        D.strict_object(raw)
