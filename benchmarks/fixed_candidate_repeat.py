"""Registered four-cell repeat batch; no retries or candidate changes."""

import argparse
import shutil
import sys
from pathlib import Path

from capability_fit import WORK, write
from inherited_context_recovery import digest, read
from normal_unit_candidate_trial import verify_candidate
from supervised_scope_check import invoke

BASE = WORK / "fixed-candidate-repeat-1"
SNAPSHOT = WORK / "transfer-candidate-runtime-1"


def verify():
    verify_candidate()
    for path, sha in read(WORK / "noop-primary-complete-1/freeze.json")[
        "files"
    ].items():
        assert digest(SNAPSHOT / path) == sha, path
    manifest = read(BASE / "registration.json")
    assert digest(Path(__file__)) == manifest["driver_sha256"]
    return manifest


def prepare():
    verify_candidate()
    BASE.mkdir(exist_ok=False)
    cells = []
    for repetition in (1, 2):
        for kind in ("timestamp", "async"):
            prior_base = WORK / (
                "normal-unit-candidate-1"
                if kind == "timestamp"
                else "transfer-candidate-1"
            )
            prior_registration = read(prior_base / "registration.json")
            prior_root = Path(prior_registration["root"])
            packet_name = (
                "packet.json" if kind == "timestamp" else "qual-unit-reference.json"
            )
            packet = read(prior_root / ".agent" / packet_name)
            prior_run = (
                prior_root
                / ".agent/tasks"
                / packet["task_id"]
                / "runs"
                / packet["run_id"]
            )
            hashes = prior_registration.get(
                "paths", prior_registration.get("frozen_initial_hashes")
            )
            cell_id = f"{kind}-r{repetition}"
            root = BASE / cell_id
            preimages = {p["path"]: p for p in read(prior_run / "preimages.json")}
            for path, sha in hashes.items():
                if path.startswith(".agent/"):
                    continue
                source = (
                    prior_root / preimages[path]["archive_path"]
                    if path in preimages
                    else prior_root / path
                )
                assert digest(source) == sha, path
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            task = "fixed-repeat-1-" + cell_id
            packet.update(task_id=task, feature_id=task, run_id=task + "-a1")
            write(root / ".agent/packet.json", packet)
            shutil.copy2(prior_root / ".agent/config.json", root / ".agent/config.json")
            cells.append(
                {
                    "id": cell_id,
                    "root": str(root),
                    "task_id": task,
                    "run_id": task + "-a1",
                    "unit_id": packet["unit_id"],
                    "source": packet["scope"]["modify"][0],
                    "paths": {
                        p: sha
                        for p, sha in hashes.items()
                        if not p.startswith(".agent/")
                    },
                    "packet_sha256": digest(root / ".agent/packet.json"),
                    "config_sha256": digest(root / ".agent/config.json"),
                    "expected_tests": 21 if kind == "timestamp" else 2,
                }
            )
    write(
        BASE / "registration.json",
        {
            "cells": cells,
            "driver_sha256": digest(Path(__file__)),
            "calls_per_cell": 1,
            "weekly_used_start": 48,
            "weekly_used_ceiling": 50,
            "gate": "All four original validation + automatic Reviewer + independent Primary gates pass; any failure retained, no retry or mid-batch change. Not formal semantic release.",
        },
    )
    shutil.copy2(Path(__file__), BASE / "registered-driver.py")
    verify()
    print("Registered four clean cells")


def run(cell):
    root = Path(cell["root"])
    assert not (root / ".agent/repeat-live-invocation.json").exists()
    for path, sha in cell["paths"].items():
        assert digest(root / path) == sha, path
    result = invoke(
        root,
        "repeat-live",
        [
            sys.executable,
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/packet.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/coder.json"),
            "--review-report",
            str(root / ".agent/reviewer.json"),
        ],
    )
    print(cell["id"], result["exit"], result["seconds"], result["output"][-3500:])


def audit(cell):
    root = Path(cell["root"])
    assert digest(root / ".agent/packet.json") == cell["packet_sha256"]
    assert digest(root / ".agent/config.json") == cell["config_sha256"]
    for path, sha in cell["paths"].items():
        if path != cell["source"]:
            assert digest(root / path) == sha, path
    coder = read(root / ".agent/coder.json")
    reviewer = read(root / ".agent/reviewer.json")
    assert coder["status"] == "ready_for_review"
    assert reviewer["decision"] == "pass_to_primary"
    assert coder["validation_summary"]["executed"] == cell["expected_tests"]
    assert coder["validation_summary"]["inputs_unchanged"]
    assert reviewer["runtime_facts"]["inputs_unchanged"]
    checks = [
        ("tests", ["-m", "pytest", "-q", "--junitxml=.agent/primary-repeat.xml"]),
        ("lint", ["-m", "ruff", "check", "src", "tests"]),
        ("format", ["-m", "ruff", "format", "--check", "src", "tests"]),
    ]
    if cell["id"].startswith("timestamp"):
        checks.append(
            ("types", ["-m", "pyright", "--pythonpath", sys.executable, "src"])
        )
    for name, argv in checks:
        result = invoke(root, "primary-" + name, [sys.executable, "-B", *argv])
        assert result["exit"] == 0, result
    write(
        root / ".agent/repeat-audit.json",
        {
            "protected_unchanged": True,
            "tests": cell["expected_tests"],
            "reviewer_decision": reviewer["decision"],
            "coder_protocol_errors": coder["protocol_error_count"],
            "reviewer_protocol_errors": reviewer["runtime_facts"][
                "protocol_error_count"
            ],
            "primary_acceptance_pending": True,
        },
    )
    print(cell["id"], "independent checks passed; Primary diff review pending")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "audit"))
    parser.add_argument("--cell")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        selected = next(c for c in verify()["cells"] if c["id"] == args.cell)
        globals()[args.action](selected)
