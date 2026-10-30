"""Installed receipt/return-binding smoke on two already qualified task families."""

import argparse
import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import prepared_task_matrix as M

S, P = M.S, M.P
BATCH = P.I.BASE / "primary-receipt-20261022-1"
ORDER = ["labels-1", "unique-1"]
ORIGINAL_COMMAND = P.command


def command(root, mode="unit", replay=None):
    args = ORIGINAL_COMMAND(root, mode=mode, replay=replay)
    if mode == "unit":
        args.append("--compact-output")
    return args


def prepare(used):
    controls = {}
    for name in ("binding-green.xml", "controls-3.xml", "integration-regression.xml"):
        suites = list(ET.parse(BATCH / name).getroot().iter("testsuite"))
        assert suites and all(
            int(s.attrib.get(k, 0)) == 0
            for s in suites
            for k in ("failures", "errors", "skipped")
        )
        controls[name] = sum(int(s.attrib["tests"]) for s in suites)
    rows, private = {}, []
    P.command = command
    for label in ORDER:
        topic = label.split("-")[0]
        spec = copy.deepcopy(M.L.TASKS[topic])
        spec["scenarios"] = [
            {
                "id": "normal",
                "text": "Complete the frozen normal behavior and preserve inputs",
            },
            {
                "id": "boundary",
                "text": "Empty values, stable ordering and identity follow the exact frozen contract",
            },
            {
                "id": "error",
                "text": "Preserve specified missing-key/deletion behavior without unrelated effects",
            },
        ]
        spec["risk_rationale"] = (
            "Same frozen behavior/compatibility obligations; validate output receipt and current-run return binding, not a new task family. Primary full review retained."
        )
        material = M.template(BATCH, topic, spec)
        private.append(material[1])
        row = M.cell(BATCH, label, topic, spec, material, Path(__file__))
        row["arm"], row["repeat"] = "installed-compact", 1
        process = S.read(BATCH / "replay" / label / "process.json")
        receipt = json.loads(process["stdout"])
        assert receipt["receipt_protocol"] == "bounded-primary-receipt-v1"
        assert receipt["reviewer"]["reviewer_decision"] == "NOT_RUN"
        assert receipt["reviewer"]["reviewer_input_authenticated"] is True
        assert receipt["primary_acceptance"] == "not_recorded_by_this_entry"
        rows[label] = row
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "optional-primary-execution-receipt",
            "feature_risk": "medium",
            "unit_risk": "high",
            "integration_risk": "high",
            "registered": 2,
            "order": ORDER,
            "offline_controls": controls,
            "exposure": "Two already qualified/exposed local-function contracts, one installed smoke each; not a novel-task score or model-quality A/B.",
            "candidate": "Default-off --compact-output; same model prompts, profile, checks, budgets. Also deterministic current-run Reviewer process/report/canonical completion binding repair, separately red/green fault-injected.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "context_length": 24576,
                "single_residency": True,
            },
            "common_budget": "C12requests/3edits/3postchecks/900s/4096output; R16requests/4errors/600s/4096output; 2220s/cell and 5400s/batch. Same existing profile.",
            "gate": "2/2 independent full acceptance plus receipt/canonical state parity and retained complete reports/process logs. No scope drift, assistance, budget reset, reroll or default enablement. Receipt never records Primary acceptance.",
            "continue_rule": "Ordinary failure retained and continue fixed second unit; infrastructure/safety/drift/deadline/user stop halts. Failure gate is not cleared by extra attempts.",
            "cost": "Measure actual output bytes only; Primary preparation/final review remain, cloud tokens and active time unknown. No savings claim.",
            "weekly_used_start": used,
            "weekly_cap": None,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                S.KIT / "tests/test_primary_receipt.py",
                S.KIT / "tests/test_bounded_review_result_binding.py",
                *[BATCH / p for p in controls],
                *private,
            ),
        },
    )
    print(
        "Two installed compact-output smoke cells registered; no live yet", flush=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        P.BATCH, P.ORDER, P.command = BATCH, ORDER, command
        P.run(args.cell, args.weekly_used)
