"""Primary-only final receipts; no model calls or automatic semantic grading."""

import json
import subprocess
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import reviewer_bounded_trial as R
import supervised_acceptance as A


def legacy_probes(batch, cell):
    batch = Path(batch)
    root = Path(S.read(batch / "cells.json")[cell]["root"])
    origin = Path(R.source(cell)["root"])
    result = {}
    for label, source in (("parent", origin), ("child", root)):
        observed = T.run(
            [
                S.PYTHON,
                "-X",
                "utf8",
                "-B",
                S.KIT / "benchmarks/reviewer_rework_audit.py",
                "--root",
                source,
            ],
            source,
            timeout=120,
        )
        assert observed["exit_code"] == 0, observed
        result[label] = json.loads(observed["stdout"])
    result["unchanged_legacy_outcomes"] = (
        result["parent"]["rows"] == result["child"]["rows"]
    )
    S.save(batch / "primary" / cell / "legacy-probes.json", result)
    print(cell, "legacy unchanged", result["unchanged_legacy_outcomes"])


def record(
    batch, cell, *, decision, reason, source_correct, new_regression, reviewer_correct
):
    """Primary must inspect actual source, both diffs and evidence before calling."""
    batch = Path(batch)
    row = S.read(batch / "cells.json")[cell]
    root, identity = Path(row["root"]), row["identity"]
    result = S.read(batch / "results" / cell / "result.json")
    report = (
        S.read(root / ".agent/child-reviewer.json")
        if (root / ".agent/child-reviewer.json").exists()
        else {}
    )
    task, name = identity["task_id"], identity["run_id"]
    run = root / ".agent/tasks" / task / "runs" / name
    review = (
        root / ".agent/tasks" / task / "reviews" / ("auto-" + name) / "handoff.json"
    )
    disposition = None
    if decision == "accept":
        assert source_correct and not new_regression and result["all_checks_pass"]
        assert (
            not result["stop_batch"]
            and report["decision"] == "pass_to_primary"
            and not report["findings"]
        )
        canonical = S.read(review)
        disposition = {
            "schema_version": 1,
            "authority": "primary",
            "identity": canonical["identity"],
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
        }
        paths |= set(canonical["runtime_facts"]["observed_read_hashes"])
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
            "checks": result["checks"],
            "work": {
                "code_review": "Full current function and original parent plus child diff",
                "semantic_feedback": 0,
                "implementation_edits": 0,
                "cloud_tokens": "unknown",
                "active_seconds": "unknown",
            },
        }
        accepted = A.evaluate(root, task, name, disposition, primary)
        S.save(batch / "primary" / cell / "supervised-acceptance.json", accepted)
    elif decision != "replan":
        raise ValueError("Explicit final accept or replan only")
    dest = batch / "primary" / cell
    if disposition:
        S.save(dest / "disposition.json", disposition)
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
        decision,
        "--summary",
        reason,
        "--config",
        str(root / ".agent/config.json"),
    ]
    if disposition:
        cmd += ["--disposition", str(dest / "disposition.json")]
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
    assert done.returncode == 0, done.stderr
    S.save(
        dest / "judgment.json",
        {
            "decision": decision,
            "reason": reason,
            "source_correct": source_correct,
            "new_regression": new_regression,
            "reviewer_correct": reviewer_correct,
            "primary_semantic_feedback": 0,
            "primary_code_edits": 0,
            "source_sha256": S.sha(root / row["target"]),
            "local_team_assistance": True,
            "primary_cloud_tokens": "unknown",
            "primary_active_seconds": "unknown",
        },
    )
    print(cell, decision)


def close(batch, used):
    batch = Path(batch)
    registration = S.read(batch / "registration.json")
    assert all(S.sha(p) == h for p, h in registration["pins"].items())
    rows = []
    for cell in R.ORDER:
        result = S.read(batch / "results" / cell / "result.json")
        judgment = S.read(batch / "primary" / cell / "judgment.json")
        assert not result["protected_drift"]
        rows.append(
            {
                "cell": cell,
                "coder_status": result["coder_status"],
                "reviewer_decision": result["reviewer_decision"],
                "host": result["child"],
                "independent_checks": result["all_checks_pass"],
                "seconds": result["seconds"],
                "primary": judgment,
            }
        )
    accepted = sum(
        r["cell"].startswith("defect") and r["primary"]["decision"] == "accept"
        for r in rows
    )
    harm = sum(
        r["cell"].startswith("false-positive") and r["primary"]["new_regression"]
        for r in rows
    )
    metrics = {
        "registered": 4,
        "executed": 4,
        "not_run": 0,
        "defect_strict_accept": accepted,
        "false_positive_new_regressions": harm,
        "new_coder_requests": sum(r["host"]["actual"]["model_requests"] for r in rows),
        "new_coder_edits": sum(r["host"]["actual"]["edits"] for r in rows),
        "rows": rows,
    }
    S.save(batch / "metrics.json", metrics)
    S.save(
        batch / "closed-candidate-sources.json",
        {
            p: {"sha256": digest, "source": Path(p).read_text(encoding="utf-8")}
            for p, digest in registration["pins"].items()
            if Path(p).suffix == ".py"
        },
    )
    S.save(
        batch / "decision.json",
        {
            "gate_met": accepted == 2 and harm == 0,
            "status": "PASS_EXPOSED_FEEDBACK_COMPARISON"
            if accepted == 2 and harm == 0
            else "HOLD_FEEDBACK_COMPARISON",
            "weekly_used": used,
            "weekly_stop": 50,
            "r4_release": False,
            "coordinator_qualified": False,
            "production_enabled": False,
            "unknown_task_transfer": "not measured",
            "cloud_savings": "not established",
            "old_failures_preserved": True,
        },
    )
    S.save(
        batch / "handoff.json",
        {
            "state": "closed",
            "metrics": "metrics.json",
            "decision": "decision.json",
            "scope": "Only Coder-visible feedback changed. Original raw canonical feedback/Reviewer/contract/budget retained. Four exposed units, sequential comparison, no general qualification.",
            "primary_cost": "Fixture and experiment preparation plus final source/contract/probe audit; no runtime semantic guidance or implementation edits.",
        },
    )
    print(
        "Closed", accepted, "/2 defect accepts;", harm, "/2 false-positive regressions"
    )
