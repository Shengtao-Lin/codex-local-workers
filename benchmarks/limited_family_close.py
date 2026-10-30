"""Close the fixed scope qualification, never infer acceptance from green checks."""

import argparse
from pathlib import Path

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/limited-family-20261020-2"


def close(used):
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    cells = S.read(BATCH / "cells.json")
    rows = []
    for cell in reg["order"]:
        outcome = BATCH / "live-results" / cell / "result.json"
        if not outcome.exists():
            rows.append({"cell": cell, "status": "NOT_RUN", "accepted": False})
            continue
        result = S.read(outcome)
        row = cells[cell]
        root = Path(row["root"])
        identity = row["identity"]
        archive = (
            root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
        )
        review = archive / "review.json"
        primary = BATCH / "primary" / cell / "supervised-review.json"
        accepted = (
            primary.exists()
            and review.exists()
            and S.read(review)["decision"] == "accept"
        )
        if accepted:
            assert result["all_independent_pass"] and not result["protected_drift"]
        rows.append(
            {
                "cell": cell,
                "status": result["coder_status"],
                "accepted": accepted,
                "reviewer": result["summary"].get("reviewer_decision"),
                "independent_checks_pass": result["all_independent_pass"],
                "protected_drift": result["protected_drift"],
                "seconds": result["seconds"],
                "ledger": (result.get("ledger") or {}).get("actual", {}),
                "primary_semantic_hints": 0,
                "primary_implementation_edits": 0,
            }
        )
    accepted = sum(r["accepted"] for r in rows)
    old = S.read(BATCH / "baseline.json")["production"]
    drift = [p for p, h in old.items() if S.sha(S.KIT / p) != h]
    assert not drift
    S.save(
        BATCH / "metrics.json",
        {
            "rows": rows,
            "registered": 6,
            "executed": sum(r["status"] != "NOT_RUN" for r in rows),
            "accepted": accepted,
            "primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "runtime_seconds": sum(r.get("seconds", 0) for r in rows),
            "coder_totals": {
                key: sum(r.get("ledger", {}).get(key, 0) for r in rows)
                for key in (
                    "requests",
                    "edits",
                    "post_edit_checks",
                    "noops",
                    "protocol_recoveries",
                )
            },
            "production_drift": drift,
            "weekly_used": used,
            "weekly_stop": 50,
            "cost_claim": "No Primary-only control or complete cloud/time measurement; savings unknown",
        },
    )
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_LIMITED_CODER_REVIEWER_FAMILIES"
            if accepted == 6
            else "HOLD_LIMITED_FAMILIES",
            "accepted": accepted,
            "gate": reg["gate"],
            "old_HOLD": "Unchanged",
            "explorer": "NOT_TESTED_IN_THIS_BATCH",
            "coordinator": "NOT_ADMITTED",
            "production_default": "Unchanged; experimental entry only",
        },
    )
    S.save(
        BATCH / "handoff.json",
        {
            "bounded_scope_only": True,
            "general_capability_or_false_acceptance_guarantee": False,
            "primary_preparation": "Contracts, tests, references and fixed packets authored before live",
            "primary_runtime": "Final full diff and independent acceptance; no semantic rescue",
            "history": "Preparation -1 and all execution records retained; no old score overwritten",
        },
    )
    print({"accepted": accepted, "registered": 6, "production_drift": drift})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--weekly-used", type=int, required=True)
    close(p.parse_args().weekly_used)
