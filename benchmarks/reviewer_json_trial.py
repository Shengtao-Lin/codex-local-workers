"""Frozen compatibility probe and conditional20 semantic controls for recovery."""

import argparse
import json
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import reviewer_effort_compare as PREVIOUS
import reviewer_json_recovery as J
import reviewer_wire_trial as R

BATCH = S.KIT / "benchmarks/work/harness-convergence/reviewer-json-recovery-20261020-1"


def prepare():
    if not (PREVIOUS.BATCH / "decision.json").exists():
        raise ValueError("Previous fixed batch not closed")
    controls = list(ET.parse(BATCH / "offline-controls-v3.xml").iter("testcase"))
    if len(controls) != 13 or any(
        c.find(tag) is not None
        for c in controls
        for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("All13 original gate/budget/recovery controls required")
    parent = S.read(R.BATCH / "registration.json")
    rows = []
    for old in parent["cells"]:
        root = BATCH / "cells" / old["id"] / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            if S.sha(source) != digest:
                raise ValueError("Frozen original input drift")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        path = root / ".agent/experiment-request.json"
        request = S.read(path)
        request["review_id"] = BATCH.name + "-" + old["id"]
        path.write_text(json.dumps(request, indent=2), encoding="utf-8")
        rows.append(
            {
                **old,
                "root": str(root),
                "identity": request,
                "files": {p: S.sha(root / p) for p in old["files"]},
            }
        )
    pins = {
        **parent["pins"],
        str(Path(J.__file__).resolve()): S.sha(J.__file__),
        str(Path(__file__).resolve()): S.sha(__file__),
        str(BATCH / "offline-controls-v3.xml"): S.sha(
            BATCH / "offline-controls-v3.xml"
        ),
    }
    S.save(
        BATCH / "registration.json",
        {
            "cells": rows,
            "order": [r["id"] for r in rows],
            "registered": 20,
            "pins": pins,
            "weekly_stop": 50,
            "batch_seconds": 10800,
            "candidate": "Only after two global output-limit failures with no complete source REPORT, one strict-JSON REPORT recovery. Same semantic schema/observation accounting/quote+identity+source gates; no semantic judgment resampling.",
            "budget": {
                "requests": 16,
                "errors": 4,
                "seconds": 600,
                "output_tokens": 4096,
                "native_output_recoveries": 1,
                "additional_changed_format_recoveries": 1,
            },
            "budget_change": "Old candidate stopped after second output exhaustion; new candidate may spend one more request from the SAME16/4/600 global pool in changed format. This is a newly registered recovery policy, not an unchanged historical budget or reinterpretation of old failures.",
            "probe": {
                "model_calls": 1,
                "max_tokens": 1024,
                "timeout": 180,
                "scope": "Synthetic full REPORT-schema transport only,0semantic/product credit; must pass before any20 real control",
            },
            "conditional": {
                "first": ["sample-17-candidate", "sample-18-candidate"],
                "requires": "Both independently correct judgments/report hashes before remaining18",
            },
            "gate": "Original16/16 and exposed real4/4 substantive decisions, no wrong pass or invented defect. Same exact source/contracts/tests/observations. No Coder/R4/product qualification from this control matrix alone.",
            "continue_rule": "Initial pair completes ordinary outcomes; expand only on both correct. Then complete remaining18 ordinary outcomes. Infra/safety/drift/deadline/weekly50 stop, no resampling or extra mode search.",
        },
    )
    print(
        "Conditional20 frozen; live synthetic JSON compatibility probe required first"
    )


def probe(used, observed):
    if not 0 <= used < 50 or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh usage required")
    reg = S.read(BATCH / "registration.json")
    root = Path(reg["cells"][0]["root"])
    module = F.load(root / ".local-agents/worker-runtime.py", "json_probe_worker")
    config = S.read(root / ".agent/experiment-config.json")
    schema = J.action_schema(J.CORE.ACCOUNTING.TOOLS)
    client = module.LMStudioClient(
        config["lmstudio_base_url"],
        config["reviewer_model"],
        180,
        max_tokens=1024,
        temperature=0,
        structured_output=True,
        action_schema=schema,
        schema_name="reviewer_report_compatibility",
        context_length=24576,
        context_safety_margin=1024,
    )
    client.reasoning_effort = "low"
    value = {
        "action": "REPORT",
        "arguments": {
            "obligations": [
                {
                    "id": "compat-only",
                    "verdict": "satisfied",
                    "evidence_ids": ["probe"],
                    "explanation": "Synthetic format copy, no repository review or acceptance.",
                    "line": None,
                    "fix": "",
                    "severity": "low",
                }
            ],
            "uncertainties": [],
            "observation_assessments": [],
        },
    }
    S.save(
        BATCH / "probe-start.json",
        {"weekly_used": used, "observed_at": observed, "expected": value},
    )
    started = time.monotonic()
    with module.MODEL_RESIDENCY.role_model_lease(client, config):
        client.preflight()
        raw = client.complete(
            [
                {
                    "role": "system",
                    "content": "Copy the supplied JSON object exactly. This is a synthetic transport check, not repository review.",
                },
                {"role": "user", "content": json.dumps(value)},
            ]
        )
    result = {
        "passed": json.loads(raw) == value,
        "actual_model_calls": 1,
        "source_review_credit": 0,
        "request_stats": client.last_request_stats,
        "seconds": time.monotonic() - started,
        "schema_sha256_source": S.sha(J.__file__),
    }
    S.save(BATCH / "probe-result.json", result)
    if not result["passed"]:
        raise ValueError("JSON transport compatibility not established")
    print("Synthetic full REPORT JSON schema probe passed;0semantic credit")


def run(cell, used, observed):
    if not 0 <= used < 50 or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh usage required")
    reg = S.read(BATCH / "registration.json")
    if not S.read(BATCH / "probe-result.json")["passed"] or any(
        S.sha(p) != h for p, h in reg["pins"].items()
    ):
        raise ValueError("Probe/candidate not current")
    if cell not in reg["conditional"]["first"]:
        for name in reg["conditional"]["first"]:
            receipt = S.read(BATCH / "primary" / (name + ".json"))
            if not receipt["correct"] or receipt["report_sha256"] != S.sha(
                BATCH / "cells" / name / "reviewer.json"
            ):
                raise ValueError("Initial pair not qualified")
    for previous in reg["order"][: reg["order"].index(cell)]:
        if S.read(BATCH / "results" / previous / "process.json")["stop_batch"]:
            raise ValueError("Previous infrastructure/safety stop")
    row = next(r for r in reg["cells"] if r["id"] == cell)
    root = Path(row["root"])
    if any(S.sha(root / p) != h for p, h in row["files"].items()):
        raise ValueError("Input drift")
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = 10800 - (time.time() - S.read(clock)["epoch"])
    if remaining <= 0:
        raise ValueError("Batch deadline")
    S.save(
        BATCH / "results" / cell / "start.json",
        {"weekly_used": used, "observed_at": observed},
    )
    started = time.monotonic()
    result = T.run(
        [
            S.PYTHON,
            "-B",
            Path(J.__file__),
            "--runtime-dir",
            root / ".local-agents",
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
    drift = [p for p, h in row["files"].items() if S.sha(root / p) != h]
    infra = report.get("infra_failure") or {}
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
        report.get("decision"),
        "expected",
        row["expected_decision"],
        round(result["seconds"], 2),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare"])
    p.parse_args()
    prepare()
