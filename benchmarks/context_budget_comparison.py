"""Fresh-context retention-only review pairs plus verified Coder handoff."""

import argparse
import importlib.util
import json
import subprocess
import sys
import time

from capability_fit import KIT, WORK, write
from context_chain_experiment import BASE, SNAPSHOT, digest, read

BUDGET_SNAPSHOT = WORK / "roleq-context-budget-candidate-1"


def invoke(root, snapshot, config_path, request_path, report, trace):
    started = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            str(KIT / "benchmarks/context_request_observer.py"),
            "--snapshot",
            str(snapshot),
            "--role",
            "reviewer",
            "--trace",
            str(trace),
            "--request",
            str(request_path),
            "--config",
            str(config_path),
            "--report",
            str(report),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=1200,
    )
    return {
        "exit_code": result.returncode,
        "seconds": round(time.monotonic() - started, 2),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "primary_accepted": False,
    }


def coder_review():
    root = BASE / "coder-budgeted"
    spec = importlib.util.spec_from_file_location(
        "context_unit_gate", SNAPSHOT / ".local-agents/local-unit.py"
    )
    unit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unit)
    identity = unit.verify_handoff(root, read(root / ".agent/report.json"))
    request = {"schema_version": 1, **identity, "review_id": "verified-context-1"}
    path = root / ".agent/verified-review-request.json"
    write(path, request)
    result = invoke(
        root,
        SNAPSHOT,
        root / ".agent/config.json",
        path,
        root / ".agent/reviewer.json",
        root / "review-requests.jsonl",
    )
    write(root / "review-result.json", result)
    print(
        json.dumps({k: v for k, v in result.items() if k not in {"stdout", "stderr"}}),
        flush=True,
    )


def paired():
    base = WORK / "roleq-context-budget-comparison-1"
    base.mkdir(exist_ok=False)
    for relative, sha in read(BUDGET_SNAPSHOT / "freeze.json")["files"].items():
        if digest(BUDGET_SNAPSHOT / relative) != sha:
            raise ValueError("runtime drift")
    cells = [
        ("hidden", 1, "recent"),
        ("hidden", 1, "budgeted"),
        ("clean", 1, "budgeted"),
        ("clean", 1, "recent"),
        ("hidden", 2, "budgeted"),
        ("hidden", 2, "recent"),
        ("clean", 2, "recent"),
        ("clean", 2, "budgeted"),
    ]
    write(
        base / "plan.json",
        {
            "classification": "Development retention comparison, two repetitions; no role qualification",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "contracts": [
                "independent-source-evidence",
                "bounded-context",
                "immutable-history",
            ],
            "cells": cells,
            "single_axis": "reviewer_context_retention",
            "context_recovery": False,
            "snapshot": str(BUDGET_SNAPSHOT),
            "driver_sha256": digest(KIT / "benchmarks/context_budget_comparison.py"),
            "criterion": "Both hidden findings causal and fixes compatible, both clean reports without false defects; actual visibility retained; inspect any failure before promotion",
            "original_replay_candidate": "hold: eight recovery actions exhausted turns on clean; do not combine candidates",
            "weekly_ceiling": 40,
            "coordinator_started": False,
        },
    )
    for variant, repetition, retention in cells:
        root = BASE / f"reviewer-{variant}-off"
        label = f"{variant}-r{repetition}-{retention}"
        config = read(root / ".agent/config.json")
        config.update(
            reviewer_context_recovery=False, reviewer_context_retention=retention
        )
        request = read(root / ".agent/request.json")
        request["review_id"] = "budget-comparison-1-" + label
        cfg_path, req_path = (
            base / f"{label}-config.json",
            base / f"{label}-request.json",
        )
        write(cfg_path, config)
        write(req_path, request)
        result = invoke(
            root,
            BUDGET_SNAPSHOT,
            cfg_path,
            req_path,
            base / f"{label}-report.json",
            base / f"{label}-requests.jsonl",
        )
        result["label"] = label
        write(base / f"{label}-result.json", result)
        print(
            json.dumps(
                {k: v for k, v in result.items() if k not in {"stdout", "stderr"}}
            ),
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coder-review", action="store_true")
    args = parser.parse_args()
    if args.coder_review:
        coder_review()
    else:
        paired()
