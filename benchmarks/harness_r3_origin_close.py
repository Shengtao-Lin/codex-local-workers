"""Close the fixed-origin batch without changing any execution evidence."""

import argparse
import ast
import json
from pathlib import Path

import harness_r3_origin_fixed as F

B = F.B


def close(used):
    frozen = B.read(F.BATCH / "live-freeze-approved.json")
    F.R.assert_files(B.KIT, frozen["candidate_and_driver"])
    audit = B.read(F.BATCH / "handoff-boundary-audit.json")
    assert audit["canonical_verifier_passed"] and audit["compact_verifier_failure"]
    rows, metrics = [], []
    for name in F.P.ORDER:
        case = F.BATCH / "cases" / name
        if not (case / "result.json").exists():
            assert not (case / "started.json").exists()
            F.O.require_origin(case / "isolated", F.origins()[name.split("-")[0]])
            rows.append(
                {
                    "case": name,
                    "status": "NOT_RUN",
                    "reason": "Frozen candidate CLI handoff failure; gate unreachable",
                }
            )
            continue
        row = B.read(case / "result.json")
        entry = B.read(case / "entry-result.json")
        row.update(execution="EXECUTED", entry_summary=json.loads(entry["stdout"]))
        row["classification"] = (
            "harness_cli_serialization_failure"
            if "-candidate-" in name
            else "model_noop_no_progress"
        )
        rows.append(row)
        calls = []
        for response in sorted((case / "wire").glob("*-response.json")):
            capture = B.read(response)
            wire = json.loads(capture["raw"])
            calls.append(
                {
                    "response": str(response),
                    "model": wire["model"],
                    "usage": wire.get("usage"),
                    "seconds": capture["seconds"],
                }
            )
        metrics.append(
            {
                "case": name,
                "calls": calls,
                "unit_seconds": row["seconds"],
                "reviewer_calls": 0,
                "primary_active_seconds": None,
                "load_seconds": None,
            }
        )
    assert sum(row.get("execution") == "EXECUTED" for row in rows) == 2
    candidate = F.BATCH / "cases/repair-candidate-1/isolated"
    packet = B.read(candidate / ".agent/packet.json")
    archive = candidate / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    before = archive / "preimages" / B.SOURCE
    after = candidate / B.SOURCE

    def without_target_doc(path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        owner = next(
            n
            for n in tree.body
            if isinstance(n, ast.ClassDef) and n.name == "MlflowTraceSource"
        )
        method = next(
            n
            for n in owner.body
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "get_many"
        )
        assert isinstance(method.body[0], ast.Expr) and isinstance(
            method.body[0].value, ast.Constant
        )
        method.body = method.body[1:]
        return ast.dump(tree, include_attributes=False)

    assert without_target_doc(before) == without_target_doc(after)
    B.save(
        F.BATCH / "primary-source-audit.json",
        {
            "full_diff_reviewed": True,
            "only_target_docstring_changed": True,
            "entire_module_ast_except_target_docstring_equal": True,
            "before_sha256": B.sha(before),
            "after_sha256": B.sha(after),
            "primary_acceptance": False,
            "reason": "Independent Reviewer did not run",
        },
    )
    B.save(F.BATCH / "grid-results.json", rows)
    totals = {
        key: sum(call["usage"][key] for item in metrics for call in item["calls"])
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    B.save(
        F.BATCH / "metrics.json",
        {
            "cells": metrics,
            "observed_local_tokens": totals,
            "cloud_tokens": None,
            "cost_saving_claim": False,
            "weekly_used_start": 6,
            "weekly_used_end": used,
        },
    )
    baseline = B.read(F.BATCH / "baseline.json")
    allowed = {
        str(B.KIT / "benchmarks/harness_r3_origin_fixed.py"): F.BATCH
        / "checkpoint/driver-before-import-order.py.txt",
        str(B.KIT / "docs/local-model-harness-convergence-plan.md"): F.BATCH
        / "checkpoint/plan-before-close.md",
    }
    for name, checkpoint in allowed.items():
        assert B.sha(checkpoint) == baseline[name], name
    drift = []
    for index, (name, digest) in enumerate(baseline.items()):
        if name not in allowed and (
            not Path(name).is_file() or B.sha(Path(name)) != digest
        ):
            drift.append(name)
        if index and index % 20000 == 0:
            print(f"Final preservation {index}", flush=True)
    B.save(
        F.BATCH / "preservation-final.json",
        {
            "checked": len(baseline),
            "unexpected_drift": drift,
            "passed": not drift,
            "intentional_changes": [
                {
                    "path": name,
                    "preimage": str(checkpoint),
                    "before": baseline[name],
                    "after": B.sha(Path(name)),
                    "reason": "Pre-live import ordering of new driver"
                    if name.endswith(".py")
                    else "Post-run plan status update",
                }
                for name, checkpoint in allowed.items()
            ],
            "production_and_old_drivers_unchanged": True,
        },
    )
    assert not drift
    B.save(
        F.BATCH / "final-environment.json",
        {
            "weekly_used": used,
            "ceiling": 30,
            "head": B.command(["git", "rev-parse", "HEAD"]),
            "status": B.command(["git", "status", "--short"]),
            "diff_check": B.command(["git", "diff", "--check"]),
            "models": B.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
            "siblings_read_only": True,
        },
    )
    B.save(
        F.BATCH / "decision.json",
        {
            "stage": "R3",
            "qualification": "HOLD",
            "experiment_validity": "VALID",
            "integration_result": "FAIL",
            "r2_qualification_unchanged": True,
            "candidate_freeze": str(F.BATCH / "live-freeze-approved.json"),
            "candidate_freeze_sha256": B.sha(F.BATCH / "live-freeze-approved.json"),
            "registered": 12,
            "executed": 2,
            "not_run": 10,
            "candidate": {
                "registered": 6,
                "executed": 1,
                "all_checks_pass": 1,
                "complete_chain_accept": 0,
                "not_run": 5,
            },
            "baseline": {
                "registered": 6,
                "executed": 1,
                "all_checks_pass": 0,
                "complete_chain_accept": 0,
                "not_run": 5,
            },
            "reviewer_calls": 0,
            "reviewer_capability": "NOT_EVALUATED",
            "model_capability": "One valid static-repair proposal succeeds; repetition and transfer unmeasured. Not a general capability verdict.",
            "failure_classification": "Deterministic CLI compact report drops execution_protocol before independent review",
            "safety": "Fail closed; no unsafe acceptance or protection drift",
            "primary_intervention": "Experiment preparation, no live semantic hints/edits; read-only post-run source and boundary audit",
            "unknowns": [
                "Repeated repair success",
                "presence transfer",
                "Reviewer live compatibility",
                "Primary active time/cloud tokens",
                "R4/R5",
            ],
            "r4_admitted": False,
            "r4_live_started": False,
            "usage_start": 6,
            "usage_end": used,
            "usage_ceiling": 30,
            "stop_reason": "Valid deterministic integration failure makes frozen complete-chain gate unreachable",
            "next_action": "Seek separate authorization for serializer-only protocol/unknown-assessment preservation and installed CLI end-to-end offline controls, then register a fresh fixed full-chain batch. No prompt/model/budget/receiver-gate change.",
        },
    )
    print(
        json.dumps(
            {
                "closed": True,
                "local_tokens": totals,
                "unexpected_drift": drift,
                "qualification": "HOLD",
                "integration": "FAIL",
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
