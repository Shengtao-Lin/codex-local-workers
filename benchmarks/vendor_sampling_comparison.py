"""Bounded complete vendor-sampler screen; same model and protected contracts."""

import argparse
import json
from pathlib import Path

import mixed_feature_benchmark as MIXED
import native_coder_comparison as RUN
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-vendor-sampling-1"
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
                case, int(round_name[1:]), SNAPSHOT / ".local-agents/config.json", "vs1"
            )["root"]
        )
        packet = read(root / ".agent/qual-unit-reference.json")
        worker.validate_packet(packet)
        config_path = root / ".agent/config.json"
        config = read(config_path)
        config.update(
            coder_temperature=0.7,
            coder_top_p=0.8,
            coder_top_k=20,
            coder_repeat_penalty=1.05,
        )
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
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
            "feature_id": "vendor-sampler-control",
            "feature_risk": "medium",
            "unit_risk": "medium",
            "integration_risk": "high",
            "risk_rationale": "Isolated decoding-profile change, no authority or acceptance changes; generality requires independent transfer",
            "contracts": [
                "protected-contract-unchanged",
                "bounded-no-selection",
                "no-automatic-acceptance",
            ],
            "axis": "Complete publisher-recommended sampler, not temperature-only. Retain 4096 output limit because this is one bounded action, not long whole-task generation; no claim of full publisher inference recipe.",
            "source": "https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct#best-practices",
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
