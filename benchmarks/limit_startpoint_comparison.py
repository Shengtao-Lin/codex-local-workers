"""Prospective draft-repair versus legacy-optimization workflow comparison."""

import argparse
import copy
import shutil
import sys
from pathlib import Path

import frozen_limit_repair_batch as prior
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from normal_unit_candidate_trial import verify_candidate
from supervised_scope_check import invoke

BASE = WORK / "limit-startpoint-comparison-1"
LEGACY = KIT / "benchmarks/fixtures/limit-recovery-v3"
SOURCE = prior.SOURCE
TEMPLATE = WORK / "frozen-limit-repair-1/repair-r1"


def verify():
    verify_candidate()
    for path, sha in read(WORK / "noop-primary-complete-1/freeze.json")[
        "files"
    ].items():
        assert digest(prior.SNAPSHOT / path) == sha, path
    registration = read(BASE / "registration.json")
    assert digest(Path(__file__)) == registration["driver_sha256"]
    for path, sha in registration["inputs"].items():
        assert digest(Path(path)) == sha, path
    return registration


def prepare():
    verify_candidate()
    BASE.mkdir(exist_ok=False)
    previous = read(WORK / "frozen-limit-repair-1/registration.json")["cells"][0]
    template_packet = read(TEMPLATE / ".agent/packet.json")
    old_packet = read(prior.PRIOR / ".agent/packet.json")
    archive = (
        prior.PRIOR
        / ".agent/tasks"
        / old_packet["task_id"]
        / "runs"
        / old_packet["run_id"]
    )
    preimage = read(archive / "preimages.json")[0]
    draft_source = prior.PRIOR / preimage["archive_path"]
    legacy_source = LEGACY / SOURCE
    assert digest(draft_source) == preimage["sha256"]
    assert digest(legacy_source) == read(LEGACY / "provenance.json")["files"][SOURCE]
    cells = []
    for repetition in (1, 2):
        for arm in ("draft", "legacy"):
            identity = f"limit-startpoint-1-{arm}-r{repetition}"
            root = BASE / f"{arm}-r{repetition}"
            hashes = previous["paths"].copy()
            hashes[SOURCE] = digest(draft_source if arm == "draft" else legacy_source)
            for path, sha in hashes.items():
                origin = (
                    (draft_source if arm == "draft" else legacy_source)
                    if path == SOURCE
                    else TEMPLATE / path
                )
                assert digest(origin) == sha, path
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origin, target)
            packet = copy.deepcopy(template_packet)
            packet.update(
                task_id=identity, feature_id=identity, run_id=identity + "-a1"
            )
            if arm == "legacy":
                packet["review_feedback"] = []
            # Every field except identity and historical feedback stays exact.
            for key in template_packet:
                if key not in {"task_id", "feature_id", "run_id", "review_feedback"}:
                    assert packet[key] == template_packet[key], key
            write(root / ".agent/packet.json", packet)
            for name in ("config", "pyright"):
                shutil.copy2(
                    TEMPLATE / f".agent/{name}.json", root / f".agent/{name}.json"
                )
            cells.append(
                {
                    "id": root.name,
                    "arm": arm,
                    "root": str(root),
                    "task_id": identity,
                    "run_id": identity + "-a1",
                    "unit_id": packet["unit_id"],
                    "paths": hashes,
                    **{
                        name + "_sha256": digest(root / f".agent/{name}.json")
                        for name in ("packet", "config", "pyright")
                    },
                    "historical_feedback_ids": [
                        item["finding_id"] for item in packet["review_feedback"]
                    ],
                }
            )
    inputs = [
        draft_source,
        legacy_source,
        TEMPLATE / ".agent/packet.json",
        TEMPLATE / ".agent/config.json",
        TEMPLATE / ".agent/pyright.json",
    ]
    write(
        BASE / "registration.json",
        {
            "cells": cells,
            "driver_sha256": digest(Path(__file__)),
            "inputs": {str(p): digest(p) for p in inputs},
            "shared_auditor_sha256": digest(Path(prior.__file__)),
            "calls_per_cell": 1,
            "weekly_used_start": 48,
            "weekly_used_ceiling": 60,
            "candidate": "noop-primary-complete-1",
            "coordinator_enabled": False,
            "explorer_credit": False,
            "gate": "Each workflow qualifies only if both new cells satisfy unchanged hard contracts/protected tests, original configured checks, automatic Reviewer and independent Primary acceptance. No retries or mid-batch changes.",
            "differences": {
                "draft": "Exact historical failed preimage and both original draft-bound review_feedback items",
                "legacy": "Correct original full-sort legacy semantics, lacking required optimization; no old draft repair_feedback",
            },
            "causal_limit": "Two workflow factors differ together: initial source and historical feedback. Not a source-only causal experiment. No fresh/unknown-task credit.",
        },
    )
    shutil.copy2(Path(__file__), BASE / "registered-driver.py")
    verify()
    for cell in cells:
        root = Path(cell["root"])
        packet = read(root / ".agent/packet.json")
        result = invoke(
            root,
            "startpoint-before",
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                *packet["focused_tests"],
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml=.agent/startpoint-before.xml",
            ],
        )
        facts = prior.counts(root / ".agent/startpoint-before.xml")
        assert facts == {
            "tests": 35,
            "failure": 8 if cell["arm"] == "draft" else 2,
            "error": 0,
            "skipped": 0,
        }, facts
        assert result["exit"] == 1
        print(cell["id"], "preflight", facts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "audit"))
    parser.add_argument("--cell")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        registration = verify()
        assert digest(Path(prior.__file__)) == registration["shared_auditor_sha256"]
        cell = next(c for c in registration["cells"] if c["id"] == args.cell)
        getattr(prior, args.action)(cell)
