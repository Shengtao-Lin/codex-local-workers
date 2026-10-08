"""One fresh inherited context per failed unit, without supplied semantic answers."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from capability_fit import WORK, load_worker, write

BASE = WORK / "roleq-inherited-context-2"
PARENT = WORK / "roleq-protocol-transfer-1"
SNAPSHOT = WORK / "roleq-prefetch-guard-candidate-1"
CASES = ("filename-suffix", "window-groups", "timeout-roundtrip")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    BASE.mkdir(exist_ok=False)
    worker = load_worker(SNAPSHOT)
    cells = []
    for case in CASES:
        root = PARENT / "runs/v1/canonical1" / f"{case}-round-1"
        parent = read(root / ".agent/qual-unit-reference.json")
        child = {k: parent[k] for k in ("schema_version", "task_id", "unit_id")}
        child.update(
            run_id=parent["run_id"].replace("-a1", "-a2"),
            parent_run_id=parent["run_id"],
            preserve_contract=True,
            attempt=2,
            packet_revision=2,
            plan_revision=1,
            review_feedback=[
                {
                    "text": "Use the inherited runtime failure traceback to repair the current draft. Preserve the complete original contract and protected tests; validate current inputs. No implementation or semantic answer is supplied by Primary.",
                    "verify_in_review": False,
                }
            ],
        )
        resolved = worker.resolve_inherited_packet(root, child)
        worker.validate_packet(resolved)
        if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
            raise ValueError("parent draft drift")
        path = root / ".agent/fresh-context-a2.json"
        write(path, child)
        cells.append(
            {
                "case": case,
                "root": str(root),
                "hashes": {
                    p.relative_to(root).as_posix(): digest(p)
                    for p in root.rglob("*.py")
                    if ".agent" not in p.parts
                },
                "child_sha256": digest(path),
                "config_sha256": digest(root / ".agent/config.json"),
            }
        )
    write(
        BASE / "manifest.json",
        {
            "cells": cells,
            "runtime": str(SNAPSHOT),
            "classification": "Unguided inherited recovery; not initial success and not new qualification",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Preserved authority and failure denominators; functional risk inherited unchanged",
            "contracts": [
                "parent-provenance",
                "unchanged-semantic-contract",
                "independent-acceptance",
            ],
            "difference": "Fresh call with current failed draft and canonical inherited traceback; no new semantic hints, implementation example or expanded scope. Current guarded-read runtime includes independent safety fix.",
            "max_calls": 3,
            "stop_per_unit": "One child only; no third call if failure",
            "weekly_used_ceiling": 40,
            "coordinator_started": False,
            "criterion": "Full protected validation, independent Reviewer and Primary; old parent failure never overwritten",
            "driver_sha256": digest(Path(__file__)),
        },
    )
    print(BASE)


def run(case):
    manifest = read(BASE / "manifest.json")
    if digest(Path(__file__)) != manifest["driver_sha256"]:
        raise ValueError("driver drift")
    for relative, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        if digest(SNAPSHOT / relative) != sha:
            raise ValueError("snapshot drift")
    cell = next(c for c in manifest["cells"] if c["case"] == case)
    root = Path(cell["root"])
    for relative, sha in {
        **cell["hashes"],
        ".agent/fresh-context-a2.json": cell["child_sha256"],
        ".agent/config.json": cell["config_sha256"],
    }.items():
        if digest(root / relative) != sha:
            raise ValueError("input drift: " + relative)
    write(BASE / f"{case}-started.json", {"started_at": time.time()})
    start = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/fresh-context-a2.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/fresh-context-coder-a2.json"),
            "--review-report",
            str(root / ".agent/fresh-context-reviewer-a2.json"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    record = {
        "exit": result.returncode,
        "seconds": time.monotonic() - start,
        "output": result.stdout + result.stderr,
        "primary_accepted": False,
    }
    write(BASE / f"{case}-result.json", record)
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--case", choices=CASES)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.case:
        run(args.case)
    else:
        parser.error("select prepare or case")
