"""Close matched repair diagnostics without granting independent review credit."""

import subprocess

import static_focus_matched as M


def close(used):
    rows = []
    cells = M.S.read(M.BATCH / "cells.json")
    for cell in M.ORDER:
        row = cells[cell]
        root = M.Path(row["root"])
        result = M.S.read(M.BATCH / "live-results" / cell / "result.json")
        identity = row["identity"]
        command = [
            M.S.PYTHON,
            "-B",
            root / ".local-agents/record-review.py",
            "--repo",
            root,
            "--task-id",
            identity["task_id"],
            "--run-id",
            identity["run_id"],
            "--decision",
            "replan",
            "--summary",
            "Coder-only matched diagnostic complete. No Reviewer or full-chain acceptance; preserve original outcome.",
        ]
        receipt = subprocess.run(
            [str(x) for x in command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        M.S.save(
            M.BATCH / "primary" / cell / "record.json",
            {
                "exit_code": receipt.returncode,
                "stdout": receipt.stdout,
                "stderr": receipt.stderr,
            },
        )
        if receipt.returncode:
            raise ValueError("Primary diagnostic closure failed")
        rows.append(
            {
                "cell": cell,
                "arm": cell.split("-")[1],
                "all_checks": result["all_independent_pass"]
                and result["coder_status"] == "validation_passed_pending_review",
                "seconds": result["seconds"],
                "ledger": result["ledger"]["actual"],
                "stop_batch": result["stop_batch"],
            }
        )
    counts = {
        arm: sum(r["arm"] == arm and r["all_checks"] for r in rows)
        for arm in ("A", "B")
    }
    M.S.save(
        M.BATCH / "metrics.json",
        {
            "registered": 8,
            "executed": 8,
            "not_run": 0,
            "coder_checks": counts,
            "Reviewer_runs": 0,
            "full_chain_accepts": 0,
            "rows": rows,
            "Primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
        },
    )
    M.S.save(
        M.BATCH / "decision.json",
        {
            "status": "PASS_NARROW_DIAGNOSTIC"
            if counts["B"] == 4 and not any(r["stop_batch"] for r in rows)
            else "HOLD",
            "A": counts["A"],
            "B": counts["B"],
            "denominator_per_arm": 4,
            "weekly_used": used,
            "weekly_stop": 40,
            "confirmed": "Same single-helper draft A0/2 B2/2; two-helper draft A2/2 B2/2. All successful actual diffs only add missing annotations; no behavior repair or protected changes. Existing runtime parser data was omitted from the consolidated context and is useful on this small sample.",
            "limits": "Two exposed drafts, not general model capability or full-chain qualification. Role/model/safety/budget unchanged; no handoff or Coordinator promotion.",
        },
    )
    print(counts)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--weekly-used", type=int, required=True)
    close(p.parse_args().weekly_used)
