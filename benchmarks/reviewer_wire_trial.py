"""Same twenty frozen review controls with explicit phase reasoning on the wire."""

import argparse
import json
import shutil
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import reasoning_wire_candidate as W
import reviewer_contract_first as CORE

OLD = S.KIT / "benchmarks/work/harness-convergence/r4-contract-first-20261017-1"
BATCH = S.KIT / "benchmarks/work/harness-convergence/reviewer-wire-20261020-2"


def prepare():
    rows, proofs, patches = [], [], []
    for old in S.read(OLD / "registration.json")["cells"]:
        root = BATCH / "cells" / old["id"] / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            if S.sha(source) != digest:
                raise ValueError("Historical frozen source drift: " + name)
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        patches.append(W.patch_client(root / ".local-agents/worker-runtime.py"))
        config = S.read(root / ".agent/experiment-config.json")
        request = S.read(root / ".agent/experiment-request.json")
        request["review_id"] = "wire-20261020-2-" + old["id"]
        (root / ".agent/experiment-request.json").write_text(
            json.dumps(request, indent=2), encoding="utf-8"
        )
        # Authenticate and compare material on a distinct no-model copy.
        offline = BATCH / "offline" / old["id"] / "isolated"
        shutil.copytree(root, offline)
        module = F.load(
            offline / ".local-agents/reviewer-runtime.py", "wire_offline_" + old["id"]
        )
        runtime = CORE.install(module, forward_reasoning_effort=True)(
            offline, request, config, object()
        )
        runtime.prepare()
        bundle = runtime.bundle()
        identity = old["identity"]
        prior = (
            Path(old["root"])
            / ".agent/tasks"
            / identity["task_id"]
            / "reviews"
            / identity["review_id"]
            / "semantic-input.json"
        )
        prior_bundle = S.read(prior)
        prior_bundle.pop("model_contract_prediction_review", None)
        if bundle != prior_bundle:
            raise ValueError("Semantic material differs for " + old["id"])
        proofs.append(
            {
                "cell": old["id"],
                "canonical_authentication": True,
                "semantic_material_unchanged": True,
                "old_bundle_sha256": S.sha(prior),
                "model_calls": 0,
            }
        )
        rows.append(
            {
                **old,
                "root": str(root),
                "identity": request,
                "files": {name: S.sha(root / name) for name in old["files"]},
            }
        )
    S.save(BATCH / "offline-material-proof.json", proofs)
    S.save(BATCH / "client-patches.json", patches)
    pins = {
        str(p.resolve()): S.sha(p)
        for p in [
            Path(__file__),
            Path(W.__file__),
            Path(CORE.__file__),
            S.KIT / "benchmarks/reviewer_semantic_entry.py",
            S.KIT / "benchmarks/reviewer_semantic_policy.py",
            S.KIT / "benchmarks/reviewer_semantic_transport.py",
            S.KIT / "benchmarks/reviewer_typed_observations.py",
            S.KIT / "benchmarks/reviewer_fixed_observations.py",
            BATCH / "controls-v2.xml",
        ]
    }
    S.save(
        BATCH / "registration.json",
        {
            "cells": rows,
            "registered": 20,
            "order": [r["id"] for r in rows],
            "pins": pins,
            "weekly_stop": 40,
            "batch_seconds": 14400,
            "candidate": "Only explicit per-request medium/low phase reasoning, matching the unchanged protocol prompt. Isolated client copies only; root production runtime/defaults unchanged.",
            "budgets": {
                "requests": 16,
                "errors": 4,
                "seconds": 600,
                "output_tokens": 4096,
                "output_recoveries": 1,
            },
            "gate": "Original16/16 substantive judgments plus exposed real4/4 causal judgments, original expected decisions and findings; no new Coder/holdout/product credit",
            "continue_rule": "Complete fixed20 ordinary semantic/protocol/output-limit outcomes. Stop HTTP/load/transport failure, safety/input drift, batch deadline or weekly40%. No resampling or replacement.",
            "input_scope": "Exact same contracts, source/tests, diff, observations and report schema as frozen20; model and other decoding unchanged. Fresh review IDs only.",
        },
    )
    print("Twenty authenticated, material-identical review controls frozen")


def run(cell, used, observed):
    if not 0 <= used < 40 or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh usage required")
    registration = S.read(BATCH / "registration.json")
    if any(S.sha(p) != digest for p, digest in registration["pins"].items()):
        raise ValueError("Reviewer candidate drift")
    for earlier in registration["order"][: registration["order"].index(cell)]:
        if S.read(BATCH / "results" / earlier / "process.json")["stop_batch"]:
            raise ValueError("Previous safety/infrastructure stop")
    row = next(r for r in registration["cells"] if r["id"] == cell)
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
    result = T.run(
        [
            S.PYTHON,
            "-B",
            S.KIT / "benchmarks/reviewer_contract_first.py",
            "--runtime-dir",
            root / ".local-agents",
            "--forward-reasoning-effort",
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
    result.update(
        seconds=time.monotonic() - start,
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
        "seconds",
        round(result["seconds"], 2),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare"])
    parser.parse_args()
    prepare()
