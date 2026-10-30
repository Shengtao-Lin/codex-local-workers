"""Separate frozen mechanical repair batch; reuse immutable same-session controls."""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import harness_reviewer_semantic as OLD

B, R, E = OLD.B, OLD.R, OLD.E
BATCH = OLD.BATCH.parent / "r4-semantic-transport-20261017-1"
ADAPTER = B.KIT / "benchmarks/reviewer_semantic_transport.py"


def prepare(used):
    assert 0 <= used < 50
    OLD.audit()
    assert B.read(OLD.BATCH / "decision.json")["qualification"] == "HOLD"
    BATCH.mkdir(exist_ok=False)
    rows = []
    for previous in B.read(OLD.BATCH / "registration.json")["cells"]:
        if previous["arm"] != "candidate":
            continue
        name = previous["id"]
        root = BATCH / "cells" / name / "isolated"
        source = Path(previous["root"])
        R.assert_files(source, previous["files"])
        for path in previous["files"]:
            if path == ".agent/experiment-request.json":
                continue
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / path, dest)
        identity = {**previous["identity"], "review_id": "transport-v2-" + name}
        B.save(root / ".agent/experiment-request.json", identity)
        control = OLD.BATCH / "cells" / name.replace("candidate", "control")
        rows.append(
            {
                **previous,
                "root": str(root),
                "identity": identity,
                "origin": str(source),
                "origin_files": previous["files"],
                "files": {
                    p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)
                },
                "same_session_control": {
                    str(control / p): B.sha(control / p)
                    for p in ("result.json", "reviewer.json")
                },
            }
        )
    B.save(
        BATCH / "registration.json",
        {
            "feature_id": "semantic-disposition-mechanical-transport-v2",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "owned_contract_ids": [
                "unambiguous-citation-location",
                "truthful-absence-location",
                "explicit-blocked-disposition",
            ],
            "dependencies": [str(OLD.BATCH / "decision.json")],
            "axis": "Only locator normalization and confirmed-defect blocked-route aggregation. Original semantic prompt/schema/model/input/validation/budgets unchanged. Production runtime unchanged.",
            "criterion": "Fixed original sixteen 16/16 AND four exposed real regressions 4/4 substantive correctness; no worse than pinned same-session controls. No resampling or new candidate in this batch. No R4 or new Coder/holdout credit.",
            "control_caveat": "Same-session formal controls are reused and pinned, not a new randomized simultaneous control run.",
            "weekly_used_start": used,
            "usage_ceiling": 50,
            "registered": 20,
            "cells": rows,
            "failure_policy": "Complete ordinary quality failures; stop safety/input drift/transport/usage>=50. Keep raw output-cap results classified separately from service failure.",
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "offline-controls-combined.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + t) for t in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(OLD.BATCH / "live-freeze.json")["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        B.KIT / "tests/test_reviewer_semantic_transport.py",
                        OLD.BATCH / "decision.json",
                        OLD.BATCH / "primary-adjudications.json",
                        BATCH / "registration.json",
                        BATCH / "offline-controls.xml",
                    BATCH / "offline-controls-combined.xml",
                    )
                },
            }
        },
    )


def audit():
    OLD.audit()
    for p, sha in B.read(BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(p)) == sha, p


def run(name, used):
    assert 0 <= used < 50
    audit()
    rows = B.read(BATCH / "registration.json")["cells"]
    row = next(r for r in rows if r["id"] == name)
    for old in rows[: rows.index(row)]:
        result = B.read(BATCH / "cells" / old["id"] / "result.json")
        assert not result["protected_drift"]
        assert (
            not result["infra_failure"]
            or result["infra_failure"].get("reason_code") == "output_token_limit"
        )
    root, cell = Path(row["root"]), Path(row["root"]).parent
    R.assert_files(root, row["files"])
    R.assert_files(Path(row["origin"]), row["origin_files"])
    for path, sha in row["same_session_control"].items():
        assert B.sha(Path(path)) == sha
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
        text=True,
        capture_output=True,
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
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "argv": argv,
        },
    )
    report = B.read(cell / "reviewer.json")
    result = {
        "id": name,
        "case": row["case"],
        "arm": "candidate",
        "group": row["group"],
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
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
