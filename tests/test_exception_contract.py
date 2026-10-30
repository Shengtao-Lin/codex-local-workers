"""Only prospective contract text differs; all acceptance inputs stay frozen."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import exception_contract_diagnostic as X


def test_only_goal_and_owned_behavior_words_change():
    fixture = X.T.read(X.BATCH / "fixture.json")
    a = X.R.D.INTERFACE.restore_literal(fixture["user_message"])
    b = X.R.D.INTERFACE.restore_literal(fixture["explicit_user_message"])
    assert b["goal"] == a["goal"].replace(X.OLD, X.NEW, 1)
    assert b["required_behavior"][0]["text"] == a["required_behavior"][0][
        "text"
    ].replace(X.OLD, X.NEW, 1)
    b["goal"], b["required_behavior"] = a["goal"], a["required_behavior"]
    assert a == b


def test_protected_tests_and_source_unchanged():
    fixture = X.T.read(X.BATCH / "fixture.json")
    assert X.T.sha(X.BATCH / "snapshot.py") == fixture["binding"]["sha256"]
    for row in X.T.read(X.BATCH / "cells.json").values():
        root = Path(row["root"])
        assert all(X.T.sha(root / p) == sha for p, sha in row["files"].items())
        assert not (root.parent / "started.json").exists()


def test_no_instruction_or_schema_or_guard_change():
    assert (
        X.T.read(X.BATCH / "fixture.json")["system_message"] == X.R.D.PROMPTS["whole"]
    )
    assert all(
        X.T.sha(p) == sha
        for p, sha in X.T.read(X.R.BATCH / "freeze.json")["pins"].items()
    )
