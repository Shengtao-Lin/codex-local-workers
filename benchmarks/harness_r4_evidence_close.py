"""Close observation experiment from independent Primary judgments, no live calls."""

import argparse
from pathlib import Path

import harness_r4_dto_audit as AUDIT
import harness_r4_evidence as E

B = E.B


def main(used):
    E.prior_unchanged()
    for path, digest in B.read(E.BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(path)) == digest
    manual = B.read(E.BATCH / "primary-adjudications.json")
    by_id = {r["id"]: r for r in manual}
    assert len(manual) == len(by_id)
    grid = []
    for row in B.read(E.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        E.R.assert_files(root, row["files"])
        cell = root.parent
        if not (cell / "result.json").exists():
            grid.append({"id": row["id"], "status": "NOT_RUN"})
            continue
        result = B.read(cell / "result.json")
        report = B.read(cell / "reviewer.json")
        judgment = by_id.pop(row["id"])
        assert type(judgment["correct"]) is bool and judgment["reason"]
        if judgment["correct"]:
            assert result["expected"] == result["observed"]
            assert not result["protected_drift"] and not result["infra_failure"]
            assert (
                report["evidence_observation_protocol"] == "reviewer-evidence-state-v1"
            )
        grid.append(
            {
                **result,
                "primary_adjudication": judgment,
                "report_sha256": B.sha(cell / "reviewer.json"),
            }
        )
    assert not by_id and len(grid) == 16
    executed = [r for r in grid if r.get("status") != "NOT_RUN"]
    correct = sum(r["primary_adjudication"]["correct"] for r in executed)
    state = (
        "PASS" if correct == 16 else "HOLD" if correct < len(executed) else "INCOMPLETE"
    )
    B.save(E.BATCH / "grid-results.json", grid)
    B.save(
        E.BATCH / "decision.json",
        {
            "qualification": state,
            "registered": 16,
            "executed": len(executed),
            "correct": correct,
            "not_run": 16 - len(executed),
            "criterion": "Original 16/16 substantive correctness",
            "r4_passed": False,
            "new_transfer_admitted": state == "PASS",
            "production_promoted": False,
            "old_failures_unchanged": True,
            "weekly_used": used,
            "usage_ceiling": 45,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    B.save(E.BATCH / "metrics.json", AUDIT.metrics(E.BATCH))
    baseline = B.read(E.BATCH / "baseline.json")
    for p, sha in baseline["old_decisions"].items():
        assert B.sha(Path(p)) == sha
    drift = [
        p
        for p, sha in baseline["files"].items()
        if not (B.KIT / p).is_file() or B.sha(B.KIT / p) != sha
    ]
    allowed = {
        "benchmarks/harness_r4_evidence.py",
        "docs/local-model-harness-convergence-plan.md",
    }
    assert set(drift) <= allowed, drift
    B.save(
        E.BATCH / "preservation.json",
        {
            "checked_files": len(baseline["files"]),
            "intentional_changes": drift,
            "live_pins_unchanged": True,
            "old_decisions_unchanged": True,
            "production_runtime_unchanged": True,
            "sibling_writes": False,
        },
    )
    print(
        {"qualification": state, "correct": correct, "executed": len(executed)},
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    main(parser.parse_args().used)
