"""Independent checks and explicit Primary receipts for the fixed recovery pair."""

import subprocess
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import explorer_inherited_trial as R
import mapping_recovery_trial as M
import supervised_acceptance as A


def check(cell):
    row = S.read(R.BATCH / "cells.json")[cell]
    root = Path(row["root"])
    private = S.read(M.BATCH / "cells.json")[cell]["private_tests"]
    commands = [
        [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", private],
        [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
        [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
        [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
    ]
    result = [T.run(command, root, timeout=120) for command in commands]
    S.save(R.BATCH / "primary" / cell / "independent-checks.json", result)
    print(cell, [r["exit_code"] for r in result])


def record(cell, reason, explorer_assessment):
    # Called only after Primary reads actual source/diff, Reviewer and Explorer.
    row = S.read(R.BATCH / "cells.json")[cell]
    root = Path(row["root"])
    result = S.read(R.BATCH / "results" / cell / "result.json")
    identity = {k: result["identity"][k] for k in ("task_id", "unit_id", "run_id")}
    task, name = identity["task_id"], identity["run_id"]
    archive = root / ".agent/tasks" / task / "runs" / name
    handoff = (
        root / ".agent/tasks" / task / "reviews" / ("auto-" + name) / "handoff.json"
    )
    report = S.read(handoff)
    checks = S.read(R.BATCH / "primary" / cell / "independent-checks.json")
    assert all(c["exit_code"] == 0 for c in checks)
    assert (
        not result["stop_batch"]
        and report["decision"] == "pass_to_primary"
        and not report["findings"]
    )
    disposition = {
        "schema_version": 1,
        "authority": "primary",
        "identity": report["identity"],
        "report_sha256": S.sha(handoff),
        "resolution": "cleared",
        "evidence": [reason],
        "findings": [],
    }
    paths = {
        p.relative_to(root).as_posix()
        for p in (
            archive / "handoff.json",
            archive / "packet.json",
            archive / "validation.json",
            archive / "cumulative.diff",
            handoff,
            root / ".agent/config.json",
        )
    }
    paths |= set(report["runtime_facts"]["observed_read_hashes"])
    paths |= set(S.read(archive / "post-state.json")["validation_inputs"])
    primary = {
        "authority": "primary",
        "identity": identity,
        "decision": "accept",
        "reason": reason,
        "assisted": False,
        "takeover": False,
        "complete_profile": True,
        "bindings": {p: S.sha(root / p) for p in paths},
        "checks": checks,
        "work": {
            "code_review": "full actual source/diff",
            "semantic_feedback": 0,
            "implementation_edits": 0,
            "cloud_tokens": "unknown",
            "active_seconds": "unknown",
        },
    }
    acceptance = A.evaluate(root, task, name, disposition, primary)
    dest = R.BATCH / "primary" / cell
    S.save(dest / "disposition.json", disposition)
    S.save(dest / "primary.json", primary)
    S.save(dest / "supervised-review.json", acceptance)
    S.save(dest / "explorer-assessment.json", explorer_assessment)
    cmd = [
        str(S.PYTHON),
        "-B",
        str(root / ".local-agents/record-review.py"),
        "--repo",
        str(root),
        "--task-id",
        task,
        "--run-id",
        name,
        "--decision",
        "accept",
        "--summary",
        reason,
        "--config",
        str(root / ".agent/config.json"),
        "--disposition",
        str(dest / "disposition.json"),
    ]
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)
    S.save(
        dest / "strict-record-command.json",
        {
            "argv": cmd,
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        },
    )
    assert process.returncode == 0, process.stderr
    print(cell, "strict and supervised accept; Explorer independently assessed")


def close(used):
    rows = []
    for cell in R.ORDER:
        result = S.read(R.BATCH / "results" / cell / "result.json")
        dest = R.BATCH / "primary" / cell
        assert S.read(dest / "strict-record-command.json")["exit_code"] == 0
        assert S.read(dest / "primary.json")["decision"] == "accept"
        parent, child = result["parent_coder"], result["child_coder"]
        assert parent["actual"]["requests"] + child["actual"]["requests"] <= 12
        assert parent["seconds"] + child["seconds"] <= 900
        rows.append(
            {
                "id": cell,
                "strict_accept": True,
                "fresh_explorer_causal_diagnosis": "supported",
                "explorer_fully_factual": S.read(dest / "explorer-assessment.json")[
                    "fully_factual_report"
                ],
                "parent_requests": parent["actual"]["requests"],
                "child_requests": child["actual"]["requests"],
                "child_edits": child["actual"]["edits"],
                "child_post_checks": child["actual"]["post_edit_checks"],
                "child_noops": child["actual"]["noops"],
                "reviewer": result["reviewer_decision"],
                "seconds": result["seconds"],
                "primary_semantic_feedback": 0,
                "primary_code_edits": 0,
                "parent_failure_preserved": True,
            }
        )
    metrics = {
        "registered": 2,
        "executed": 2,
        "strict_full_chain_accept": 2,
        "fresh_explorer_main_cause_supported": 2,
        "clean_explorer_reports": 0,
        "primary_runtime_semantic_feedback": 0,
        "primary_code_edits": 0,
        "cloud_tokens": "unknown",
        "primary_active_seconds": "unknown",
        "rows": rows,
    }
    S.save(R.BATCH / "metrics.json", metrics)
    S.save(
        R.BATCH / "decision.json",
        {
            "status": "PASS_EXPOSED_RECOVERY_MECHANISM_EXPLORER_QUALITY_HOLD",
            "full_chain": "2/2 fresh local research to inherited Coder, host checks, fresh Reviewer and strict Primary accept",
            "qualification": "Two implementations of ONE exposed task, not two task families or a new-task transfer.",
            "explorer": "Correct main causal diagnosis2/2, clean factual/citation report0/2; contradictory claim and inaccurate free-text line hints retained separately.",
            "autonomy": "No manual note curation, semantic feedback or code edits between roles. Primary still prepared the experiment and performed independent final acceptance.",
            "r4_release": False,
            "coordinator_qualified": False,
            "production_enabled": False,
            "reviewer_auto_rework_authorized": False,
            "weekly_used": used,
            "weekly_stop": 50,
        },
    )
    S.save(
        R.BATCH / "handoff.json",
        {
            "state": "closed",
            "decision": "decision.json",
            "metrics": "metrics.json",
            "bounds": "Default-off experiment only. No production defaults, old scores, sibling files or Git operations changed.",
            "remaining": "Independent unseen-task transfer, clean Explorer causal evidence and Reviewer-to-Coder authority not established; do not call general E/C/R stable.",
            "critical_policy": "Current policy requires Primary finding-by-finding disposition before Reviewer-based rework. Fully automatic semantic rework would change authority and remains pending explicit decision.",
        },
    )
    print(
        "Recovery pair closed2/2 strict accept; Explorer quality/general release HOLD"
    )
