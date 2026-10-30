"""Registered isolated Reviewer DTO candidate; original controls, no resampling."""

import argparse
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_r4_reviewer as OLD

B, R = OLD.B, OLD.R
BATCH = OLD.H.BATCH.parent / "r4-review-dto-20261016-1"
ADAPTER = B.KIT / "benchmarks/reviewer_compact_dto.py"


def baseline(used):
    assert 0 <= used < 30
    BATCH.mkdir(exist_ok=False)
    prior = B.read(OLD.H.BATCH / "live-freeze-approved.json")
    R.assert_files(B.KIT, prior["candidate_and_driver"])
    shutil.copytree(
        B.KIT / ".local-agents",
        BATCH / "runtime",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "config.json"),
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
            "files": {p: B.sha(B.KIT / p) for p in listed if (B.KIT / p).is_file()},
            "previous_stage": {
                p: B.sha(OLD.H.BATCH / p)
                for p in (
                    "decision.json",
                    "grid-results.json",
                    "preservation-final.json",
                    "reviewer-screen-v2/registration.json",
                    "reviewer-screen-v2/grid-results.json",
                )
            },
            "frozen_runtime": prior["candidate_and_driver"],
        },
    )
    B.save(
        BATCH / "design-registration.json",
        {
            "stage": "R4 independent Reviewer report DTO",
            "feature_id": "reviewer-report-dto-v1",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "owned_contract_ids": [
                "explicit-model-judgment",
                "source-binding",
                "truthful-check-provenance",
                "legacy-isolation",
                "immutable-history",
            ],
            "rationale": "A report authority boundary; only duplicate bookkeeping moves to the host, not semantic judgment or finding creation.",
            "authorization": "User approved the preceding overall-goal proposal and said to begin.",
            "axis": "Remove duplicate verified-contract/check arrays from model REPORT; type finding fields explicitly; retain assessment, findings, contract/order review and uncertainty.",
            "not_authorized_by_candidate": "No auto findings, no keyword judgments, no repaired verdict, no model/budget change, no product enablement or R4 transfer retry.",
            "same_sixteen_gate": "16/16 substantive correctness under original criteria, all calls retained; finish screen unless safety/usage stops it.",
            "old_transfer_hold_unchanged": True,
            "next_transfer_requires_new_unexposed_freeze": True,
            "weekly_used_start": used,
            "weekly_used_ceiling": 30,
            "preparation_clock_start": time.time(),
            "timing_caveat": "Clock starts after initial environment/design reads; phase wall time is not Primary active time.",
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    print("Baseline and design registration frozen; no model calls", flush=True)


def prepare():
    old = B.read(OLD.BATCH / "registration.json")
    cells = []
    for row in old["cells"]:
        source = Path(row["root"])
        R.assert_files(source, row["files"])
        root = BATCH / "cells" / row["id"] / "isolated"
        for relative in row["files"]:
            # Original immutable pre-live files only, never the later indexes/reports.
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
        config = B.read(root / ".agent/config.json")
        config["reviewer_compact_report"] = True
        request = {**row["identity"], "review_id": "dto-v1-" + row["id"]}
        B.save(root / ".agent/dto-config.json", config)
        B.save(root / ".agent/dto-request.json", request)
        module = R.load(root / ".local-agents/reviewer-runtime.py", "dto_" + row["id"])
        adapter = R.load(ADAPTER, "dto_adapter_" + row["id"])
        adapter.install(module)
        client = type("NoModel", (), {"native_tools": None})()
        runtime = module.ReviewerRuntime(root, request, config, client)
        assert runtime.max_turns == 16 and runtime.max_protocol_errors == 4
        runtime.initial_payload()
        cells.append(
            {
                "id": row["id"],
                "root": str(root),
                "identity": request,
                "expected_decision": row["expected_decision"],
                "files": {
                    p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)
                },
            }
        )
    B.save(
        BATCH / "registration.json",
        {
            "cells": cells,
            "registered": 16,
            "model": "meta/muse-glimmer",
            "source_registration_sha256": B.sha(OLD.BATCH / "registration.json"),
            "gate": "Original 16/16 substantive correctness; no verdict-label-only credit",
            "single_model_residency": True,
            "no_retry": True,
            "usage_ceiling": 30,
        },
    )
    print("Prepared sixteen original isolated controls; no model calls", flush=True)


def freeze():
    for name in ("dto-controls-final.xml", "legacy-regression.xml"):
        tree = ET.parse(BATCH / name)
        assert tree.findall(".//testcase")
        assert not tree.findall(".//failure") and not tree.findall(".//error")
        assert not tree.findall(".//skipped")
    B.save(
        BATCH / "live-freeze.json",
        {
            "adapter": B.sha(ADAPTER),
            "driver": B.sha(Path(__file__)),
            "registration": B.sha(BATCH / "registration.json"),
            "controls_source": B.sha(B.KIT / "tests/test_reviewer_compact_dto.py"),
            "runtime": {
                p.relative_to(BATCH / "runtime").as_posix(): B.sha(p)
                for p in B.files(BATCH / "runtime")
            },
            "preparation_phase_wall_seconds": time.time()
            - B.read(BATCH / "design-registration.json")["preparation_clock_start"],
            "primary_active_seconds": None,
        },
    )
    print("Live freeze approved", flush=True)


def run(name, used):
    assert 0 <= used < 30
    seal = B.read(BATCH / "live-freeze.json")
    assert B.sha(ADAPTER) == seal["adapter"]
    assert B.sha(Path(__file__)) == seal["driver"]
    assert B.sha(BATCH / "registration.json") == seal["registration"]
    R.assert_files(BATCH / "runtime", seal["runtime"])
    rows = B.read(BATCH / "registration.json")["cells"]
    row = next(item for item in rows if item["id"] == name)
    for prior in rows[: rows.index(row)]:
        assert (BATCH / "cells" / prior["id"] / "result.json").exists()
    root, cell = Path(row["root"]), Path(row["root"]).parent
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
        str(root / ".agent/dto-request.json"),
        "--config",
        str(root / ".agent/dto-config.json"),
        "--report",
        str(cell / "reviewer.json"),
    ]
    start = time.monotonic()
    process = subprocess.run(
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
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "seconds": time.monotonic() - start,
        },
    )
    report = B.read(cell / "reviewer.json")
    drift = [p for p, sha in row["files"].items() if B.sha(root / p) != sha]
    result = {
        "id": name,
        "observed": report.get("decision"),
        "expected": row["expected_decision"],
        "failure_reason": report.get("failure_reason"),
        "infra_failure": report.get("infra_failure"),
        "protected_drift": drift,
        "seconds": time.monotonic() - start,
        "primary_adjudication": "pending",
    }
    B.save(cell / "result.json", result)
    print(result, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["baseline", "prepare", "freeze", "run"])
    parser.add_argument("--used", type=int)
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "baseline":
        baseline(args.used)
    elif args.action == "prepare":
        prepare()
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
