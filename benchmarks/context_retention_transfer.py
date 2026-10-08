"""Bounded cross-family check of the accepted retention direction."""

import hashlib
import json
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, load_worker, write


def prepare():
    base = WORK / "roleq-retention-transfer-1"
    base.mkdir(exist_ok=False)
    source = WORK / "roleq-boundary-comparison-1/corpus.json"
    cases = json.loads(source.read_text(encoding="utf-8"))
    write(base / "corpus.json", cases)
    config = json.loads((KIT / ".local-agents/config.json").read_text(encoding="utf-8"))
    config.update(
        coder_context_retention="budgeted",
        reviewer_context_retention="budgeted",
        reviewer_context_recovery=False,
    )
    write(base / "candidate-config.json", config)
    MIXED.CORPUS, MIXED.WORK = base / "corpus.json", base / "runs"
    snapshot = WORK / "roleq-context-budget-candidate-1"
    worker = load_worker(snapshot)
    cells = []
    for repetition in (1, 2):
        for case in ("window-groups", "timeout-roundtrip"):
            result = MIXED.prepare(
                case, repetition, base / "candidate-config.json", "retention1"
            )
            root = Path(result["root"])
            packet_path = root / ".agent/qual-unit-reference.json"
            worker.validate_packet(json.loads(packet_path.read_text(encoding="utf-8")))
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
            "classification": "Known semantic-boundary development transfer; not new qualification or replacement of original failures",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Qualification evidence; immutable input provenance and no false capability credit",
            "contracts": [
                "independent-role-evidence",
                "qualification-before-coordinator",
            ],
            "cells": cells,
            "runtime_snapshot": str(snapshot),
            "explorer_cases": [],
            "candidate": "Budgeted retention for Coder and Reviewer; no extra prompts, examples or inherited rework",
            "runtime_other_changes": "Includes previously accepted same-input timeout rejection; compare as current candidate, not pure historical single-axis causal estimate",
            "criterion": "Full protected checks, independent Reviewer and Primary; failure on first repetition stops that family's second repetition",
            "calls_max": 4,
            "weekly_ceiling": 40,
            "coordinator_started": False,
            "models_sampling_context_limits_unchanged": True,
            "preflight": "Same frozen stronger subclass/False tests as roleq-boundary-comparison-1; prior reference/mutant preflight retained",
        },
    )
    print(str(base))


if __name__ == "__main__":
    prepare()
