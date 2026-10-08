"""Bounded transfer check for canonical action-envelope prompt alignment."""

import hashlib
import json
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import WORK, load_worker, write


def main():
    base = WORK / "roleq-protocol-transfer-1"
    snapshot = WORK / "roleq-protocol-prompt-candidate-1"
    base.mkdir(exist_ok=False)
    corpus = json.loads(
        (WORK / "roleq-boundary-comparison-1/corpus.json").read_text(encoding="utf-8")
    )
    write(base / "corpus.json", corpus)
    MIXED.CORPUS, MIXED.WORK = base / "corpus.json", base / "runs"
    worker = load_worker(snapshot)
    cells = []
    for repetition in (1, 2):
        for case in ("filename-suffix", "window-groups", "timeout-roundtrip"):
            root = Path(
                MIXED.prepare(
                    case,
                    repetition,
                    snapshot / ".local-agents/config.json",
                    "canonical1",
                )["root"]
            )
            packet_path = root / ".agent/qual-unit-reference.json"
            worker.validate_packet(json.loads(packet_path.read_text()))
            spec = next(c for c in corpus["cases"] if c["case_id"] == case)
            cells.append(
                {
                    "case": case,
                    "repetition": repetition,
                    "workspace": str(root),
                    "initial_hashes": {
                        p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                        for p in spec["files"]
                    },
                    "packet_sha256": hashlib.sha256(
                        packet_path.read_bytes()
                    ).hexdigest(),
                    "config_sha256": hashlib.sha256(
                        (root / ".agent/config.json").read_bytes()
                    ).hexdigest(),
                }
            )
    write(
        base / "manifest.json",
        {
            "classification": "Previously exposed development transfer, not unseen qualification",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Independent role credit and preserved qualification authority",
            "contracts": [
                "immutable-history",
                "canonical-action-envelope",
                "qualification-before-coordinator",
            ],
            "cells": cells,
            "runtime_snapshot": str(snapshot),
            "explorer_cases": [],
            "candidate": "System prompt examples now match action+arguments schema. Legacy flat parsing remains supported. Whitespace candidate remains default-off.",
            "fixed": "Same protected tests, original task goals, models, sampling, budgeted retention; no extra semantic hints or few-shot",
            "criterion": "All deterministic checks, independent Reviewer and Primary; score protocol errors separately from semantic outcomes",
            "stop": "First failed repetition closes that family; at most six Coder calls, no identical retry. Remaining families are independent diagnostics.",
            "coordinator_started": False,
            "weekly_ceiling": 40,
            "drivers": {
                Path(__file__).name: hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest()
            },
        },
    )
    print(base)


if __name__ == "__main__":
    main()
