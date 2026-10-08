"""Two one-shot development cases with guarded dynamic evidence, unchanged tests."""

import argparse
import json
import shutil
from pathlib import Path

import mixed_feature_benchmark as MIXED
import native_coder_comparison as RUN
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-execution-witness-1"
SNAPSHOT = WORK / "roleq-native-wire-candidate-1"
ADAPTER = KIT / "benchmarks/execution_witness_adapter.py"
PLUGIN = KIT / "benchmarks/execution_witness_plugin.py"
ORDER = ("window-groups", "timeout-roundtrip")


def prepare():
    BASE.mkdir(exist_ok=False)
    corpus = read(WORK / "roleq-native-coder-1/corpus.json")
    write(BASE / "corpus.json", corpus)
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    worker = load_worker(SNAPSHOT)
    cells = []
    for case in ORDER:
        root = Path(
            MIXED.prepare(case, 1, SNAPSHOT / ".local-agents/config.json", "ew1")[
                "root"
            ]
        )
        plugin_name = "_execution_witness.py"
        shutil.copyfile(PLUGIN, root / plugin_name)
        packet_path = root / ".agent/qual-unit-reference.json"
        packet = read(packet_path)
        packet["scope"]["read"].append(plugin_name)
        packet["scope"]["readonly"].append(plugin_name)
        worker.validate_packet(packet)
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
        config_path = root / ".agent/config.json"
        config = read(config_path)
        argv = config["validation_profiles"][packet["validation_profile"]][
            "pytest_argv"
        ]
        argv.extend(["-p", "_execution_witness"])
        for source in packet["scope"]["modify"]:
            argv.extend(["--witness-source", source])
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        files = next(c for c in corpus["cases"] if c["case_id"] == case)["files"]
        cells.append(
            {
                "label": case,
                "root": str(root),
                "arm": "native",
                "actual_protocol": "unchanged JSON-schema; native is the reused runner's adapter dispatch label only",
                "hashes": {
                    p: digest(root / p)
                    for p in [
                        *files,
                        plugin_name,
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
            "feature_id": "execution-witness-diagnostic",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Trusted pytest instrumentation may expose only bounded allowed-source facts; must preserve verdicts, signatures, scope and acceptance",
            "contracts": [
                "observations-not-fixes",
                "protected-tests-unchanged",
                "failure-identity-preserved",
                "no-automatic-acceptance",
            ],
            "classification": "Known development diagnostic, no unseen or guided semantic answer credit",
            "axis": "Actual bounded source execution events exposed via JUnit properties and repair observations; no inferred expected values, no prompt/algorithm hints",
            "fixed": "Model, current sampling, JSON action schema, context, limits, all protected test bytes and gate remain unchanged",
            "cells": cells,
            "order": ORDER,
            "coder_calls_max": 2,
            "retries": 0,
            "stop": "Exactly one call per cell, retain both. No production promotion from a known-case pass; independently review and transfer first.",
            "snapshot": str(SNAPSHOT),
            "coordinator_started": False,
            "weekly_used_ceiling": 60,
            "drivers": {
                str(p): digest(p)
                for p in [
                    Path(__file__),
                    ADAPTER,
                    PLUGIN,
                    Path(RUN.__file__),
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
        RUN.BASE, RUN.SNAPSHOT, RUN.ADAPTER = BASE, SNAPSHOT, ADAPTER
        RUN.run(args.action)
