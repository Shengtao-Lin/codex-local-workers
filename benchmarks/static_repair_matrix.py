"""Two exposed contracts, two static defects, matched old/corrected flat adapter."""

import argparse
import copy
from pathlib import Path

import prepared_task_matrix as M

S, P, L = M.S, M.P, M.L
BATCH = P.I.BASE / "static-repair-matrix-20261022-1"
OFFLINE = P.I.BASE / "flat-diagnostics-20261022-1"
ORDER = ["labels-A", "labels-B", "route-B", "route-A"]


def prepare(used):
    assert (
        S.read(OFFLINE / "decision.json")["status"] == "PASS_DIAGNOSTIC_CALLBACK_PARITY"
    )
    tasks = {topic: copy.deepcopy(L.TASKS[topic]) for topic in ("labels", "route")}
    tasks["labels"]["start"] = tasks["labels"]["reference"].replace(
        "result.pop(key, None)", "removed = result.pop(key, None)"
    )
    tasks["route"]["start"] = tasks["route"]["reference"].replace(
        "    return base.rstrip('/') + '/' + encode_segment(segment)",
        "    encoded: int = encode_segment(segment)\n    return base.rstrip('/') + '/' + str(encoded)",
    )
    tasks["route"]["files"] = {
        "src/product/dependencies.py": tasks["route"]["dependency"]
    }
    tasks["route"]["dependency_context"] = tasks["route"]["dependency"]
    rows = {}
    materials = {}
    for topic, spec in tasks.items():
        spec["risk_rationale"] = (
            "Preserve exact existing behavior while repairing static diagnostics; errors and input compatibility remain high-risk invariants."
        )
        spec["scenarios"] = [
            {
                "id": "normal",
                "text": "Keep all registered results and object/input behavior",
            },
            {
                "id": "boundary",
                "text": "Preserve empty/deletion or encoded-boundary behavior",
            },
            {
                "id": "error",
                "text": "Retain documented errors and pass strict static checks",
            },
        ]
        materials[topic] = M.template(BATCH, topic, spec)
        baseline = S.read(BATCH / "task-controls" / f"{topic}.json")["baseline"]
        assert baseline[0]["exit_code"] == 0, (
            "This diagnostic needs behavior-passing, static-failing starts"
        )
        assert baseline[2 if topic == "labels" else 3]["exit_code"] != 0
    old = OFFLINE / "preimages/.local-agents/bounded/compatibility_profile.py"
    for cell in ORDER:
        topic, arm = cell.split("-")
        row = M.cell(
            BATCH,
            cell,
            topic,
            tasks[topic],
            materials[topic],
            Path(__file__),
            runtime_override={".local-agents/bounded/compatibility_profile.py": old}
            if arm == "A"
            else None,
        )
        rows[cell] = {**row, "arm": arm}
    for topic in tasks:
        assert rows[topic + "-A"]["start_sha256"] == rows[topic + "-B"]["start_sha256"]
    S.save(BATCH / "cells.json", rows)
    registration = {
        "feature_id": "static-repair-callback-diagnostic",
        "feature_risk": "high",
        "unit_risk": "high",
        "integration_risk": "high",
        "order": ORDER,
        "registered": 4,
        "weekly_stop": None,
        "weekly_used_start": used,
        "batch_seconds": 5400,
        "hypothesis": "Restored existing source-bound static focus may improve conversion into behavior-preserving fixes; callback parity itself is separately proven offline.",
        "arms": {
            "A": "frozen prior compatibility adapter without callback",
            "B": "same installed runtime with existing callback forwarded",
        },
        "exposure": "Previously exposed labels/route contracts; new controlled static-defect drafts, not new task migration, not original natural errors.",
        "gate": "B2/2 fresh Reviewer plus Primary independent full checks, zero assistance/drift. Improvement claim additionally requires B>A; parity fix can remain for deterministic correctness without claiming live benefit.",
        "continue_rule": "Ordinary failure HOLD but finish fixed pairs. Infra/safety/unchanged-input drift/fixed time stop; no extra samples or repairs from Primary.",
        "budget": S.read(P.BATCH / "registration.json")["budget"],
        "roles": S.read(P.BATCH / "registration.json")["roles"],
        "unchanged": [
            "models",
            "single residency",
            "source/contract/test inputs within pairs",
            "prompts/schema",
            "editor/formatter",
            "checks/budgets",
            "Reviewer",
            "Primary full review",
            "defaults",
        ],
        "Primary": "Prepared controlled defects and unchanged contracts/tests; no semantic guidance in live. No Primary-only comparison, costs unknown.",
        "pins": M.pins(
            BATCH,
            Path(__file__),
            old,
            OFFLINE / "decision.json",
            *(m[1] for m in materials.values()),
        ),
    }
    S.save(BATCH / "registration.json", registration)
    print("Four frozen cells; no live yet")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        P.BATCH, P.ORDER = BATCH, ORDER
        P.run(args.cell, args.weekly_used)
