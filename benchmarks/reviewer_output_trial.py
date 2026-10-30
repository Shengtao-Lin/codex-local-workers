"""One bounded output-cap contrast; semantic inputs and whole-call limits fixed."""

import argparse
import json
import shutil
import time
from pathlib import Path

import reviewer_wire_trial as R

S, T = R.S, R.T
BATCH = R.BATCH.with_name("reviewer-output-6144-20261020-1")


def prepare():
    parent = S.read(R.BATCH / "registration.json")
    rows = []
    for old in parent["cells"]:
        root = BATCH / "cells" / old["id"] / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            if S.sha(source) != digest:
                raise ValueError("Parent input drift")
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        request = S.read(root / ".agent/experiment-request.json")
        request["review_id"] = "output6144-20261020-1-" + old["id"]
        (root / ".agent/experiment-request.json").write_text(
            json.dumps(request, indent=2), encoding="utf-8"
        )
        rows.append(
            {
                **old,
                "root": str(root),
                "identity": request,
                "files": {name: S.sha(root / name) for name in old["files"]},
            }
        )
    S.save(
        BATCH / "registration.json",
        {
            **parent,
            "cells": rows,
            "pins": {**parent["pins"], str(Path(__file__).resolve()): S.sha(__file__)},
            "candidate": "Only Reviewer output cap4096->6144 via existing --max-tokens CLI. Same model, medium/low wire control, native schema, semantic inputs and safety gates. Config/seals unchanged.",
            "budgets": {
                "requests": 16,
                "errors": 4,
                "seconds": 600,
                "output_tokens": 6144,
                "output_recoveries": 1,
                "request_timeout_seconds": 180,
            },
            "continue_rule": "Initial negative17/positive18 pair; complete ordinary failures in pair. Expand remaining18 only if both independently correct. Else HOLD with18 conditional NOT_RUN. HTTP/load/safety/40% stop. No additional cap search or resampling in this candidate.",
            "conditional": {
                "first": ["sample-17-candidate", "sample-18-candidate"],
                "requires": "both Primary causal/correct judgments",
            },
            "why": "Actual4k responses exhausted output entirely on reasoning with zero complete report despite medium then low. A single50% headroom increase tests truncation rather than weakening correctness. Local token/time cost recorded; whole-call600sec/16requests/4errors unchanged.",
            "same_version_evidence": str(R.BATCH / "offline-material-proof.json"),
        },
    )
    print("Output6144 candidate frozen offline; no model calls")


def run(cell, used, observed):
    if not (R.BATCH / "decision.json").exists():
        raise ValueError("Complete previous registered batch first")
    if not 0 <= used < 40 or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh usage required")
    registration = S.read(BATCH / "registration.json")
    if any(S.sha(path) != digest for path, digest in registration["pins"].items()):
        raise ValueError("Candidate drift")
    if cell not in registration["conditional"]["first"]:
        for required in registration["conditional"]["first"]:
            receipt = S.read(BATCH / "primary" / (required + ".json"))
            if receipt["correct"] is not True or receipt["report_sha256"] != S.sha(
                BATCH / "cells" / required / "reviewer.json"
            ):
                raise ValueError("Expansion not qualified")
    for previous in registration["order"][: registration["order"].index(cell)]:
        if S.read(BATCH / "results" / previous / "process.json")["stop_batch"]:
            raise ValueError("Previous infrastructure/safety stop")
    row = next(item for item in registration["cells"] if item["id"] == cell)
    root = Path(row["root"])
    if any(S.sha(root / name) != digest for name, digest in row["files"].items()):
        raise ValueError("Input drift")
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = 14400 - (time.time() - S.read(clock)["epoch"])
    if remaining <= 0:
        raise ValueError("Batch deadline reached")
    S.save(
        BATCH / "results" / cell / "start.json",
        {"weekly_used": used, "observed_at": observed},
    )
    start = time.monotonic()
    process = T.run(
        [
            S.PYTHON,
            "-B",
            S.KIT / "benchmarks/reviewer_contract_first.py",
            "--runtime-dir",
            root / ".local-agents",
            "--forward-reasoning-effort",
            "--max-tokens",
            "6144",
            "--request",
            root / ".agent/experiment-request.json",
            "--config",
            root / ".agent/experiment-config.json",
            "--report",
            root.parent / "reviewer.json",
        ],
        root,
        timeout=min(1200, remaining),
    )
    report = (
        S.read(root.parent / "reviewer.json")
        if (root.parent / "reviewer.json").exists()
        else {}
    )
    drift = [
        name for name, digest in row["files"].items() if S.sha(root / name) != digest
    ]
    infra = report.get("infra_failure") or {}
    process.update(
        seconds=time.monotonic() - start,
        decision=report.get("decision"),
        protected_drift=drift,
        stop_batch=bool(drift)
        or not report
        or bool(infra and infra.get("reason_code") != "output_token_limit"),
    )
    S.save(BATCH / "results" / cell / "process.json", process)
    print(
        cell,
        process["decision"],
        "expected",
        row["expected_decision"],
        round(process["seconds"], 2),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare"])
    parser.parse_args()
    prepare()
