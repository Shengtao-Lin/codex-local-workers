"""Two assisted legacy optimizations; only advisory algorithm guidance changes."""

import argparse
import copy
import shutil
import sys
import time
from pathlib import Path

import frozen_limit_repair_batch as execution
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from normal_unit_candidate_trial import verify_candidate
from supervised_scope_check import invoke

BASE = WORK / "limit-assisted-1"
TEMPLATE = WORK / "limit-startpoint-comparison-1/legacy-r1"
LEGACY = KIT / "benchmarks/fixtures/limit-recovery-v3"
STRATEGY = KIT / "docs/limit-assisted-strategy.md"


def verify():
    verify_candidate()
    registration = read(BASE / "registration.json")
    assert digest(Path(__file__)) == registration["driver_sha256"]
    assert digest(Path(execution.__file__)) == registration["auditor_sha256"]
    for path, sha in registration["inputs"].items():
        assert digest(Path(path)) == sha, path
    for path, sha in read(WORK / "noop-primary-complete-1/freeze.json")[
        "files"
    ].items():
        assert digest(execution.SNAPSHOT / path) == sha, path
    return registration


def prepare():
    started = time.monotonic()
    verify_candidate()
    BASE.mkdir(exist_ok=False)
    previous = next(
        c
        for c in read(WORK / "limit-startpoint-comparison-1/registration.json")["cells"]
        if c["id"] == "legacy-r1"
    )
    template = read(TEMPLATE / ".agent/packet.json")
    strategy = STRATEGY.read_text(encoding="utf-8")
    cells = []
    for repetition in (1, 2):
        task = f"limit-assisted-1-r{repetition}"
        root = BASE / f"assisted-r{repetition}"
        for path, sha in previous["paths"].items():
            origin = LEGACY / path if path == execution.SOURCE else TEMPLATE / path
            assert digest(origin) == sha, path
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origin, target)
        packet = copy.deepcopy(template)
        packet.update(
            task_id=task,
            feature_id=task,
            run_id=task + "-a1",
            implementation_guidance=[strategy],
        )
        for key in template:
            if key not in {
                "task_id",
                "feature_id",
                "run_id",
                "implementation_guidance",
            }:
                assert template[key] == packet[key], key
        write(root / ".agent/packet.json", packet)
        for name in ("config", "pyright"):
            shutil.copy2(TEMPLATE / f".agent/{name}.json", root / f".agent/{name}.json")
        cells.append(
            {
                "id": root.name,
                "root": str(root),
                "task_id": task,
                "run_id": task + "-a1",
                "unit_id": packet["unit_id"],
                "paths": previous["paths"],
                **{
                    name + "_sha256": digest(root / f".agent/{name}.json")
                    for name in ("packet", "config", "pyright")
                },
            }
        )
    inputs = [
        STRATEGY,
        TEMPLATE / ".agent/packet.json",
        TEMPLATE / ".agent/config.json",
        TEMPLATE / ".agent/pyright.json",
        LEGACY / execution.SOURCE,
    ]
    write(
        BASE / "registration.json",
        {
            "cells": cells,
            "driver_sha256": digest(Path(__file__)),
            "auditor_sha256": digest(Path(execution.__file__)),
            "inputs": {str(p): digest(p) for p in inputs},
            "candidate": "noop-primary-complete-1",
            "weekly_start": 48,
            "weekly_ceiling": 60,
            "calls_per_cell": 1,
            "coordinator_enabled": False,
            "explorer_credit": False,
            "difference_from_prior_legacy_workflow": "Only advisory implementation_guidance containing Primary-reviewed strategy; identity rebased. Same original source, hard contract, tests, risk, budgets and configuration.",
            "gate": "Both cells must pass unchanged validation/static checks, automatic Reviewer and independent Primary. No mid-batch edits, guidance, retries or preferred-patch comparison.",
            "credit": "Assisted implementation of exposed task, not autonomous algorithm design, unfamiliar-task success or overall release.",
            "primary_cost": {
                "strategy_review_window_start_utc": "2026-10-11T01:37:58+00:00",
                "strategy_review_window_end_utc": "2026-10-11T01:38:31+00:00",
                "strategy_review_window_seconds": 33,
                "window_note": "Observed wall interval for strategy review/write after initial environment/context inspection; not total active reasoning or all Primary cost.",
                "strategy_chars": len(strategy),
                "strategy_utf8_bytes": len(strategy.encode("utf-8")),
                "strategy_words_whitespace_split": len(strategy.split()),
                "cloud_tokens": None,
                "primary_active_seconds": None,
                "direct_primary_comparator": "Not measured; no cost reduction claim",
            },
        },
    )
    shutil.copy2(Path(__file__), BASE / "registered-driver.py")
    verify()
    for cell in cells:
        root = Path(cell["root"])
        packet = read(root / ".agent/packet.json")
        result = invoke(
            root,
            "assisted-before",
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                *packet["focused_tests"],
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml=.agent/assisted-before.xml",
            ],
        )
        facts = execution.counts(root / ".agent/assisted-before.xml")
        assert result["exit"] == 1 and facts == {
            "tests": 35,
            "failure": 2,
            "error": 0,
            "skipped": 0,
        }, facts
        print(cell["id"], "baseline", facts)
    write(
        BASE / "preparation-cost.json",
        {
            "script_wall_seconds": time.monotonic() - started,
            "note": "File/hash/packet setup and two baseline commands only; excludes runner development, strategy review and active Primary work.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "audit"))
    parser.add_argument("--cell")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        cell = next(c for c in verify()["cells"] if c["id"] == args.cell)
        getattr(execution, args.action)(cell)
