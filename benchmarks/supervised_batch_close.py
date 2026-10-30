"""Close one fixed batch; never pool trials or revise canonical history."""

import argparse
import subprocess
from pathlib import Path

import bounded_evidence_support as S


def close(batch, used):
    registration = S.read(batch / "registration.json")
    cells = S.read(batch / "cells.json")
    rows = []
    for cell in registration["order"]:
        record = batch / "live-results" / cell / "result.json"
        if not record.exists():
            rows.append({"cell": cell, "status": "NOT_RUN"})
            continue
        result = S.read(record)
        row = cells[cell]
        root = Path(row["root"])
        name = row["identity"]["run_id"]
        run = root / ".agent/tasks" / name / "runs" / name
        accepted = batch / "primary" / cell / "supervised-review.json"
        if not accepted.exists() and not (run / "review.json").exists():
            cmd = [
                str(S.PYTHON), "-B", str(root / ".local-agents/record-review.py"),
                "--repo", str(root), "--task-id", name, "--run-id", name,
                "--decision", "replan", "--summary",
                "Fixed trial did not establish complete independent acceptance. Preserve partial edits, checks and reviewer outcome; no rescue or automatic rework.",
            ]
            outcome = subprocess.run(cmd, capture_output=True, text=True, check=False)
            S.save(batch / "primary" / cell / "strict-record-command.json", {
                "exit_code": outcome.returncode, "stdout": outcome.stdout, "stderr": outcome.stderr,
            })
            if outcome.returncode:
                raise ValueError("Failed to preserve Primary decision")
        strict = S.read(run / "review.json")["decision"]
        ledger = (result.get("ledger") or {}).get("actual", {})
        rows.append(
            {
                "cell": cell,
                "status": result["coder_status"],
                "supervised_accepted": accepted.exists(),
                "strict_decision": strict,
                "reviewer": result["summary"].get("reviewer_decision"),
                "independent_all_pass": result["all_independent_pass"],
                "protected_drift": result["protected_drift"],
                "seconds": result["seconds"],
                "ledger": ledger,
            }
        )
    executed = sum(r["status"] != "NOT_RUN" for r in rows)
    accepted = sum(r.get("supervised_accepted", False) for r in rows)
    stats = {
        "rows": rows,
        "registered": len(rows),
        "executed": executed,
        "not_run": len(rows) - executed,
        "supervised_accepted": accepted,
        "strict_accepted": sum(r.get("strict_decision") == "accept" for r in rows),
        "unit_seconds": sum(r.get("seconds", 0) for r in rows),
        "primary_active_time": "unknown",
        "cloud_tokens": "unknown",
        "primary_semantic_hints": 0,
        "primary_implementation_edits": 0,
        "local_retry": {
            k: sum(r.get("ledger", {}).get(k, 0) for r in rows)
            for k in (
                "model_requests",
                "edits",
                "post_edit_checks",
                "protocol_recoveries",
                "noops",
            )
        },
    }
    S.save(batch / "metrics.json", stats)
    S.save(
        batch / "decision.json",
        {
            "status": "PASS_FIXED_SUPERVISED_REPEAT"
            if accepted == len(rows)
            else "HOLD_FIXED_SUPERVISED_REPEAT",
            "registered": len(rows),
            "executed": executed,
            "accepted": accepted,
            "weekly_used": used,
            "weekly_stop": 40,
            "qualification": "Only this registered scope; Explorer independently pending and Coordinator not admitted",
            "history": "Prior trials remain separate; no inference of general capability or cost savings",
        },
    )
    print(
        {
            k: stats[k]
            for k in (
                "registered",
                "executed",
                "supervised_accepted",
                "strict_accepted",
            )
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("batch", type=Path)
    p.add_argument("--weekly-used", type=int, required=True)
    args = p.parse_args()
    close(args.batch.resolve(), args.weekly_used)
