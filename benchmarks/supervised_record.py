"""Record a Primary-reviewed fresh result without rewriting strict history."""

import argparse
import subprocess
from pathlib import Path

import bounded_evidence_support as S
import supervised_acceptance as A
from supervised_release_checkpoint import BATCH


def record(cell, reason, disposition_path=None, batch=BATCH):
    BATCH = Path(batch).resolve()
    row = S.read(BATCH / "cells.json")[cell]
    root = Path(row["root"])
    identity = row["identity"]
    name = identity["run_id"]
    run = root / ".agent/tasks" / name / "runs" / name
    review = (
        root / ".agent/tasks" / name / "reviews" / ("auto-" + name) / "handoff.json"
    )
    report = S.read(review)
    result = S.read(BATCH / "live-results" / cell / "result.json")
    if (
        not result["all_independent_pass"]
        or result["protected_drift"]
        or result["stop_batch"]
    ):
        raise ValueError("Cannot accept failed or interrupted unit")
    if disposition_path:
        disposition = S.read(disposition_path)
    else:
        if report["decision"] != "pass_to_primary" or report["findings"]:
            raise ValueError(
                "Primary must explicitly adjudicate nonempty/non-PASS report"
            )
        disposition = {
            "schema_version": 1,
            "authority": "primary",
            "identity": report["identity"],
            "report_sha256": S.sha(review),
            "resolution": "cleared",
            "evidence": [reason],
            "findings": [],
        }
    paths = {
        p.relative_to(root).as_posix()
        for p in (
            run / "handoff.json",
            run / "packet.json",
            run / "validation.json",
            run / "cumulative.diff",
            review,
            root / ".agent/config.json",
        )
    } | set(report["runtime_facts"]["observed_read_hashes"])
    paths |= set(S.read(run / "post-state.json")["validation_inputs"])
    primary = {
        "authority": "primary",
        "identity": identity,
        "decision": "accept",
        "reason": reason,
        "assisted": False,
        "takeover": False,
        "complete_profile": True,
        "bindings": {p: S.sha(root / p) for p in paths},
        "checks": result["independent_checks"],
        "work": {
            "code_review": "full changed file and actual diff",
            "semantic_feedback": 0,
            "implementation_edits": 0,
            "cloud_tokens": "unknown",
            "active_seconds": "unknown",
        },
    }
    supervised = A.evaluate(root, name, name, disposition, primary)
    dest = BATCH / "primary" / cell
    S.save(dest / "disposition.json", disposition)
    S.save(dest / "primary.json", primary)
    S.save(dest / "supervised-review.json", supervised)
    # Strict historical meaning is retained even when the new supervised mode accepts.
    decision = "accept" if report["decision"] == "pass_to_primary" else "replan"
    cmd = [
        str(S.PYTHON),
        "-B",
        str(root / ".local-agents/record-review.py"),
        "--repo",
        str(root),
        "--task-id",
        name,
        "--run-id",
        name,
        "--decision",
        decision,
        "--summary",
        reason,
        "--config",
        str(root / ".agent/config.json"),
        "--disposition",
        str(dest / "disposition.json"),
    ]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    S.save(
        dest / "strict-record-command.json",
        {
            "argv": cmd,
            "exit_code": done.returncode,
            "stdout": done.stdout,
            "stderr": done.stderr,
        },
    )
    if done.returncode:
        raise ValueError(
            "Strict record command failed; separate supervised result retained"
        )
    print(cell, "supervised accept; strict", decision)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cell")
    p.add_argument("--reason", required=True)
    p.add_argument("--disposition", type=Path)
    p.add_argument("--batch", type=Path, default=BATCH)
    args = p.parse_args()
    record(args.cell, args.reason, args.disposition, args.batch)
