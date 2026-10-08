"""Bounded atomic-contract ledger screen; same cohesive units and semantics."""

import argparse
import json
from pathlib import Path

import mixed_feature_benchmark as MIXED
import native_coder_comparison as RUN
from atomic_acceptance_cases import apply_ledger
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-atomic-contract-1"
SNAPSHOT = WORK / "roleq-native-wire-candidate-1"
ORDER = ("window-r1", "timeout-r1", "timeout-r2", "window-r2")


def prepare():
    BASE.mkdir(exist_ok=False)
    corpus = read(WORK / "roleq-native-coder-1/corpus.json")
    write(BASE / "corpus.json", corpus)
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    worker = load_worker(SNAPSHOT)
    cells = []
    for label in ORDER:
        prefix, round_name = label.split("-")
        case = "window-groups" if prefix == "window" else "timeout-roundtrip"
        root = Path(
            MIXED.prepare(
                case, int(round_name[1:]), SNAPSHOT / ".local-agents/config.json", "ac1"
            )["root"]
        )
        packet = read(root / ".agent/qual-unit-reference.json")
        packet = apply_ledger(packet, case)
        worker.validate_packet(packet)
        (root / ".agent/qual-unit-reference.json").write_text(
            json.dumps(packet, indent=2) + "\n", encoding="utf-8"
        )
        files = next(c for c in corpus["cases"] if c["case_id"] == case)["files"]
        cells.append(
            {
                "label": label,
                "root": str(root),
                "arm": "envelope",
                "hashes": {
                    p: digest(root / p)
                    for p in [
                        *files,
                        "pyproject.toml",
                        ".agent/config.json",
                        ".agent/qual-unit-reference.json",
                    ]
                },
            }
        )
    write(
        BASE / "manifest.json",
        {
            "feature_id": "atomic-contract-ledger",
            "feature_risk": "medium",
            "unit_risk": "medium",
            "integration_risk": "high",
            "risk_rationale": "Contract projection must retain every original invariant, unit boundary, risk and immutable protected test; no preferred code or repair answer",
            "contracts": [
                "protected-contract-unchanged",
                "bounded-no-selection",
                "no-automatic-acceptance",
            ],
            "axis": "Replace one conjunctive behavior ID and generic scenarios with five atomic behavior IDs and concrete observable scenarios. Same goal, tests, unit, scope, model, sampling and runtime; explicit plan/contract representation change, not a new semantic capability claim.",
            "classification": "Known development screen with historical JSON controls, no unseen credit or causal parameter attribution",
            "snapshot": str(SNAPSHOT),
            "cells": cells,
            "order": ORDER,
            "coder_calls_max": 4,
            "retries": 0,
            "stop": "Run both r1 cells once. If either fails, do not run r2; do not select best samples. Only if both accepted may r2 proceed.",
            "coordinator_started": False,
            "weekly_used_ceiling": 60,
            "drivers": {
                str(p): digest(p)
                for p in [
                    Path(__file__),
                    Path(RUN.__file__),
                    Path(MIXED.__file__),
                    KIT / "benchmarks/native_coder_adapter.py",
                    KIT / "benchmarks/atomic_acceptance_cases.py",
                ]
            },
        },
    )


def run(label):
    if label.endswith("r2"):
        for first in ORDER[:2]:
            cell = next(
                c for c in read(BASE / "manifest.json")["cells"] if c["label"] == first
            )
            root = Path(cell["root"])
            report = read(root / ".agent/coder.json")
            decision = read(
                root / report["evidence_refs"]["run_archive"] / "review.json"
            )
            if decision.get("decision") != "accept":
                raise ValueError(
                    "replication requires both first-round Primary accepts"
                )
    RUN.BASE, RUN.SNAPSHOT = BASE, SNAPSHOT
    RUN.run(label)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", *ORDER))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(args.action)
