"""Single-axis inherited recovery: old versus node-ID test-prefetch runtime."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "quixbugs-repair-prefetch-1"
OLD = WORK / "coordinator-report-baseline-2"
CANDIDATE = WORK / "quixbugs-node-prefetch-baseline-1"
PARENT = WORK / "coordinator-quixbugs-wrap-1"


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(CANDIDATE.name)
    manifest = read(PARENT / "manifest.json")
    cells = []
    feedback = [
        {
            "text": "Use the inherited runtime failure traceback to repair the current failed draft. Preserve the complete original contract and every protected test. Validate actual edits. No semantic answer, implementation example, scope expansion or new budget is supplied by Primary.",
            "verify_in_review": False,
        }
    ]
    for arm, identity, snapshot in (
        ("control", "control-r1", OLD),
        ("candidate", "control-r2", CANDIDATE),
    ):
        root = Path(
            next(cell for cell in manifest["cells"] if cell["id"] == identity)["root"]
        )
        parent = read(root / ".agent/normalize-unit-bound.json")
        child = {key: parent[key] for key in ("schema_version", "task_id", "unit_id")}
        child.update(
            run_id=parent["run_id"] + "-node-prefetch-a2",
            parent_run_id=parent["run_id"],
            preserve_contract=True,
            attempt=2,
            plan_revision=1,
            packet_revision=2,
            review_feedback=feedback,
        )
        worker = load_worker(snapshot)
        resolved = worker.resolve_inherited_packet(root, child)
        worker.validate_packet(resolved)
        if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
            raise ValueError("parent source drift")
        child_path = root / ".agent/node-prefetch-a2.json"
        write(child_path, child)
        cells.append(
            {
                "arm": arm,
                "root": str(root),
                "runtime": str(snapshot),
                "child": str(child_path),
                "child_sha256": digest(child_path),
                "parent_run_id": parent["run_id"],
                "run_id": child["run_id"],
                "task_id": child["task_id"],
                "inputs": {
                    path: digest(root / path)
                    for path in (
                        "src/product/target.py",
                        "tests/test_target.py",
                        "tests/official-wrap.json",
                        "pyproject.toml",
                        ".agent/config.json",
                    )
                },
            }
        )
    if cells[0]["inputs"] != cells[1]["inputs"]:
        raise ValueError("paired inherited inputs differ")
    # Only runtime implementation and its regression tests may differ from the
    # old production freeze; no accidental model/profile/role change is allowed.
    changed = [
        path
        for path, sha in read(OLD / "freeze.json")["files"].items()
        if digest(CANDIDATE / path) != sha
    ]
    if set(changed) != {
        ".local-agents/worker-runtime.py",
        ".local-agents/tests/test_worker_runtime.py",
    }:
        raise ValueError("unexpected candidate drift: " + repr(changed))
    write(
        BASE / "manifest.json",
        {
            "cells": cells,
            "changed_runtime_paths": changed,
            "weekly_used_start": 7,
            "weekly_used_ceiling": 15,
            "driver_sha256": digest(Path(__file__)),
            "classification": "Fresh inherited repair, not initial benchmark success or Coordinator release",
            "changed_axis": "Normalize focused node IDs to readable test paths for compact repair excerpts",
            "models_budgets_contract_feedback_inputs_equal": True,
            "max_calls": 2,
            "primary_semantic_guidance": False,
            "old_failed_rounds_retained": True,
            "primary_total_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    print(json.dumps({"registered": str(BASE), "changed_paths": changed}))


def run(arm):
    manifest = read(BASE / "manifest.json")
    if digest(Path(__file__)) != manifest["driver_sha256"]:
        raise ValueError("driver drift")
    cell = next(cell for cell in manifest["cells"] if cell["arm"] == arm)
    root, snapshot = Path(cell["root"]), Path(cell["runtime"])
    for path, sha in read(snapshot / "freeze.json")["files"].items():
        if digest(snapshot / path) != sha:
            raise ValueError("runtime snapshot drift")
    for path, sha in cell["inputs"].items():
        if digest(root / path) != sha:
            raise ValueError("inherited input drift: " + path)
    if digest(Path(cell["child"])) != cell["child_sha256"]:
        raise ValueError("child packet changed")
    write(BASE / f"{arm}-started.json", {"at": time.time()})
    started = time.monotonic()
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            str(snapshot / ".local-agents/local-unit.py"),
            "--packet",
            cell["child"],
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/node-prefetch-coder-a2.json"),
            "--review-report",
            str(root / ".agent/node-prefetch-reviewer-a2.json"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1200,
        check=False,
    )
    write(
        BASE / f"{arm}-invocation.json",
        {
            "exit": process.returncode,
            "seconds": time.monotonic() - started,
            "output": process.stdout + process.stderr,
            "primary_accepted": False,
        },
    )
    report = read(root / ".agent/node-prefetch-coder-a2.json")
    print(
        json.dumps(
            {
                "arm": arm,
                "status": report["status"],
                "validation": report["validation_summary"],
                "failure": report["failure_reason"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("arm", nargs="?", choices=("control", "candidate"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(args.arm)
