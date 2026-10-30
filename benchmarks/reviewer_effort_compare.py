"""Matched configuration diagnosis: current implicit default vs phase forwarding."""

import argparse
import json
import shutil
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import reviewer_wire_trial as R

BATCH = S.KIT / "benchmarks/work/harness-convergence/reviewer-effort-compare-20261020-1"
ORDER = ["default-negative", "phase-negative", "phase-positive", "default-positive"]


def prepare():
    parent = S.read(R.BATCH / "registration.json")
    rows = []
    for cell in ORDER:
        source_id = (
            "sample-17-candidate"
            if cell.endswith("negative")
            else "sample-18-candidate"
        )
        old = next(r for r in parent["cells"] if r["id"] == source_id)
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            if S.sha(source) != digest:
                raise ValueError("Frozen Reviewer input drift")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        request_path = root / ".agent/experiment-request.json"
        request = S.read(request_path)
        request["review_id"] = BATCH.name + "-" + cell
        request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
        rows.append(
            {
                **old,
                "id": cell,
                "root": str(root),
                "identity": request,
                "files": {p: S.sha(root / p) for p in old["files"]},
            }
        )
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "cells": rows,
            "registered": 4,
            "pins": {**parent["pins"], str(Path(__file__).resolve()): S.sha(__file__)},
            "weekly_stop": 50,
            "batch_seconds": 7200,
            "A_default": "Existing client default None: no reasoning_effort parameter; unchanged prompts still mention medium/low. This is a measured baseline, not endorsement of implicit config.",
            "B_phase": "Same prompts/model/material and response cap, add existing --forward-reasoning-effort: medium normally, low on sole output-limit recovery.",
            "why": "Original r4-contract-first20/20 passed before explicit forwarding; recent forwarded controls repeatedly failed negative reporting. Need current matched evidence before attributing failures to model/context or adopting transport setting changes.",
            "gate": "Reviewer-only diagnostic; correct negative requires causal None guard defect and source quote, positive requires correct clean PASS. No new Coder/full-chain or product credit.",
            "budget": {
                "requests": 16,
                "errors": 4,
                "seconds": 600,
                "output_tokens": 4096,
                "output_recoveries": 1,
            },
            "continue_rule": "Complete4 ordinary semantic/output outcomes; infra/safety/input drift/deadline/weekly50 stop; no extra setting search or resampling in this batch.",
            "model": "Same Muse, single residency; no temperature/template/quantization changes. Effective default high established in earlier host prompt probe; current default is observed separately, not guessed from prompt text.",
        },
    )
    print("Four matched default/phase controls frozen, no new model calls")


def run(cell, used, observed):
    if not 0 <= used < 50 or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh weekly usage required")
    reg = S.read(BATCH / "registration.json")
    if any(S.sha(p) != h for p, h in reg["pins"].items()):
        raise ValueError("Candidate drift")
    for previous in ORDER[: ORDER.index(cell)]:
        if S.read(BATCH / "results" / previous / "process.json")["stop_batch"]:
            raise ValueError("Previous infrastructure/safety stop")
    row = next(r for r in reg["cells"] if r["id"] == cell)
    root = Path(row["root"])
    if any(S.sha(root / p) != h for p, h in row["files"].items()):
        raise ValueError("Input drift")
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = 7200 - (time.time() - S.read(clock)["epoch"])
    if remaining <= 0:
        raise ValueError("Batch deadline")
    S.save(
        BATCH / "results" / cell / "start.json",
        {"weekly_used": used, "observed_at": observed},
    )
    argv = [
        S.PYTHON,
        "-B",
        S.KIT / "benchmarks/reviewer_contract_first.py",
        "--runtime-dir",
        root / ".local-agents",
        "--request",
        root / ".agent/experiment-request.json",
        "--config",
        root / ".agent/experiment-config.json",
        "--report",
        root.parent / "reviewer.json",
    ]
    if cell.startswith("phase"):
        argv.append("--forward-reasoning-effort")
    started = time.monotonic()
    result = T.run(argv, root, timeout=min(1200, remaining))
    report = (
        S.read(root.parent / "reviewer.json")
        if (root.parent / "reviewer.json").exists()
        else {}
    )
    infra = report.get("infra_failure") or {}
    drift = [p for p, h in row["files"].items() if S.sha(root / p) != h]
    result.update(
        seconds=time.monotonic() - started,
        decision=report.get("decision"),
        protected_drift=drift,
        stop_batch=bool(drift)
        or not report
        or bool(infra and infra.get("reason_code") != "output_token_limit"),
    )
    S.save(BATCH / "results" / cell / "process.json", result)
    print(
        cell,
        result["decision"],
        "expected",
        row["expected_decision"],
        round(result["seconds"], 2),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare"])
    p.parse_args()
    prepare()
