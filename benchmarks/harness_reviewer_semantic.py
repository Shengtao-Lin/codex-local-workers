"""Matched-input formal control versus task-local semantic disposition experiment."""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import harness_r4_medium as PREVIOUS

B, R, E = PREVIOUS.B, PREVIOUS.R, PREVIOUS.E
BATCH = PREVIOUS.BATCH.parent / "r4-semantic-disposition-20261017-1"
ADAPTER = B.KIT / "benchmarks/reviewer_semantic_entry.py"
CONTROL = B.KIT / "benchmarks/reviewer_medium_entry.py"


def prepare(used):
    assert 0 <= used < 50
    E.prior_unchanged()
    BATCH.mkdir(exist_ok=False)
    old = B.read(PREVIOUS.BATCH / "registration.json")
    rows = []
    for index, origin in enumerate(old["cells"], 1):
        source = Path(origin["root"])
        R.assert_files(source, origin["files"])
        for arm in ("control", "candidate") if index % 2 else ("candidate", "control"):
            name = f"sample-{index:02}-{arm}"
            root = BATCH / "cells" / name / "isolated"
            for path in origin["files"]:
                if path == ".agent/experiment-request.json":
                    continue
                dest = root / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / path, dest)
            identity = {**origin["identity"], "review_id": "semantic-v1-" + name}
            B.save(root / ".agent/experiment-request.json", identity)
            rows.append(
                {
                    "id": name,
                    "arm": arm,
                    "case": origin["id"],
                    "group": origin["group"],
                    "root": str(root),
                    "origin": str(source),
                    "origin_files": origin["files"],
                    "identity": identity,
                    "expected_decision": origin["expected_decision"],
                    "files": {
                        p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)
                    },
                }
            )
    listed = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=B.KIT,
        text=True,
        encoding="utf-8",
    ).splitlines()
    B.save(
        BATCH / "baseline.json",
        {
            "head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=B.KIT, text=True
            ).strip(),
            "files": {p: B.sha(B.KIT / p) for p in listed if (B.KIT / p).is_file()},
            "previous_decisions": {
                str(p): B.sha(p) for p in PREVIOUS.BATCH.parent.glob("*/decision.json")
            },
        },
    )
    B.save(
        BATCH / "registration.json",
        {
            "feature_id": "task-local-semantic-disposition-v1",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "rationale": "Authority for semantic disposition and evidence provenance; hard gates retained.",
            "owned_contract_ids": [
                "explicit-semantic-disposition",
                "truthful-citations",
                "shared-budget",
                "immutable-history",
            ],
            "dependencies": [str(PREVIOUS.BATCH / "decision.json")],
            "authorization": "2026-10-17 user approved continuation of the proposed independent stage; ceiling raised to 50%.",
            "weekly_used_start": used,
            "usage_ceiling": 50,
            "registered": 40,
            "cells": rows,
            "intervention": "Task-local upfront source/tests/trusted dependency context, per-obligation semantic verdicts and deterministic report assembly. Joint workflow/input/output candidate, not single-factor causal attribution.",
            "control": "Frozen formal medium entry; exact matched source/contract/config/tests, counterbalanced within pairs.",
            "criterion": "Candidate original controls 16/16 AND exposed real regression 4/4 substantive correctness, and no worse than matched control in either group. No resampling. No R4 or Coder/holdout credit.",
            "budgets": "Same per-invocation 16 model turns / 4 protocol errors, 4096 per response / original whole-call deadline. Semantic and assembly share one budget; no second model or overall-assessment call.",
            "failure_policy": "Complete semantic/protocol/output-cap quality failures; stop transport, protected-input drift, safety, missing usage or weekly used >=50. No further candidate in this batch.",
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "production_promoted": False,
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "offline-controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + t) for t in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(PREVIOUS.BATCH / "live-freeze.json")["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        CONTROL,
                        B.KIT / "tests/test_reviewer_semantic_entry.py",
                        BATCH / "registration.json",
                        BATCH / "baseline.json",
                        BATCH / "offline-controls.xml",
                    )
                },
            }
        },
    )


def audit():
    E.prior_unchanged()
    for path, digest in B.read(BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(path)) == digest, path
    for path, digest in B.read(BATCH / "baseline.json")["previous_decisions"].items():
        assert B.sha(Path(path)) == digest, path


def run(name, used):
    assert 0 <= used < 50
    audit()
    rows = B.read(BATCH / "registration.json")["cells"]
    row = next(r for r in rows if r["id"] == name)
    for previous in rows[: rows.index(row)]:
        result = B.read(BATCH / "cells" / previous["id"] / "result.json")
        assert not result["protected_drift"]
        infra = result["infra_failure"]
        assert not infra or infra.get("reason_code") == "output_token_limit"
    root = Path(row["root"])
    R.assert_files(root, row["files"])
    R.assert_files(Path(row["origin"]), row["origin_files"])
    cell = root.parent
    B.save(
        cell / "started.json",
        {"weekly_used": used, "at": time.time(), "no_retry": True},
    )
    argv = [
        sys.executable,
        "-B",
        str(ADAPTER if row["arm"] == "candidate" else CONTROL),
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
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "argv": argv,
        },
    )
    if not (cell / "reviewer.json").is_file():
        raise RuntimeError(
            "No reviewer report; preserve entry-result and stop infrastructure audit"
        )
    report = B.read(cell / "reviewer.json")
    result = {
        "id": name,
        "case": row["case"],
        "arm": row["arm"],
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
