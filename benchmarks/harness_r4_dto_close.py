"""Immutable closeout from Primary-reviewed reports; no model or runtime writes."""

import argparse
import time
from pathlib import Path

import harness_r4_dto as D
from harness_r4_close import wire_metrics

B = D.B


def main(used):
    root = D.BATCH
    seal = B.read(root / "live-freeze.json")
    assert B.sha(D.ADAPTER) == seal["adapter"]
    assert B.sha(B.KIT / "benchmarks/harness_r4_dto.py") == seal["driver"]
    assert B.sha(root / "registration.json") == seal["registration"]
    assert (
        B.sha(B.KIT / "tests/test_reviewer_compact_dto.py") == seal["controls_source"]
    )
    D.R.assert_files(root / "runtime", seal["runtime"])
    judgments = B.read(root / "primary-adjudications.json")
    manual = {row["id"]: row for row in judgments}
    assert len(manual) == len(judgments)
    rows = []
    for item in B.read(root / "registration.json")["cells"]:
        cell = root / "cells" / item["id"]
        D.R.assert_files(Path(item["root"]), item["files"])
        if not (cell / "result.json").exists():
            rows.append({"id": item["id"], "status": "NOT_RUN"})
            continue
        result, report = B.read(cell / "result.json"), B.read(cell / "reviewer.json")
        judgment = manual.pop(item["id"])
        assert type(judgment["correct"]) is bool and judgment["reason"]
        if judgment["correct"]:
            assert result["observed"] == result["expected"]
            assert report["review_protocol"] == "reviewer-compact-report-v1"
            assert not result["protected_drift"] and not result["infra_failure"]
        rows.append(
            {
                **result,
                "primary_adjudication": judgment,
                "report_sha256": B.sha(cell / "reviewer.json"),
                "protocol_errors": report.get("runtime_facts", {}).get(
                    "protocol_error_count"
                ),
                "chat_completions": wire_metrics(cell),
            }
        )
    assert not manual
    executed = [row for row in rows if row.get("status") != "NOT_RUN"]
    correct = sum(row["primary_adjudication"]["correct"] for row in executed)
    qualification = (
        "PASS"
        if correct == 16
        else "HOLD"
        if correct < len(executed)
        else "INCOMPLETE_BUDGET"
    )
    assert len(rows) == 16
    if len(executed) < 16:
        assert used >= 30
    B.save(root / "grid-results.json", rows)
    B.save(
        root / "decision.json",
        {
            "stage": "Independent R4 Reviewer compact REPORT candidate",
            "qualification": qualification,
            "registered": 16,
            "executed": len(executed),
            "substantively_correct": correct,
            "not_run": 16 - len(executed),
            "criterion": "Original 16/16 substantive correctness unchanged",
            "old_transfer_hold_unchanged": True,
            "r4_passed": False,
            "runtime_production_promoted": False,
            "new_transfer_admitted": qualification == "PASS",
            "usage_end": used,
            "usage_ceiling": 30,
            "preparation_phase_wall_seconds": seal["preparation_phase_wall_seconds"],
            "registered_phase_wall_seconds": time.time()
            - B.read(root / "design-registration.json")["preparation_clock_start"],
            "summed_live_cell_seconds": sum(row["seconds"] for row in executed),
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "cost_caveat": "Preparation wall time includes local checks and excludes initial environment/design reading; cannot claim Primary cost reduction.",
        },
    )
    baseline = B.read(root / "baseline.json")
    drift = []
    for path, expected in baseline["files"].items():
        target = B.KIT / path
        actual = B.sha(target) if target.is_file() else None
        if expected != actual:
            drift.append(
                {
                    "path": path,
                    "sha256": actual,
                    "intentional": path
                    in {
                        "benchmarks/harness_r4_dto.py",
                        "docs/local-model-harness-convergence-plan.md",
                    },
                }
            )
    D.R.assert_files(B.KIT, baseline["frozen_runtime"])
    D.R.assert_files(D.OLD.H.BATCH, baseline["previous_stage"])
    B.save(
        root / "preservation.json",
        {
            "checked_workspace_files": len(baseline["files"]),
            "changes": drift,
            "preserved": all(row["intentional"] for row in drift),
            "production_runtime_unchanged": True,
            "previous_stage_seals_unchanged": True,
            "historical_chain": "Prior R4 preservation-final.json verified 133662 paths; this phase only created a new isolated batch and experimental sources.",
        },
    )
    print(
        {
            "qualification": qualification,
            "correct": correct,
            "executed": len(executed),
            "changes": drift,
        },
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    main(parser.parse_args().used)
