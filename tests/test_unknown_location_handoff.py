from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

import stability_e2e as STABILITY
import unknown_location_handoff as HANDOFF


def test_locator_handoff_rejects_changed_or_outside_evidence(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("value = 1\n")
    report = {
        "explorer_mode": "locate",
        "source_refs": [
            {
                "path": "source.py",
                "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        ],
    }
    assert HANDOFF.locator_inputs_unchanged(tmp_path, report)
    source.write_text("value = 2\n")
    assert not HANDOFF.locator_inputs_unchanged(tmp_path, report)
    report["source_refs"][0]["path"] = "../outside.py"
    assert not HANDOFF.locator_inputs_unchanged(tmp_path, report)


def test_handoff_requires_explorer_source_and_test_evidence() -> None:
    case = next(item for item in STABILITY.CASES if item.name == "selection-order")
    test_path = "tests/test_selection_order.py"
    report = {
        "status": "success",
        "relevant_files": [{"path": case.target, "reason": "ordering branch"}],
        "relevant_tests": [test_path],
        "evidence_summary": {"observed_files": [case.target, test_path]},
        "findings": [
            f"{case.target} line 10: ordering",
            f"{test_path} line 5: asserts it",
        ],
        "call_flow": [],
        "uncertainties": [],
    }
    assert HANDOFF.handoff_ready(report, case, test_path)
    report["relevant_files"] = [{"path": test_path, "reason": "test"}]
    assert not HANDOFF.handoff_ready(report, case, test_path)
    report["relevant_files"] = [{"path": case.target, "reason": "ordering branch"}]
    report["findings"] = [f"{test_path} line 5: asserts it"]
    assert not HANDOFF.handoff_ready(report, case, test_path)
