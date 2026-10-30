"""Record Primary's independent semantic adjudication of the three controls."""

from pathlib import Path

import bounded_evidence_support as S
import reviewer_profile_screen as V
import reviewer_profile_screen_v3 as NEW


def main():
    batch = NEW.BATCH
    reg = S.read(batch / "registration.json")
    assert all(S.sha(path) == digest for path, digest in reg["pins"].items())
    cells = S.read(batch / "cells.json")
    reasons = {
        "hash-1": "CONFIRMED F1: strip-based normalization collapses nonempty whitespace revision; violates exact-empty-only contract and independent oracle fails. Reviewer quotes current source condition.",
        "binding-1": "CONFIRMED correct: environment != empty string preserves whitespace, insertion order workspace first, application quote safe empty; independent positive controls pass. No invented defect.",
        "collector-1": "CONFIRMED F1: truthiness test permits enabled=1, whereas contract requires identity True; actual oracle fails strict rejection. Reviewer names exact condition and counterexample.",
    }
    expected = S.read(batch / "oracle.json")["expected"]
    rows = []
    for cell in V.ORDER:
        row = cells[cell]
        root = Path(row["root"])
        report_path = root / ".agent/screen-review.json"
        report = S.read(report_path)
        assert report["decision"] == expected[cell]
        identity = row["identity"]["run_id"]
        review = root / ".agent/tasks" / identity / "reviews" / ("screen-" + identity)
        budget = S.read(review / "contract-first-budget.json")
        checks = S.read(batch / "oracle" / (cell + "-checks.json"))
        assert (checks["exit_code"] == 0) == (cell == "binding-1")
        disposition = {"cell": cell, "reviewer_report_sha256": S.sha(report_path),
                       "Primary_semantic_assessment": reasons[cell],
                       "model_review_count": 1, "same_code_semantic_resampling": False,
                       "feature_acceptance": False, "coder_model_credit": False}
        S.save(batch / "primary" / (cell + ".json"), disposition)
        rows.append({"cell": cell, "decision": report["decision"],
                     "correct_verdict": True, "requests": budget["actual_requests"],
                     "protocol_errors": budget["protocol_errors"]})
    S.save(batch / "metrics.json", {"registered": 3, "executed": 3, "correct_positive": "1/1",
           "true_defect_rejections": "2/2", "false_pass": 0, "false_reject": 0,
           "rows": rows, "coder_model_requests": 0, "cloud_savings": "unknown"})
    S.save(batch / "decision.json", {"status": "PASS_FIXED_REVIEWER_SCREEN", "scope": "Two explicit contract defects and one positive; not unknown-boundary reliability or production release",
           "gate": reg["gate"], "Primary": "All three report judgments independently confirmed against actual source and hidden oracle; no model repair or semantic resampling",
           "history": "Earlier two preparation failures retained; no model semantic failures excluded from this batch"})
    S.save(batch / "handoff.json", {"conclusion": "Packaged Reviewer detects both seeded public-test-passing regressions; actual contract-first semantic method unchanged",
           "limits": "Explicitly stated whitespace and strict-bool rules; small exposed-source control set, not unknown boundary proof; Primary still owns final acceptance",
           "next": "Fix evidenced Explorer task-obligation mismatch, not Reviewer prompts; keep semantic automatic rework disabled"})
    print("Primary confirmed Reviewer positive1/1 and real defect rejection2/2")


if __name__ == "__main__":
    main()
