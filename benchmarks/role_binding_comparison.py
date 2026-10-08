"""Freeze known-case development comparison for actual parameter evidence only."""

import hashlib
import json
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, write


def prepare():
    base = WORK / "roleq-binding-comparison-1"
    base.mkdir(exist_ok=False)
    original = WORK / "roleq-six-1"
    MIXED.CORPUS = original / "corpus.json"
    MIXED.WORK = base / "runs"
    cases = json.loads(MIXED.CORPUS.read_text(encoding="utf-8"))
    cells = []
    for repetition in (1, 2):
        for case in ("window-groups", "timeout-roundtrip"):
            prepared = MIXED.prepare(
                case, repetition, KIT / ".local-agents/config.json", "bindings1"
            )
            root = Path(prepared["root"])
            spec = next(c for c in cases["cases"] if c["case_id"] == case)
            cells.append(
                {
                    "case": case,
                    "repetition": repetition,
                    "workspace": str(root),
                    "initial_hashes": {
                        p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                        for p in spec["files"]
                    },
                }
            )
    write(
        base / "manifest.json",
        {
            "classification": "Known developer cases; not unseen qualification or original score replacement",
            "cells": cells,
            "runtime_snapshot": str(WORK / "roleq-bindings-1"),
            "explorer_cases": [],
            "axis": "Only bounded JUnit displayed_bindings extraction/repair evidence propagation",
            "control": "Existing window-groups and timeout-roundtrip two-round initial results: 0/4; same frozen fixture/config/protected tests",
            "candidate_calls_max": 4,
            "unchanged": [
                "models",
                "sampling",
                "context",
                "budgets",
                "prompts",
                "packet contract",
                "protected tests",
            ],
            "outcome": "Actual repair/full validation/fresh Reviewer and Primary, no diagnostic success implies semantic acceptance",
            "criterion": "Repeated completion improvement warrants further qualification only; no overall Coordinator entry",
            "weekly_ceiling": 40,
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "run_driver_sha256": hashlib.sha256(
                (KIT / "benchmarks/role_qualification_run.py").read_bytes()
            ).hexdigest(),
        },
    )
    print(base)


if __name__ == "__main__":
    prepare()
