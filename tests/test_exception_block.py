"""Actual error span and unchanged original editor scope, with negative controls."""

import copy
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import exception_block_diagnostic as X

GOOD = """        if isinstance(raw_messages, (Message, Mapping)):
            messages = [Message.model_validate(raw_messages)]
        else:
            raise TypeError("Adapter output mapping must contain a message sequence")"""


def initial(tmp_path):
    row = X.T.read(X.BATCH / "cells.json")["block-1"]
    root = tmp_path / "isolated"
    shutil.copytree(row["root"], root)
    return root, row, X.T.read(X.BATCH / "fixture.json")


def test_real_guarded_block_reference_all25_and_static(tmp_path):
    root, row, fixture = initial(tmp_path)
    result = X.apply(root, json.dumps({"replacement": GOOD}), "block", fixture)
    assert result["applied"]
    checks = [
        X.M.command(
            [
                X.M.PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_messages_output.py",
                X.C.N.BATCH / "private/messages_output/test_private_messages_output.py",
            ],
            root,
            {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(root / "src"),
            },
        )
    ]
    checks += [
        X.M.command(
            [X.M.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"], root
        ),
        X.M.command([X.M.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root),
        X.M.command(
            [X.M.PYTHON, "-B", "-m", "pyright", "--pythonpath", X.M.PYTHON], root
        ),
    ]
    assert all(c["exit_code"] == 0 for c in checks), checks
    assert "25 passed" in checks[0]["stdout"]
    assert all(
        X.T.sha(root / p) == sha
        for p, sha in row["files"].items()
        if p != fixture["binding"]["path"]
    )


@pytest.mark.parametrize(
    "tamper", ["hash", "path", "line", "source", "indent", "duplicate_json"]
)
def test_negative_binding_and_scope(tmp_path, tamper):
    root, row, fixture = initial(tmp_path)
    fixture = copy.deepcopy(fixture)
    replacement = GOOD
    if tamper == "hash":
        fixture["span"]["source_sha256"] = "0" * 64
    elif tamper == "path":
        fixture["span"]["path"] = "src/agent_runtime/models.py"
    elif tamper == "line":
        fixture["span"]["start_line"] -= 1
    elif tamper == "source":
        fixture["span"]["source"] += "# not actual source"
    elif tamper == "indent":
        replacement = "def escape():\n    return None"
    raw = json.dumps({"replacement": replacement})
    if tamper == "duplicate_json":
        raw = '{"replacement":"x","replacement":"y"}'
    with pytest.raises((ValueError, SyntaxError, X.D.EDITOR.SafeEditError)):
        X.apply(root, raw, "block", fixture)
    assert all(X.T.sha(root / p) == sha for p, sha in row["files"].items())


def test_span_is_actual_nearest_statement_and_same_input():
    f = X.T.read(X.BATCH / "fixture.json")
    facts = X.D.INTERFACE.restore_literal(f["user_message"])
    source = (X.BATCH / "snapshot.py").read_text(encoding="utf-8")
    assert (
        X.locate(source, f["binding"], facts["validation_failure"]["focused_tests"])
        == f["span"]
    )
    assert f["span"]["source"].lstrip().startswith("try:")
    assert X.T.sha(X.BATCH / "snapshot.py") == f["binding"]["sha256"]
