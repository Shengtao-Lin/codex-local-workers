"""Version2 qualification matrix, existing frozen contracts; no score replacement."""

import argparse
import os
import shutil
from pathlib import Path

import bounded_evidence_support as S
import project_caller_trial as J
from strata_native_trial import command

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-native-v2-20261023-1"
BASE = BATCH.parent
CASES = ["control", "raw-1", "tools-1", "hash-1", "raw-2", "tools-2", "hash-2"]
SOURCES = [
    "strata_native_matrix.py",
    "strata_native_host_v2.py",
    "strata_native_feedback.py",
    "strata_manifest_search.py",
    "strata_native_agent.mjs",
    "strata_native_agent_core.mjs",
    "strata_native_agent_host.py",
    "strata_bridge_host.py",
    "strata_kit_tool_bridge.mjs",
]
ENTRY = Path(__file__).with_name("strata_native_host_v2.py")
CANDIDATE = "Native v2: manifest-only directory SEARCH + deterministic feedback deltas on same native Agent/host"
CHANGES = "No model/permissions/writable scope/test/validation/budget change; native host toolset same. Directory selector only scans approved exact files, no walk. Initial task unchanged; feedback drops repeated immutable snapshot and only sends fresh evidence/current function+failures after edits."
CONTROL_EXTRA = []


def origin(topic):
    batch = BASE / (
        "strata-subagent-20261023-1" if topic == "hash" else "strata-complex-20261023-2"
    )
    seed = (
        batch / "cells" / ("hash-1" if topic == "hash" else topic + "-1") / "isolated"
    )
    return batch, seed


def prepare(used):
    assert used < 50 and not BATCH.exists()
    S.save(
        BATCH / "registration.json",
        {
            "batch_id": BATCH.name,
            "weekly_used_start": used,
            "weekly_stop": 50,
            "candidate": CANDIDATE,
            "order": CASES,
            "live_registered": 6,
            "offline_controls": 1,
            "contracts": "Frozen raw/tools/hash from recorded full sibling snapshots. All already exposed,2 executions each, NOT new-repo/holdout transfer or prior failure replacement",
            "changes": CHANGES,
            "budget": "Shared model reservations+host actions<=12;3 effective edits+1initial/3postchecks;900s,12288output/4096thinking,64K declared; same iq3_s128K/parallel1/temp1/top_p.95/top_k20. No retry plugin or hidden reset.",
            "gates": "26 new+reused offline unit controls,4 native lifecycle controls, actual manifest search->edit->checks composition control beforelive. Qualification6/6 independent full project checks and Primary actualdiff; zero unsafe drift or assisted code. Not production release by itself.",
            "continue": "Ordinary failure makes HOLD but finish other preregistered cells for diagnostic evidence. Infrastructure/residency/safety/protected drift/user/weekly50 stop dispatch. Inspect each result. No reroll or midbatch change.",
            "roles": "Native implementation Agent -> same original host checks -> full Primary; no fresh Local Reviewer, Explorer or Coordinator; experimental route only",
            "risk": "Feature/unit/integration high: parser/event identity/hash public compatibility, full final source and actual caller tests",
            "model": "Same resident iq3_s instance2b1266cf-c609-421d-a538-19bfd4f7ea73; same requested native Messages profile as first smoke",
            "primary": "Reuse frozen detailed contracts, protected public/private tests/reference; no live semantic guidance. Prep/adapter development and repeated final-review costs separate; savings unknown",
            "pending_release": "Independent installation without LM Studio, portable installed entry, broader task/repair/fault coverage; no release or push based on6/6 alone",
            "pins": {
                str(Path(__file__).with_name(n)): S.sha(Path(__file__).with_name(n))
                for n in SOURCES
            },
        },
    )
    for name in SOURCES:
        target = BATCH / "candidate-source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).with_name(name), target)
    for case in CASES:
        topic = "raw" if case == "control" else case.split("-")[0]
        batch, seed = origin(topic)
        root = BATCH / "cells" / case / "isolated"
        J.copy_project(batch / "templates" / topic, root)
        shutil.copytree(seed / ".local-agents", root / ".local-agents")
        shutil.copyfile(seed / "AGENTS.md", root / "AGENTS.md")
        packet = S.read(seed / ".agent/packet.json")
        packet.update(
            {k: BATCH.name + "-" + case for k in ("task_id", "unit_id", "run_id")}
        )
        for name, value in [
            ("packet", packet),
            ("config", S.read(seed / ".agent/config.json")),
            ("capture-spec", S.read(seed / ".agent/capture-spec.json")),
        ]:
            S.save(root / f".agent/{name}.json", value)
        result = command(
            [
                S.PYTHON,
                "-B",
                root / ".local-agents/local-bounded-prepare.py",
                "--packet",
                ".agent/packet.json",
                "--config",
                ".agent/config.json",
                "--capture-spec",
                ".agent/capture-spec.json",
                "--apply",
            ],
            root,
        )
        S.save(root.parent / "prepare.json", result)
        assert result["exit_code"] == 0, result
        program = {
            "mode": "control" if case == "control" else "live",
            "instance_id": "2b1266cf-c609-421d-a538-19bfd4f7ea73",
        }
        if case == "control":
            program["actions"] = [
                *CONTROL_EXTRA,
                {
                    "name": "kit_search",
                    "arguments": {
                        "path": "src/evaluation_harness",
                        "query": "isinstance(",
                    },
                },
                {
                    "name": "kit_propose",
                    "arguments": {
                        "path": packet["scope"]["modify"][0],
                        "expected_sha256": "@current",
                        "content": J.function_source(
                            batch / "references/raw" / packet["scope"]["modify"][0],
                            "mapping_raw",
                        ),
                    },
                },
            ]
        S.save(root.parent / "frontend.json", program)
    print("Frozen1 control +6 known-contract live units; no model calls", flush=True)


def run(case, used):
    assert used < 50
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    if case != "control":
        assert (
            S.read(BATCH / "cells/control/result.json")["host_handoff_verified"] is True
        )
    root = BATCH / "cells" / case / "isolated"
    packet = S.read(root / ".agent/packet.json")
    prepared = root / ".agent/prepared" / packet["run_id"]
    result = command(
        [
            S.PYTHON,
            "-B",
            ENTRY,
            "--packet",
            prepared / "packet.json",
            "--config",
            prepared / "config.json",
            "--program",
            root.parent / "frontend.json",
        ],
        root,
        timeout=1020,
    )
    S.save(root.parent / "process.json", result)
    summary = S.read(root / ".agent/native-host-summary.json")
    S.save(root.parent / "result.json", {"exit_code": result["exit_code"], **summary})
    print(result["stdout"], result["stderr"][-2000:], flush=True)
    if case == "control":
        assert result["exit_code"] == 0 and summary["host_handoff_verified"], result
        assert (
            summary["actual"]["evidence_actions"] == 1
            and summary["provider_calls"] == 0
        )
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        feedback = S.read(archive / "native-feedback-2.json")["context"]
        assert "task_material" not in feedback
        assert feedback["evidence_observations"][0]["observation"]["scope"].startswith(
            "exact approved"
        )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", *CASES])
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    prepare(args.weekly_used) if args.mode == "prepare" else run(
        args.mode, args.weekly_used
    )
