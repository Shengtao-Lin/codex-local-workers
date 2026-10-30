"""Two frozen failed-selection repairs under the unchanged product candidate."""

import argparse
import copy
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from capability_fit import WORK, write
from inherited_context_recovery import digest, read
from normal_unit_candidate_trial import verify_candidate
from supervised_scope_check import invoke

BASE = WORK / "frozen-limit-repair-1"
PRIOR = WORK / "limit-recovery-3/control-1"
SNAPSHOT = WORK / "transfer-candidate-runtime-1"
SOURCE = "src/evaluation_harness/datasets/selection.py"


def counts(path):
    cases = list(ET.parse(path).getroot().iter("testcase"))
    return {
        "tests": len(cases),
        **{
            k: sum(c.find(k) is not None for c in cases)
            for k in ("failure", "error", "skipped")
        },
    }


def verify():
    verify_candidate()
    for path, sha in read(WORK / "noop-primary-complete-1/freeze.json")[
        "files"
    ].items():
        assert digest(SNAPSHOT / path) == sha, path
    registration = read(BASE / "registration.json")
    assert digest(Path(__file__)) == registration["driver_sha256"]
    for path, sha in registration["historical_inputs"].items():
        assert digest(Path(path)) == sha, path
    return registration


def prepare():
    verify_candidate()
    BASE.mkdir(exist_ok=False)
    prior_packet = read(PRIOR / ".agent/packet.json")
    archive = (
        PRIOR
        / ".agent/tasks"
        / prior_packet["task_id"]
        / "runs"
        / prior_packet["run_id"]
    )
    preimage = read(archive / "preimages.json")[0]
    source = PRIOR / preimage["archive_path"]
    assert digest(source) == preimage["sha256"]
    prior_hashes = read(PRIOR / ".agent/manifest.json")["files"]
    assert prior_hashes[SOURCE] == preimage["sha256"]
    assert read(WORK / "limit-recovery-3/positive-preflight.json")["passed"]
    cells = []
    for repetition in (1, 2):
        root = BASE / f"repair-r{repetition}"
        for path, sha in prior_hashes.items():
            origin = source if path == SOURCE else PRIOR / path
            assert digest(origin) == sha, path
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origin, target)
        packet = copy.deepcopy(prior_packet)
        task = f"frozen-limit-repair-1-r{repetition}"
        packet.update(task_id=task, feature_id=task, run_id=task + "-a1")
        write(root / ".agent/packet.json", packet)
        config = read(WORK / "normal-unit-candidate-1/candidate/.agent/config.json")
        profile = copy.deepcopy(
            read(PRIOR / ".agent/config.json")["validation_profiles"]["project-strict"]
        )
        profile["pytest_argv"] = [
            a if not a.startswith("--basetemp=") else "--basetemp=.agent/test-temp"
            for a in profile["pytest_argv"]
        ]
        config["validation_profiles"]["project-strict"] = profile
        write(root / ".agent/config.json", config)
        shutil.copy2(PRIOR / ".agent/pyright.json", root / ".agent/pyright.json")
        cells.append(
            {
                "id": f"repair-r{repetition}",
                "root": str(root),
                "task_id": task,
                "unit_id": packet["unit_id"],
                "run_id": task + "-a1",
                "paths": prior_hashes,
                "packet_sha256": digest(root / ".agent/packet.json"),
                "config_sha256": digest(root / ".agent/config.json"),
                "pyright_sha256": digest(root / ".agent/pyright.json"),
            }
        )
    inputs = [
        PRIOR / ".agent/packet.json",
        PRIOR / ".agent/manifest.json",
        source,
        WORK / "limit-recovery-3/positive-preflight.json",
    ]
    write(
        BASE / "registration.json",
        {
            "cells": cells,
            "driver_sha256": digest(Path(__file__)),
            "historical_inputs": {str(p): digest(p) for p in inputs},
            "candidate": "noop-primary-complete-1",
            "weekly_start": 48,
            "weekly_ceiling": 60,
            "calls_per_cell": 1,
            "explorer_credit": False,
            "coordinator_enabled": False,
            "gate": "Both original focused/static checks, automatic Reviewer and independent full-fixture Primary acceptance must pass. No mid-batch changes, retries or Primary repair guidance. Any failure retained and prevents batch pass.",
            "classification": "Previously exposed real-module failed-draft recovery with existing advisory review_feedback; not blind or clean-start implementation.",
            "config_note": "Current normal-unit model/presentation/budget settings; unchanged historical project-strict checks and Pyright scope, only workspace temp path rebased.",
        },
    )
    shutil.copy2(Path(__file__), BASE / "registered-driver.py")
    verify()
    for cell in cells:
        root = Path(cell["root"])
        packet = read(root / ".agent/packet.json")
        result = invoke(
            root,
            "repair-before",
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                *packet["focused_tests"],
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml=.agent/repair-before.xml",
            ],
        )
        actual = counts(root / ".agent/repair-before.xml")
        assert actual == {"tests": 35, "failure": 8, "error": 0, "skipped": 0}, actual
        assert result["exit"] == 1
        print(cell["id"], "baseline", actual)


