"""Fixed whole-function vs exact-block comparison on two exposed failed drafts."""

import argparse
import ast
import shutil
from pathlib import Path

import host_block_proposal as B
import prepared_task_matrix as M

S, T, P = M.S, M.T, M.P
BATCH = P.I.BASE / "host-block-trial-20261022-2"
OFFLINE = P.I.BASE / "host-block-offline-20261022-1"
ORDER = [
    "usage-A1",
    "frame-B1",
    "usage-B1",
    "frame-A1",
    "frame-A2",
    "usage-B2",
    "frame-B2",
    "usage-A2",
]
PARENTS = {
    "usage": ("usage-completion-transfer-20261022-1", "usage-1", "usage"),
    "frame": ("stream-slice-transfer-20261022-3", "frame-1", "frame"),
}
BASE_COMMAND = P.command


def command(root, mode="unit", replay=None):
    args = BASE_COMMAND(root, mode=mode, replay=replay)
    label = S.read(root / ".agent/packet.json")["run_id"].removeprefix(BATCH.name + "-")
    arm = label.split("-")[1][0]
    args[2] = str(Path(B.__file__))
    if arm == "B":
        args.insert(3, "--host-blocks")
    return args


def prepare(used):
    import xml.etree.ElementTree as ET

    suites = ET.parse(OFFLINE / "controls-6.xml").getroot()
    assert all(
        int(s.attrib.get("errors", 0)) == int(s.attrib.get("failures", 0)) == 0
        for s in suites.iter("testsuite")
    )
    materials, specs, parents, rows = {}, {}, {}, {}
    for topic, (batch_name, label, ref_topic) in PARENTS.items():
        old = P.I.BASE / batch_name
        row = S.read(old / "cells.json")[label]
        root = Path(row["root"])
        packet = S.read(root / ".agent/packet.json")
        capture = S.read(root / ".agent/capture-spec.json")
        current = (root / M.TARGET).read_text(encoding="utf-8")
        symbol = capture["target"]["symbol"]
        target = next(
            n
            for n in ast.parse(current).body
            if isinstance(n, ast.FunctionDef) and n.name == symbol
        )
        header = "".join(current.splitlines(keepends=True)[: target.lineno - 1])
        reference = old / "reference-checks" / ref_topic / M.TARGET
        spec = {
            "header": header,
            "start": T.extract(root / M.TARGET, symbol),
            "reference": T.extract(reference, symbol),
            "symbol": symbol,
            "contract": packet["goal"],
            "public": (root / "tests/test_contract.py").read_text(encoding="utf-8"),
            "private": Path(row["private_tests"]).read_text(encoding="utf-8"),
            "cases": capture["cases"],
            "scenarios": packet["acceptance_scenarios"],
            "risk_rationale": "Preserve complete existing compatibility contract, strict static checks and independent acceptance while changing proposal granularity only.",
        }
        specs[topic] = spec
        materials[topic] = M.template(BATCH, topic, spec)
        assert S.sha(materials[topic][0] / M.TARGET) == S.sha(root / M.TARGET)
        assert S.sha(materials[topic][0] / "tests/test_contract.py") == S.sha(
            root / "tests/test_contract.py"
        )
        assert S.sha(materials[topic][1]) == S.sha(row["private_tests"])
        parents[topic] = {
            "batch": batch_name,
            "cell": label,
            "source_sha256": S.sha(root / M.TARGET),
            "tests_sha256": S.sha(root / "tests/test_contract.py"),
            "private_sha256": S.sha(row["private_tests"]),
            "contract": packet["goal"],
        }
    for label in ORDER:
        topic, arm_repeat = label.split("-")
        row = M.cell(
            BATCH, label, topic, specs[topic], materials[topic], Path(__file__)
        )
        row["arm"], row["repeat"] = arm_repeat[0], int(arm_repeat[1])
        root = Path(row["root"])
        # Extra installed candidate replay: reference is outside live readable scope.
        # This is offline plumbing proof, never a model response or accepted run.
        proof = BATCH / "block-replay" / label / "isolated"
        shutil.copytree(root, proof)
        reference = T.extract(materials[topic][2] / M.TARGET, specs[topic]["symbol"])
        original = T.extract(root / M.TARGET, specs[topic]["symbol"])
        value = (
            {
                "kind": "edits",
                "edits": [{"find": original, "replace": reference}],
                "reason": "",
            }
            if row["arm"] == "B"
            else {"kind": "replacement", "content": reference}
        )
        replay = proof.parent / "reference.json"
        S.save(replay, [value])
        result = T.run(command(proof, replay=replay), proof, timeout=180)
        S.save(proof.parent / "process.json", result)
        assert result["exit_code"] == 0, result
        rows[label] = row
    for topic in specs:
        assert (
            len({row["start_sha256"] for row in rows.values() if row["topic"] == topic})
            == 1
        )
    S.save(BATCH / "parents.json", parents)
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "host-owned-block-repair-comparison",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "usage",
                "frame",
                "atomic-target-edit",
                "current-validation",
                "independent-acceptance",
            ],
            "dependencies": [
                "checked-static-research-20261022-1",
                "repair-representation-20261018-1",
            ],
            "registered": 8,
            "order": ORDER,
            "hypothesis": "A small exact-block proposal interface reduces no-op/copied-code repair stalls compared with full-function proposals under the same existing host-driven checks.",
            "A": "Unchanged installed flat-v1 complete-function/module proposal, current diagnostic parity fixes.",
            "B": "Same base/runtime/facts/render/editor/checks/reviewer; only Coder schema/system output instructions and in-memory materializer change to 1-3 nonoverlapping exact blocks inside the existing target. Same atomic effective-edit accounting, no new privileges, no host semantic fix.",
            "exposure": "Two already-exposed failed real slices, two repeats per arm. Both arms start with exact same frozen failed draft, tests, original contract, captures and private acceptance. These are new diagnostic trials with fresh budgets, not same-parent recovery, unknown tasks or replacement of old scores. No Explorer advice included.",
            "historical_distinction": "Earlier span experiment restricted a specific helper declaration under the previous harness. This tests model-selected blocks through the current host-owned complete loop on both behavioral and type-check repair; not the old native action protocol.",
            "budgets": "Identical C12requests/3effective atomic proposals/3full post-edit checks/1initial/12format preparations/2protocol recoveries/2consecutive noops/900s/4096output. R16requests/4errors/600s/4096output.2220s/cell,5400s/batch. No extra research calls or primary hints.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "context_length": 24576,
                "single_residency": True,
            },
            "roles_not_used": "Explorer: known targets and real failure facts already available; Coordinator: separately evaluated cohesive units. No claim about either role.",
            "gate": "B4/4 checks+fresh Reviewer+Primary independent full review, zero safety/protected drift or assisted success. Comparative benefit additionally requires B>A or fewer failures/noops at equal accepted counts. Otherwise no adoption; any failed cell keeps strict batch HOLD. No same-code Reviewer rerolls.",
            "continue_rule": "Ordinary failure retained and remaining fixed pairs continue; unsafe/scope/input drift, infrastructure, batch deadline or user stop halts. NOT_RUN remains distinct. No extra attempts to fill pass counts.",
            "conditional_next": "Only demonstrated benefit warrants unchanged-candidate new-task transfer. No benefit: retire added block complexity and report observed model/representation boundary; no same-case prompt expansion.",
            "primary_cost": "Reuse original detailed contracts/tests/reference. New adapter/safety tests/registration is one-time development; final source/evidence review remains recurring work. No extra semantic advice or code takeover in live. Cloud tokens/active time unknown; no savings claim.",
            "weekly_used_start": used,
            "weekly_cap": None,
            "production_defaults_changed": False,
            "commit_push": False,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                Path(B.__file__),
                S.KIT / "tests/test_host_block_proposal.py",
            OFFLINE / "controls-6.xml",
                BATCH / "parents.json",
                *[v[1] for v in materials.values()],
            ),
        },
    )
    print(
        "Eight matched exposed-draft cells registered; all offline entry replays passed; no live yet",
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
