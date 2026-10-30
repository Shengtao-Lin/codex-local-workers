"""Fixed same-invocation recovery from two exposed starting states, no resets."""

import argparse
import ast
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import noop_block_recovery as N
import prepared_task_matrix as M

S, T, P = M.S, M.T, M.P
BATCH = P.I.BASE / "noop-block-recovery-20261022-1"
OLD = P.I.BASE / "stream-slice-transfer-20261022-3"
ORDER = [
    "stalled-B1",
    "legacy-A1",
    "stalled-A1",
    "legacy-B1",
    "legacy-B2",
    "stalled-A2",
    "legacy-A2",
    "stalled-B2",
]
BASE_COMMAND = P.command


def command(root, mode="unit", replay=None):
    args = BASE_COMMAND(root, mode=mode, replay=replay)
    label = S.read(root / ".agent/packet.json")["run_id"].removeprefix(BATCH.name + "-")
    args[2] = str(Path(N.__file__))
    if label.split("-")[1].startswith("B"):
        args.insert(3, "--noop-block-recovery")
    return args


def prepare(used):
    for name, expected in (("controls-1.xml", 46), ("core-regression-2.xml", 635)):
        suites = list(ET.parse(BATCH / name).getroot().iter("testsuite"))
        assert sum(int(s.attrib["tests"]) for s in suites) == expected
        assert all(
            int(s.attrib.get(k, 0)) == 0
            for s in suites
            for k in ("failures", "errors", "skipped")
        )
    old_row = S.read(OLD / "cells.json")["frame-1"]
    old_root = Path(old_row["root"])
    packet = S.read(old_root / ".agent/packet.json")
    capture = S.read(old_root / ".agent/capture-spec.json")
    reference = OLD / "reference-checks/frame/src/product/code.py"
    starts = {
        "legacy": OLD / "templates/frame/src/product/code.py",
        "stalled": old_root / M.TARGET,
    }
    specs, materials, rows = {}, {}, {}
    for topic, path in starts.items():
        source = path.read_text(encoding="utf-8")
        target = next(
            n
            for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == "_sse"
        )
        spec = {
            "header": "".join(source.splitlines(keepends=True)[: target.lineno - 1]),
            "start": T.extract(path, "_sse"),
            "reference": T.extract(reference, "_sse"),
            "symbol": "_sse",
            "contract": packet["goal"],
            "public": (old_root / "tests/test_contract.py").read_text(encoding="utf-8"),
            "private": Path(old_row["private_tests"]).read_text(encoding="utf-8"),
            "cases": capture["cases"],
            "scenarios": packet["acceptance_scenarios"],
            "risk_rationale": "Unchanged event protocol compatibility; new host routing must not reset authority, history or resource limits. Primary high-risk full review remains required.",
        }
        specs[topic] = spec
        materials[topic] = M.template(BATCH, topic, spec)
        assert S.sha(materials[topic][0] / M.TARGET) == S.sha(path)
        assert S.sha(materials[topic][1]) == S.sha(old_row["private_tests"])
    for label in ORDER:
        topic, arm_repeat = label.split("-")
        row = M.cell(
            BATCH, label, topic, specs[topic], materials[topic], Path(__file__)
        )
        row["arm"], row["repeat"] = arm_repeat[0], int(arm_repeat[1])
        if row["arm"] == "B" and row["repeat"] == 1:
            root = Path(row["root"])
            proof = BATCH / "switched-replay" / label / "isolated"
            shutil.copytree(root, proof)
            current = T.extract(root / M.TARGET, "_sse")
            correct = T.extract(materials[topic][2] / M.TARGET, "_sse")
            replay = proof.parent / "responses.json"
            S.save(
                replay,
                [{"kind": "replacement", "content": current}] * 2
                + [
                    {
                        "kind": "edits",
                        "edits": [{"find": current, "replace": correct}],
                        "reason": "",
                    }
                ],
            )
            result = T.run(command(proof, replay=replay), proof, timeout=180)
            S.save(proof.parent / "process.json", result)
            assert result["exit_code"] == 0, result
            archive = (
                proof
                / ".agent/tasks"
                / row["identity"]["task_id"]
                / "runs"
                / row["identity"]["run_id"]
            )
            actual = S.read(archive / "handoff.json")["consolidated_harness"]["actual"]
            assert actual["proposal_profile_switches"] == 1
            assert (
                actual["requests"] == 3
                and actual["edits"] == actual["post_edit_checks"] == 1
            )
        rows[label] = row
    for topic in starts:
        assert (
            len({r["start_sha256"] for r in rows.values() if r["topic"] == topic}) == 1
        )
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "single-invocation-interface-recovery",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "frame-contract",
                "single-budget",
                "current-inputs",
                "one-switch",
                "fresh-independent-review",
            ],
            "registered": 8,
            "order": ORDER,
            "dependencies": [
                "host-block-trial-20261022-2",
                "host-block-transfer-20261022-1",
            ],
            "A": "Current host with no callback; original flat whole-function profile, two consecutive noops stop.",
            "B": "Start identical to A. On two noops with source-current failed validation and remaining credits, trusted host switches output codec once to the unchanged exact-block candidate; same call/lock/ledger/deadline. No semantic hint, extra model/role or fresh budget.",
            "exposure": "One exposed real event-encoding contract, two starting states: original legacy implementation and prior failed model draft. Two repeats per state/arm, not two unknown tasks. Old failures and previous gates unchanged. No usage-type case rerun.",
            "common_budget": "C12requests/3edits/3post checks/1initial/12format preparations/2protocol recoveries/900s/4096output. R16requests/4errors/600s/4096output.2220s/cell,5400s/batch. Switch occurs only once and never replenishes any counter.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "context_length": 24576,
                "single_residency": True,
            },
            "gate": "B4/4 full independent current checks+fresh Reviewer+Primary acceptance, at least one genuine model-driven switch and accepted post-switch edit, zero reset/drift/assistance/wrong release. Otherwise HOLD. A comparisons retained; normal success without switch does not count as recovery evidence.",
            "continue_rule": "Ordinary failure keeps HOLD but finish registered pairs; infrastructure, safety, input drift, fixed time or user stop halts. No same-code Reviewer reroll, new attempts, hints, changed tests or discarded failure.",
            "next_branch": "If passed, installed default-off routing qualification/negative controls before any product enablement. If nonadopted, retain default stop and route unresolved work to Primary with compact facts; do not broaden to unqualified type repairs or alter Reviewer to clear this gate.",
            "primary": "Original contract/tests/reference reused; one-time host development tracked separately from per-task review. No live semantic help/production coding. Active time/cloud tokens unknown; no savings claim.",
            "weekly_used_start": used,
            "weekly_cap": None,
            "production_defaults_changed": False,
            "commit_push": False,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                Path(N.__file__),
                Path(N.BLOCK.__file__),
                S.KIT / "tests/test_noop_block_recovery.py",
                BATCH / "controls-1.xml",
                BATCH / "core-regression-2.xml",
                *[v[1] for v in materials.values()],
            ),
        },
    )
    print(
        "Eight fixed single-call recovery cells registered after offline controls; no live yet",
        flush=True,
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
