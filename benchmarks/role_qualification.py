"""Create-only frozen qualification preparation; no automatic acceptance."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import capability_fit as FIT
import mixed_feature_benchmark as MIXED
from role_qualification_cases import corpus


def prepare():
    root = FIT.WORK / "roleq-six-1"
    root.mkdir(exist_ok=False)
    template = json.loads(
        (FIT.KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(
            encoding="utf-8"
        )
    )["cases"][0]
    cases, oracles = corpus(template)
    FIT.write(root / "corpus.json", cases)
    FIT.write(root / "primary-only-oracles.json", oracles)
    MIXED.CORPUS = root / "corpus.json"
    MIXED.WORK = root / "runs"
    prepared = []
    for repetition in (1, 2):
        for case in cases["cases"]:
            cell = MIXED.prepare(
                case["case_id"],
                repetition,
                FIT.KIT / ".local-agents/config.json",
                "roleq1",
            )
            workspace = Path(cell["root"])
            prepared.append(
                {
                    "case": case["case_id"],
                    "repetition": repetition,
                    "workspace": str(workspace),
                    "initial_hashes": {
                        p: hashlib.sha256((workspace / p).read_bytes()).hexdigest()
                        for p in case["files"]
                    },
                }
            )
    paths = [
        FIT.KIT / "benchmarks/role_qualification_cases.py",
        Path(__file__),
        FIT.KIT / "benchmarks/mixed_feature_benchmark.py",
        FIT.KIT / "docs/supervised-role-qualification.md",
    ]
    paths += [p for p in (FIT.KIT / ".local-agents").glob("*") if p.is_file()]
    FIT.write(
        root / "manifest.json",
        {
            "state": "preregistered_not_executed",
            "runtime_snapshot": FIT.freeze("roleq-six-runtime-1"),
            "input_hashes": {
                str(p.relative_to(FIT.KIT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in paths
            },
            "corpus_sha256": hashlib.sha256(
                (root / "corpus.json").read_bytes()
            ).hexdigest(),
            "cells": prepared,
            "criterion": "Every declared cell passes protected tests/static checks, independent Reviewer and risk-routed Primary; no guided recovery counted",
            "scope": "new narrow supervised tasks, not general semantic qualification",
            "coordinator_enabled": False,
            "single_model_residency": True,
            "weekly_used_start": 23,
            "weekly_used_ceiling": 40,
            "explorer_cases": ["timeout-roundtrip", "case-preserving-query"],
            "explorer_question": "Locate the public input/output transformation and its helper, with a protected boundary assertion; cite actual read files/lines",
            "reviewer_challenges": "separate hidden/clean two-family eight-call cohort required before phase 2",
            "integration_gap": "Cross-file cohesive cases provided; accepted dependent multi-unit chain still required separately before phase 2",
            "cloud_tokens": None,
            "primary_active_time": None,
            "python": sys.executable,
            "stop": "failure decision or weekly used >=40; preserve all outcomes; no mid-cohort runtime tuning",
        },
    )
    print(root)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare()
