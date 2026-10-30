"""No-model source-closure, matched-input and real edit/check controls."""

import copy
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import exception_context_diagnostic as X


def test_only_dependency_text_changes_and_source_is_exact():
    fixture = X.T.read(X.BATCH / "fixture.json")
    full = X.D.INTERFACE.restore_literal(fixture["user_message"])
    lean = X.D.INTERFACE.restore_literal(fixture["lean_user_message"])
    assert full["target"]["dependencies"] != lean["target"]["dependencies"]
    lean["target"]["dependencies"] = full["target"]["dependencies"]
    assert full == lean
    assert "with pytest.raises(ValueError):" in json.dumps(full)
    assert X.T.sha(X.BATCH / "snapshot.py") == fixture["binding"]["sha256"]


def test_transitive_source_closure_not_handwritten_guidance():
    source = (X.ORIGIN / "src/agent_runtime/models.py").read_text(encoding="utf-8")
    text, included, excluded = X.pruned_dependencies(
        source, {"InvocationInput", "InvocationOutput", "Message"}
    )
    assert {
        "InvocationInput",
        "InvocationOutput",
        "Message",
        "MetadataModel",
        "validate_metadata",
        "ContentPart",
        "ToolResult",
        "RuntimeContext",
    } <= set(included)
    assert {
        "AgentDescriptor",
        "RuntimeResponse",
        "StreamCompleted",
        "RuntimeRequest",
    } <= set(excluded)
    assert "def validate_tool_content" in text
    assert "json.dumps" in text and "validate_bounded_metadata" in text
    assert X.T.read(X.BATCH / "fixture.json")["excluded_names"] == excluded


def test_original_guard_and_all25_checks_accept_reference(tmp_path):
    row = X.T.read(X.BATCH / "cells.json")["full-1"]
    root = tmp_path / "isolated"
    shutil.copytree(row["root"], root)
    fixture = X.T.read(X.BATCH / "fixture.json")
    reference = (
        X.N.BATCH
        / "cases/messages_output-candidate-1/isolated"
        / fixture["binding"]["path"]
    )
    function = X.D.BOUNDARY.target(
        reference.read_text(encoding="utf-8"), "messages_output"
    )[3]
    result = X.D.apply(root, json.dumps({"replacement": function}), "whole", fixture)
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
                X.N.BATCH / "private/messages_output/test_private_messages_output.py",
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


def test_stale_hash_rejected_without_writes(tmp_path):
    row = X.T.read(X.BATCH / "cells.json")["lean-1"]
    root = tmp_path / "isolated"
    shutil.copytree(row["root"], root)
    fixture = copy.deepcopy(X.T.read(X.BATCH / "fixture.json"))
    fixture["binding"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Source differs"):
        X.D.apply(root, "{}", "whole", fixture)
    assert all(X.T.sha(root / p) == sha for p, sha in row["files"].items())
