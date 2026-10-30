"""Fixed mixed behavior/static repair comparison; never revisit the ID family."""

import argparse
import copy
from pathlib import Path

import prepared_task_matrix as M

S, T, P, L = M.S, M.T, M.P, M.L
BATCH = P.I.BASE / "mixed-static-matrix-20261022-1"
OFFLINE = P.I.BASE / "supplemental-static-20261022-1"
ORDER = ["labels-B", "labels-A", "route-A", "route-B"]


def prepare(used):
    assert (
        S.read(OFFLINE / "decision.json")["status"]
        == "PASS_CURRENT_SUPPLEMENTAL_DIAGNOSTIC_PARITY"
    )
    tasks = {topic: copy.deepcopy(L.TASKS[topic]) for topic in ("labels", "route")}
    tasks["labels"]["start"] = tasks["labels"]["reference"].replace(
        "    result = dict(defaults)", "    unused = 1\n    result = {}"
    )
    tasks["route"]["start"] = tasks["route"]["reference"].replace(
        "    return base.rstrip('/') + '/' + encode_segment(segment)",
        "    encoded: int = encode_segment(segment)\n    return base + '/' + str(encoded)",
    )
    tasks["route"]["files"] = {
        "src/product/dependencies.py": tasks["route"]["dependency"]
    }
    tasks["route"]["dependency_context"] = tasks["route"]["dependency"]
    materials, rows = {}, {}
    for topic, spec in tasks.items():
        spec["risk_rationale"] = (
            "Restore existing behavior and static validity together; dependency errors/nonmutation/key order remain high-risk compatibility contracts."
        )
        spec["scenarios"] = [
            {
                "id": "normal",
                "text": "Keep all registered behavior, dependency calls and input ownership",
            },
            {
                "id": "boundary",
                "text": "Preserve empty/encoded/order/deletion boundaries",
            },
            {
                "id": "error",
                "text": "Preserve specified errors and pass strict static checks",
            },
        ]
        materials[topic] = M.template(BATCH, topic, spec)
        checks = S.read(BATCH / "task-controls" / (topic + ".json"))["baseline"]
        assert checks[0]["exit_code"] == 1
        assert checks[2 if topic == "labels" else 3]["exit_code"] == 1
    old = {
        name: OFFLINE / "preimages" / name
        for name in (
            ".local-agents/bounded/consolidated_harness.py",
            ".local-agents/bounded/static_focus_rules.py",
        )
    }
    for label in ORDER:
        topic, arm = label.split("-")
        row = M.cell(
            BATCH,
            label,
            topic,
            tasks[topic],
            materials[topic],
            Path(__file__),
            runtime_override=old if arm == "A" else None,
        )
        rows[label] = {**row, "arm": arm}
    for topic in tasks:
        assert rows[topic + "-A"]["start_sha256"] == rows[topic + "-B"]["start_sha256"]
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "mixed-static-evidence-comparison",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "existing-labels-behavior",
                "existing-route-behavior",
                "source-bound-diagnostics",
                "unchanged-acceptance",
            ],
            "dependencies": ["supplemental-static-20261022-1"],
            "registered": 4,
            "order": ORDER,
            "A": "Installed flat adapter callback already fixed, but supplemental checks not structurally focused (exact pre-fix two files).",
            "B": "Same installed runtime plus current-epoch supplemental Ruff/Pyright focus. No new instructions/parser or model capability.",
            "exposure": "Previously exposed qualified labels/route contracts, new controlled combined behavior/static defects. Not unknown migration; never pool with static-only matrix.",
            "budget": "Each C12requests/3effective edits/3write checks/1start check/12preparations/2protocol recovery/900s; fresh R16requests/4errors/4096output/600s. Outer2220percell, batch5400. Identical arms.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "single_residency": True,
            },
            "gate": "B2/2 full independent complete chains, zero assistance/drift/false release. Improvement requires B>A; deterministic parity repair may stand without claiming live gain.",
            "continue_rule": "Ordinary failure HOLD but finish fixed pairs; infra/safety/drift/deadline stops. No retries beyond per-cell controller, extra samples, Primary hints or test changes.",
            "Primary_cost": "Prepared fixed defects and existing contracts/tests; final full review, no live semantic rescue. Active time/cloud tokens unknown, no Primary-only economics.",
            "weekly_used_start": used,
            "weekly_cap": None,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                OFFLINE / "decision.json",
                *old.values(),
                *[v[1] for v in materials.values()],
            ),
        },
    )
    print("Four mixed-error cells frozen; no live yet")


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
