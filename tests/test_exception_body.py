"""Truthful hidden source, paired evidence and unchanged host-owned binding."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import exception_body_diagnostic as X


def test_only_current_body_visibility_changes_in_neutral_pair():
    f = X.T.read(X.BATCH / "fixture.json")
    full = X.D.INTERFACE.restore_literal(f["user_message"])
    hidden = X.D.INTERFACE.restore_literal(f["hidden_user_message"])
    assert hidden["target"]["source"] == f["signature"] + "\n    ...\n"
    assert full["target"]["source"] == f["binding"]["source"]
    hidden["target"]["source"] = full["target"]["source"]
    hidden["target"]["implementation_visibility"] = full["target"][
        "implementation_visibility"
    ]
    assert hidden == full


def test_bad_body_does_not_leak_through_failure_projection():
    f = X.T.read(X.BATCH / "fixture.json")
    hidden = X.D.INTERFACE.restore_literal(f["hidden_user_message"])
    assert "except Exception" not in f["hidden_user_message"]
    assert "with pytest.raises(ValueError):" in hidden["failed_test_source"]["source"]
    assert hidden["validation_failure"]["focused_tests"]["failures"]
    assert hidden["target"]["sha256"] == f["binding"]["sha256"]


def test_all_source_and_protected_tests_match_original_bytes():
    f = X.T.read(X.BATCH / "fixture.json")
    assert X.T.sha(X.BATCH / "snapshot.py") == f["binding"]["sha256"]
    for row in X.T.read(X.BATCH / "cells.json").values():
        root = Path(row["root"])
        assert all(X.T.sha(root / p) == sha for p, sha in row["files"].items())
        assert not (root.parent / "started.json").exists()


def test_all_existing_positive_negative_guard_pins_retained():
    assert all(
        X.T.sha(p) == sha
        for p, sha in X.T.read(X.B.BATCH / "freeze.json")["pins"].items()
    )
