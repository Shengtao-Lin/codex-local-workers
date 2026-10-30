"""Independent frozen observation candidate; immutable original sixteen controls."""

import argparse
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_r4_dto as D

B, R = D.B, D.R
BATCH = D.BATCH.parent / "r4-review-evidence-20261016-1"
ADAPTER = B.KIT / "benchmarks/reviewer_evidence_state.py"
TEST = B.KIT / "tests/test_reviewer_evidence_state.py"


def prior_unchanged():
    seal = B.read(D.BATCH / "live-freeze.json")
    assert B.sha(D.ADAPTER) == seal["adapter"]
    assert B.sha(B.KIT / "benchmarks/harness_r4_dto.py") == seal["driver"]
    assert B.sha(D.BATCH / "registration.json") == seal["registration"]
    R.assert_files(B.KIT, B.read(D.BATCH / "baseline.json")["frozen_runtime"])


def prepare(used):
    assert 0 <= used < 45
    prior_unchanged()
    BATCH.mkdir(exist_ok=False)
    listed = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=B.KIT,
        text=True,
        encoding="utf-8",
    ).splitlines()
    B.save(
        BATCH / "baseline.json",
        {
            "files": {p: B.sha(B.KIT / p) for p in listed if (B.KIT / p).is_file()},
            "old_decisions": {
                str(p): B.sha(p)
                for p in (
                    D.BATCH / "decision.json",
                    D.BATCH / "grid-results.json",
                    D.OLD.H.BATCH / "decision.json",
                )
            },
        },
    )
    B.save(
        BATCH / "design-registration.json",
        {
            "feature_id": "reviewer-evidence-state-v1",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "rationale": "Evidence provenance and read-readiness boundary; no semantic authority delegated to host",
            "owned_contract_ids": [
                "truthful-display-state",
                "source-version-binding",
                "unchanged-semantic-gates",
                "immutable-history",
            ],
            "axis": "Current observation facts: file line extent/EOF/unread count and current mandatory display state. No prompt or tool schema changes, no prefetch, no semantic default.",
            "dependencies": [str(D.BATCH / "decision.json")],
            "authorization": "User approved continuing the evidence-interface phase and raised weekly used ceiling to 45%",
            "weekly_used_start": used,
            "usage_ceiling": 45,
            "started": time.time(),
            "criterion": "Original sixteen substantive judgments all correct; complete ordinary failures, stop for safety/input drift/usage",
            "no_retry": True,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    rows = []
    for old in B.read(D.OLD.BATCH / "registration.json")["cells"]:
        root = BATCH / "cells" / old["id"] / "isolated"
        R.assert_files(Path(old["root"]), old["files"])
        for p in old["files"]:
            dest = root / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(old["root"]) / p, dest)
        config = B.read(root / ".agent/config.json")
        config.update(reviewer_compact_report=True, reviewer_evidence_state=True)
        identity = {**old["identity"], "review_id": "evidence-v1-" + old["id"]}
        B.save(root / ".agent/experiment-config.json", config)
        B.save(root / ".agent/experiment-request.json", identity)
        rows.append(
            {
                "id": old["id"],
                "root": str(root),
                "identity": identity,
                "expected_decision": old["expected_decision"],
                "files": {
                    p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)
                },
            }
        )
    B.save(
        BATCH / "registration.json",
        {
            "cells": rows,
            "registered": 16,
            "model": "meta/muse-glimmer",
            "usage_ceiling": 45,
            "gate": "16/16 original substantive correctness",
            "original_registration_sha256": B.sha(D.OLD.BATCH / "registration.json"),
        },
    )
    print("Prepared independent evidence candidate and unchanged sixteen controls")


def freeze():
    prior_unchanged()
    tree = ET.parse(BATCH / "offline-controls-combined.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                str(p): B.sha(p)
                for p in (
                    ADAPTER,
                    Path(__file__),
                    TEST,
                    D.ADAPTER,
                    BATCH / "registration.json",
                BATCH / "offline-controls-combined.xml",
                )
            }
        },
    )
    print("Frozen; offline controls passed")


def run(name, used):
    assert 0 <= used < 45
    prior_unchanged()
    for p, sha in B.read(BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(p)) == sha
    rows = B.read(BATCH / "registration.json")["cells"]
    row = next(r for r in rows if r["id"] == name)
    for before in rows[: rows.index(row)]:
        previous = B.read(BATCH / "cells" / before["id"] / "result.json")
        assert not previous["protected_drift"] and not previous["infra_failure"]
    root = Path(row["root"])
    cell = root.parent
    R.assert_files(root, row["files"])
    B.save(
        cell / "started.json",
        {"at": time.time(), "weekly_used": used, "no_retry": True},
    )
    argv = [
        sys.executable,
        "-B",
        str(ADAPTER),
        "--runtime-dir",
        str(root / ".local-agents"),
        "--request",
        str(root / ".agent/experiment-request.json"),
        "--config",
        str(root / ".agent/experiment-config.json"),
        "--report",
        str(cell / "reviewer.json"),
    ]
    start = time.monotonic()
    proc = subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(B.KIT / "benchmarks/r3_capture"),
            "R3_WIRE_DIR": str(cell / "wire"),
        },
    )
    B.save(
        cell / "entry-result.json",
        {
            "argv": argv,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "seconds": time.monotonic() - start,
        },
    )
    report = B.read(cell / "reviewer.json")
    result = {
        "id": name,
        "observed": report.get("decision"),
        "expected": row["expected_decision"],
        "failure_reason": report.get("failure_reason"),
        "infra_failure": report.get("infra_failure"),
        "protected_drift": [
            p for p, sha in row["files"].items() if B.sha(root / p) != sha
        ],
        "seconds": time.monotonic() - start,
        "primary_adjudication": "pending",
    }
    B.save(cell / "result.json", result)
    print(result, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "freeze", "run"])
    parser.add_argument("--used", type=int)
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
