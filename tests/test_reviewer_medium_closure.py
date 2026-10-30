"""Read-only post-live audit, deliberately separate from pre-live absence tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r4_medium_close as C


def test_fixed_results_preserve_inputs_citations_and_history():
    grid, traces, preservation = C.audit()
    assert len(grid) == len(traces) == 20
    assert preservation["production_runtime_unchanged"]
    assert [r["id"] for r in grid if not r["primary_adjudication"]["correct"]] == [
        "conflicting-contract-r1",
        "real-01",
        "real-04",
    ]


def test_formal_false_passes_already_exist_before_protocol_correction():
    for name in ("real-01", "real-04"):
        wire = C.AUDIT.calls(C.H.BATCH / "cells" / name)
        reports = [
            action["arguments"]
            for call in wire
            for action in call["actions"]
            if action.get("action") == "REPORT"
        ]
        assert len(reports) == 2
        assert reports[0]["findings"] == []
        assert all(c["status"] == "verified" for c in reports[0]["contract_review"])
        assert reports[-1]["assessment"] == "consistent"
        assert "None" in " ".join(reports[-1]["unverified_claims"])


def test_production_and_original_gate_not_promoted_from_raw_probe():
    decision = C.B.read(C.H.BATCH / "decision.json")
    assert decision["qualification"] == "HOLD"
    assert not decision["r4_passed"] and not decision["production_promoted"]
    assert decision["groups"] == [
        {"group": "original-sixteen", "correct": 15, "total": 16},
        {"group": "exposed-real", "correct": 2, "total": 4},
    ]
    assert C.B.read(C.E.BATCH / "decision.json")["correct"] == 16
    assert (
        C.B.read(C.H.BATCH.parent / "r4-review-strength-20261016-1/decision.json")[
            "selected_for_formal_diagnostic"
        ]
        == "medium"
    )