def run(cell):
    root = Path(cell["root"])
    assert not (root / ".agent/repair-live-invocation.json").exists()
    for path, sha in cell["paths"].items():
        assert digest(root / path) == sha, path
    for name in ("packet", "config", "pyright"):
        assert digest(root / f".agent/{name}.json") == cell[name + "_sha256"]
    result = invoke(
        root,
        "repair-live",
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
    print(
        cell["id"],
        result["exit"],
        round(result["seconds"], 3),
        result["output"][-4000:],
    )


def audit(cell):
    root = Path(cell["root"])
    archive = root / ".agent/tasks" / cell["task_id"] / "runs" / cell["run_id"]
    for path, sha in cell["paths"].items():
        if path != SOURCE:
            assert digest(root / path) == sha, path
    for name in ("packet", "config", "pyright"):
        assert digest(root / f".agent/{name}.json") == cell[name + "_sha256"]
    checks = []
    for name, argv in (
        (
            "tests",
            [
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml=.agent/primary-tests.xml",
            ],
        ),
        ("lint", ["-m", "ruff", "check", "src", "tests"]),
        ("format", ["-m", "ruff", "format", "--check", "src", "tests"]),
        (
            "types",
            [
                "-m",
                "pyright",
                "--project",
                ".agent/pyright.json",
                "--pythonpath",
                sys.executable,
            ],
        ),
    ):
        assert not (root / f".agent/primary-{name}-invocation.json").exists()
        result = invoke(root, "primary-" + name, [sys.executable, "-B", *argv])
        checks.append({"id": name, "exit": result["exit"]})
    compact = read(root / ".agent/coder.json")
    coder = read(archive / "handoff.json")
    reviewer_path = root / ".agent/reviewer.json"
    reviewer = read(reviewer_path) if reviewer_path.exists() else None
    attempts = [
        {
            "path": str(p.relative_to(root)),
            "sha256": digest(p),
            "attempt": read(p)["attempt"],
            "edit_revision": read(p)["edit_revision"],
            "status": read(p)["validation"]["status"],
        }
        for p in sorted(archive.glob("validation-attempt-*.json"))
    ]
    facts = {
        "coder_status": compact["status"],
        "failure_signature": coder.get("failure_signature"),
        "coder_protocol_errors": coder["protocol_error_count"],
        "reviewer_decision": reviewer["decision"] if reviewer else "not_started",
        "reviewer_protocol_errors": reviewer["runtime_facts"]["protocol_error_count"]
        if reviewer
        else None,
        "protected_unchanged": True,
        "checks": checks,
        "junit": counts(root / ".agent/primary-tests.xml"),
        "validation_attempts": attempts,
        "seconds": read(root / ".agent/repair-live-invocation.json")["seconds"],
        "source_sha256": digest(root / SOURCE),
        "primary_decision_pending": True,
    }
    assert not (root / ".agent/independent-audit.json").exists()
    write(root / ".agent/independent-audit.json", facts)
    print(json.dumps(facts, indent=2))


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
