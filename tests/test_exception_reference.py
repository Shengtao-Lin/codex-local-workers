"""Real canonical preimage context, not a supplied feature solution."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import exception_reference_diagnostic as X


def test_reference_matches_real_preimage_and_not_current_draft():
    f = X.T.read(X.BATCH / "fixture.json")
    p = f["reference_provenance"]
    assert X.T.sha(p["actual_preimage"]) == p["sha256"]
    assert X.T.sha(p["preimages_index"]) == p["index_sha256"]
    facts = X.D.INTERFACE.restore_literal(f["both_user_message"])
    expected = X.D.BOUNDARY.target(
        Path(p["actual_preimage"]).read_text(encoding="utf-8"), "messages_output"
    )[3]
    assert facts["pre_change_reference"]["source"] == expected
    assert expected != f["binding"]["source"]
    assert "does NOT satisfy" in facts["pre_change_reference"]["provenance"]


def test_paired_facts_differ_only_in_reference_or_current_visibility():
    f = X.T.read(X.BATCH / "fixture.json")
    current, both, historical = [
        X.D.INTERFACE.restore_literal(f[k])
        for k in ("user_message", "both_user_message", "reference_user_message")
    ]
    reference = both.pop("pre_change_reference")
    assert current == both
    assert historical.pop("pre_change_reference") == reference
    historical["target"]["source"] = current["target"]["source"]
    historical["target"]["implementation_visibility"] = current["target"][
        "implementation_visibility"
    ]
    assert historical == current


def test_unchanged_real_sources_no_file_rollback():
    f = X.T.read(X.BATCH / "fixture.json")
    for row in X.T.read(X.BATCH / "cells.json").values():
        root = Path(row["root"])
        assert all(X.T.sha(root / p) == sha for p, sha in row["files"].items())
        assert X.T.sha(root / f["binding"]["path"]) == f["binding"]["sha256"]
        assert not (root.parent / "started.json").exists()


def test_inherited_safety_controls_unchanged():
    assert all(
        X.T.sha(p) == sha
        for p, sha in X.T.read(X.V.BATCH / "freeze.json")["pins"].items()
    )
