import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_support as S
import explorer_recovery_controller as C
import mapping_recovery_trial as M


def parent():
    row = S.read(M.BATCH / "cells.json")["for-1"]
    return S.read(Path(row["root"]) / ".agent/unit-report.json")


def test_actual_parent_credits_are_deducted():
    credits = C.remaining_credits(parent())
    assert credits["requests"] == credits["format_preparations"] == 10
    assert credits["edits"] == credits["post_edit_checks"] == 3
    assert credits["seconds"] < 900


@pytest.mark.parametrize(
    "change",
    [
        {"status": "blocked"},
        {"infra_failure": {"reason_code": "http"}},
        {"failure_reason": "unsafe edit"},
    ],
)
def test_noneligible_parent_rejected(change):
    report = parent()
    report.update(change)
    with pytest.raises(ValueError):
        C.remaining_credits(report)


def test_partial_edit_is_not_automatically_reworked():
    report = parent()
    report["consolidated_harness"]["actual"]["edits"] = 1
    with pytest.raises(ValueError):
        C.remaining_credits(report)


def test_feedback_requires_current_approved_evidence(tmp_path):
    path = tmp_path / "code.py"
    path.write_text("x = 1\n", encoding="utf-8")
    report = {
        "status": "success",
        "findings": ["untrusted diagnosis"],
        "observed_hashes": {"code.py": S.sha(path)},
    }
    assert (
        C.research_feedback(report, tmp_path, {"code.py"})[0]["source"]
        == "local_explorer_untrusted"
    )
    bad = copy.deepcopy(report)
    bad["observed_hashes"]["code.py"] = "stale"
    for value, approved in [(bad, {"code.py"}), (report, set())]:
        with pytest.raises(ValueError):
            C.research_feedback(value, tmp_path, approved)
