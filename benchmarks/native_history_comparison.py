"""Two one-shot known-case probes of paired native tool history; no promotion."""

import argparse
from pathlib import Path

import mixed_feature_benchmark as MIXED
import native_coder_comparison as V1
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-native-history-1"
SNAPSHOT = V1.SNAPSHOT
ADAPTER = KIT / "benchmarks/native_history_adapter.py"
ORDER = ("window-groups-native", "timeout-roundtrip-native")


def prepare():
    BASE.mkdir(exist_ok=False)
    corpus = read(V1.BASE / "corpus.json")
    write(BASE / "corpus.json", corpus)
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    worker = load_worker(SNAPSHOT)
    cells = []
    for label in ORDER:
        case = label.rsplit("-", 1)[0]
        root = Path(
            MIXED.prepare(case, 1, SNAPSHOT / ".local-agents/config.json", "nh2")[
                "root"
            ]
        )
        worker.validate_packet(read(root / ".agent/qual-unit-reference.json"))
        files = next(c for c in corpus["cases"] if c["case_id"] == case)["files"]
        cells.append(
            {
                "label": label,
                "root": str(root),
                "arm": "native",
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
            "feature_id": "native-history-roundtrip",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "contracts": [
                "scope-and-gates-unchanged",
                "evidence-preserved",
                "no-automatic-acceptance",
            ],
            "risk_rationale": "Transport serialization must not change runtime authority or invent tool outcomes",
            "classification": "Known development cases, historical v1 comparison only; not unseen qualification or randomized causal evidence",
            "axis": "Paired native tool history plus accounting for schema budget; same typed schema/header/model/runtime as native v1",
            "cells": cells,
            "order": ORDER,
            "coder_calls_max": 2,
            "retries": 0,
            "stop": "One call per cell; retain both outcomes. No production promotion from compatibility alone.",
            "snapshot": str(SNAPSHOT),
            "weekly_used_ceiling": 60,
            "coordinator_started": False,
            "drivers": {
                str(p): digest(p)
                for p in [
                    Path(__file__),
                    ADAPTER,
                    KIT / "benchmarks/native_coder_adapter.py",
                    Path(V1.__file__),
                    Path(MIXED.__file__),
                ]
            },
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", *ORDER))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        V1.BASE, V1.ADAPTER = BASE, ADAPTER
        V1.run(args.action)
