"""Shared immutable closure for installed-entry qualification batches."""

import argparse
from pathlib import Path

import bounded_evidence_support as S

WORK = S.KIT / "benchmarks/work/harness-convergence"


def close(batch, used):
    batch = Path(batch).resolve()
    assert batch.is_relative_to(WORK) and 0 <= used <= 100
    reg = S.read(batch / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    cells = S.read(batch / "cells.json")
    rows = []
    for cell in reg["order"]:
        path = batch / "live-results" / cell / "result.json"
        if not path.exists():
            rows.append({"cell": cell, "status": "NOT_RUN", "accepted": False})
            continue
        result, row = S.read(path), cells[cell]
        root, identity = Path(row["root"]), row["identity"]
        run = root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
        strict = (
            S.read(run / "review.json")["decision"]
            if (run / "review.json").exists()
            else "NOT_RECORDED"
        )
        accepted = (batch / "primary" / cell / "supervised-review.json").exists()
        if accepted:
            assert result["all_independent_pass"] and not result["protected_drift"]
        rows.append(
            {
                "cell": cell,
                "status": result["coder_status"],
                "accepted": accepted,
                "strict_decision": strict,
                "reviewer": result["summary"].get("reviewer_decision"),
                "all_independent_pass": result["all_independent_pass"],
                "seconds": result["seconds"],
                "protected_drift": result["protected_drift"],
                "stopped": result["stop_batch"],
                "ledger": (result.get("ledger") or {}).get("actual", {}),
            }
        )
    accepted = sum(r["accepted"] for r in rows)
    S.save(
        batch / "metrics.json",
        {
            "registered": len(rows),
            "executed_launches": sum(r["status"] != "NOT_RUN" for r in rows),
            "accepted": accepted,
            "rows": rows,
            "strict_accepts": sum(r.get("strict_decision") == "accept" for r in rows),
            "local_seconds": sum(r.get("seconds", 0) for r in rows),
            "coder_totals": {
                k: sum(r.get("ledger", {}).get(k, 0) for r in rows)
                for k in (
                    "model_requests",
                    "edits",
                    "initial_checks",
                    "post_edit_checks",
                    "noops",
                    "protocol_recoveries",
                )
            },
            "primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "primary_runtime_semantic_hints": 0,
            "primary_implementation_edits": 0,
            "weekly_used": used,
            "weekly_stop": 50,
            "primary_preparation": reg.get("Primary"),
            "cost_savings": "Not established",
        },
    )
    S.save(
        batch / "decision.json",
        {
            "status": "PASS_FIXED_INSTALLED_SCOPE"
            if accepted == len(rows)
            else "HOLD_FIXED_INSTALLED_SCOPE",
            "accepted": accepted,
            "registered": len(rows),
            "gate": reg["gate"],
            "old_failures": "Unchanged; earlier infrastructure launches remain separate, not model quality failures",
            "coordinator": "NOT_ADMITTED_BY_THIS_BATCH",
            "production_defaults": "Unchanged",
        },
    )
    S.save(
        batch / "handoff.json",
        {
            "candidate": reg["candidate"],
            "exposure": reg.get("exposure"),
            "qualification": "Only this installed profile, scope and task families; not general release",
            "acceptance": "Primary decisions independently bound to current full profile, source and fresh Reviewer",
            "history": "All failed launches, attempts and ordinary outcomes retained; no resampling",
            "no_commit_push": True,
        },
    )
    print({"accepted": accepted, "registered": len(rows)})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("batch", type=Path)
    p.add_argument("--weekly-used", type=int, required=True)
    args = p.parse_args()
    close(args.batch, args.weekly_used)
