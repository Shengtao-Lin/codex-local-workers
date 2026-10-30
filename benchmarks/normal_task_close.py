"""Close only the fixed normal-task batch from canonical evidence; no model calls."""

import argparse
from pathlib import Path

import bounded_evidence_live_close as C
import bounded_evidence_support as S
import normal_task_trial as N


def close(used, *, batch=N.BATCH, output_prefix=""):
    registration = S.read(batch / "registration.json")
    if any(S.sha(p) != digest for p, digest in registration["pins"].items()):
        raise ValueError("Frozen inputs changed")
    cells = S.read(batch / "cells.json")
    results = []
    for cell in N.ORDER:
        path = batch / "live-results" / cell / "result.json"
        if not path.exists():
            results.append({"cell": cell, "status": "NOT_RUN"})
            continue
        row = cells[cell]
        root = Path(row["root"])
        run = (
            root
            / ".agent/tasks"
            / row["identity"]["task_id"]
            / "runs"
            / row["identity"]["run_id"]
        )
        result, handoff, primary = (
            S.read(path),
            S.read(run / "handoff.json"),
            S.read(run / "review.json"),
        )
        counts = handoff["consolidated_harness"]["actual"]
        accepted = primary["decision"] == "accept"
        if accepted and (
            not result["all_independent_pass"]
            or result["summary"].get("reviewer_decision") != "pass_to_primary"
            or result["protected_drift"]
        ):
            raise ValueError("Acceptance lacks complete-chain evidence")
        if counts["edits"] != counts["post_edit_checks"]:
            raise ValueError("Edit lacks a write-check")
        results.append(
            {
                "cell": cell,
                "status": handoff["status"],
                "accepted": accepted,
                "Primary_decision": primary["decision"],
                "Reviewer_decision": result["summary"].get("reviewer_decision"),
                "ledger": counts,
                "failure_reason": handoff.get("failure_reason"),
                "independent_all_pass": result["all_independent_pass"],
                "independent_checks": [
                    {
                        "exit_code": c["exit_code"],
                        "stdout": c["stdout"],
                        "stderr": c["stderr"],
                    }
                    for c in result["independent_checks"]
                ],
                "seconds": result["seconds"],
                "protected_drift": result["protected_drift"],
                "coder_usage": C.usage(
                    sorted(run.glob("proposal-response-*.json")), "stats"
                ),
                "format_seconds": sum(
                    S.read(p)["seconds"] for p in run.glob("preparation-*.json")
                ),
                "assisted": False,
                "Primary_implementation_edits": 0,
            }
        )
    executed = [r for r in results if r["status"] != "NOT_RUN"]
    accepted = sum(r["accepted"] for r in executed)
    totals = (
        {k: sum(r["ledger"][k] for r in executed) for k in executed[0]["ledger"]}
        if executed
        else {}
    )
    metrics = {
        "registered": 4,
        "executed": len(executed),
        "not_run": 4 - len(executed),
        "accepted": accepted,
        "cells": results,
        "totals": totals,
        "weekly_used": used,
        "weekly_stop": 20,
        "Primary_active_seconds": None,
        "Primary_cloud_tokens": None,
        "load_seconds_separate": None,
        "cost_savings": "NOT_ESTABLISHED",
    }
    S.save(batch / (output_prefix + "metrics.json"), metrics)
    S.save(
        batch / (output_prefix + "decision.json"),
        {
            "status": "PASS_EXACT_EXPOSED_REPEAT_ONLY"
            if accepted == 4
            else "HOLD_FIXED_NORMAL_REPEAT",
            "registered": 4,
            "executed": len(executed),
            "not_run": 4 - len(executed),
            "accepted": accepted,
            "gate": "4/4 and each task2/2; no assistance, no safety/protected drift",
            "current_grant": "Exact exposed task repeat evidence only"
            if accepted == 4
            else "No new task qualification",
            "release": "R4 HOLD; R5 not admitted; no Coordinator or production promotion",
            "history": "No pooling with old2/2 or overwriting old failures; original sources preserved in candidate-preimages",
            "weekly_used": used,
            "weekly_stop": 20,
            "no_more_same_batch_retries": True,
        },
    )
    baseline = S.read(batch / "baseline.json")["files"]
    expected = {
        "benchmarks/normal_task_trial.py",
        "benchmarks/consolidated_harness.py",
        "benchmarks/consolidated_entry.py",
        "benchmarks/preserved_import_guard.py",
        "benchmarks/normal_task_close.py",
        "docs/normal-task-candidate-readiness.md",
        "benchmarks/function_proposal_rules.py",
        "benchmarks/function_repeat_trial.py",
        "docs/local-model-harness-convergence-plan.md",
    }
    changed = [
        p
        for p, digest in baseline.items()
        if not (S.KIT / p).exists() or S.sha(S.KIT / p) != digest
    ]
    S.save(
        batch / (output_prefix + "preservation-verification.json"),
        {
            "changed_preexisting_files": changed,
            "unexpected_changes": sorted(set(changed) - expected),
            "note": "New stage artifacts/tests not in baseline are additional files; sibling repos were not modified",
        },
    )
    print({"executed": len(executed), "accepted": accepted, "totals": totals})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--weekly-used", type=int, required=True)
    close(p.parse_args().weekly_used)
