import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_terms_continuation as C


def test_only_two_exact_mutable_indexes_excluded():
    paths = [
        ".agent/current-task.json",
        ".agent/tasks/semantic-terms/state.json",
        ".agent/tasks/other/state.json",
        ".agent/tasks/semantic-terms/runs/terms-001/validation.json",
        ".agent/experiment-config.json",
        "src/common.py",
        "tests/test_common.py",
    ]
    kept = C.protected(dict.fromkeys(paths, "pin"))
    assert set(kept) == set(paths[2:])


def test_all_original_inputs_and_candidate_pins_remain():
    rows = C.audit()
    assert len(rows) == 8
    report = C.B.read(C.H.BATCH / "cells/cell-01/reviewer.json")
    assert report["runtime_facts"]["inputs_unchanged"]
    assert report["decision"] == "pass_to_primary"
    assert not report["findings"]  # Wrong semantic judgment is retained, not repaired.


def test_protected_source_drift_rejected(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("before", encoding="utf-8")
    frozen = {"source.py": C.B.sha(source), ".agent/current-task.json": "unused"}
    source.write_text("after", encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen paths changed"):
        C.H.R.assert_files(tmp_path, C.protected(frozen))
