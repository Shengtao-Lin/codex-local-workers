"""Frozen native Agent smoke: three offline controls, then ONE live exposed unit."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import bounded_evidence_support as S
import project_caller_trial as J

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-native-agent-20261023-1"
ORIGIN = BATCH.parent / "strata-complex-20261023-2"
CASES = ["control", "length-control", "throw-control", "live"]
TARGET = "src/evaluation_harness/adapters/common.py"
INSTANCE = "2b1266cf-c609-421d-a538-19bfd4f7ea73"


def command(argv, root, timeout=120):
    result = subprocess.run(
        [str(v) for v in argv],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=timeout,
    )
    return {
        "argv": [str(v) for v in argv],
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def prepare(used):
    assert not BATCH.exists() and used < 50
    original = S.read(ORIGIN / "registration.json")
    assert all(S.sha(p) == h for p, h in original["pins"].items())
    sources = [
        "strata_native_trial.py",
        "strata_native_agent.mjs",
        "strata_native_agent_core.mjs",
        "strata_native_agent_host.py",
        "strata_bridge_host.py",
        "strata_kit_tool_bridge.mjs",
    ]
    S.save(
        BATCH / "registration.json",
        {
            "batch_id": BATCH.name,
            "order": CASES,
            "weekly_used_start": used,
            "weekly_cap": 50,
            "controls": 3,
            "live_registered": 1,
            "candidate": "installed native AgentLoop + DeepSeek Messages adapter + local-only guarded fetch + existing host controller",
            "task": "Exposed frozen mapping_raw strict UTF8 contract; complete module and public tests supplied. No new-repo or autonomous-location credit.",
            "feature_id": "native-agent-read-edit-unit",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Existing public parser compatibility; no reduced risk from single function; full Primary independent review",
            "roles": "Native implementation agent -> original host checks/handoff -> full Primary. No Local Reviewer/Explorer/Coordinator.",
            "model": "same resident iq3_s128K/parallel1; declared client64K,12288 output,4096 thinking,medium,temp1/top_p.95/top_k20; native Messages is NEW protocol profile",
            "budget": "Same host12 action opportunities/3 effective edits/1initial+3postchecks/900s, plus SHARED model reservations+host action opportunities <=12. Per provider timeout <=600s AND remaining task time; no retry plugin; no reset. Output <=12288 each, <=147456 conservative task ceiling.",
            "safety": "Fixed127.0.0.1:47831 Messages/native status only; redirect refused; no cloud fallback, SDK profile, shell/fs/Web/skills/recursive agent; current capture stays required",
            "gate": "Offline controls complete first: tool edit handoff, max-token stop, transport error stop. Budget9+native lifecycle3 controls pass. Live needs current canonical handoff+independent164/statics+Primary actualdiff, no protected drift/assistance. One run, no reroll.",
            "stop": "Infra/residency/protected drift/safety/weekly50/user stop: halt; ordinary live failure retained, HOLD, no automatic repeat",
            "not_tested": "Generic capture/multi-file/test authoring, skills/Web, real HTTP timeout, model restart recovery, production enablement, cloud savings",
            "pins": {
                str(Path(__file__).with_name(n)): S.sha(Path(__file__).with_name(n))
                for n in sources
            },
        },
    )
    for name in sources:
        destination = BATCH / "candidate-source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).with_name(name), destination)
    for case in CASES:
        root = BATCH / "cells" / case / "isolated"
        J.copy_project(ORIGIN / "templates/raw", root)
        installed = ORIGIN / "cells/raw-1/isolated"
        shutil.copytree(installed / ".local-agents", root / ".local-agents")
        shutil.copyfile(installed / "AGENTS.md", root / "AGENTS.md")
        packet = S.read(installed / ".agent/packet.json")
        packet.update(
            {k: BATCH.name + "-" + case for k in ("task_id", "unit_id", "run_id")}
        )
        for name, value in [
            ("packet", packet),
            ("config", S.read(installed / ".agent/config.json")),
            ("capture-spec", S.read(installed / ".agent/capture-spec.json")),
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
        program = {"mode": case, "instance_id": INSTANCE}
        if case == "control":
            program["actions"] = [
                {
                    "name": "kit_read",
                    "arguments": {
                        "path": "src/evaluation_harness/canonical/models.py",
                        "start_line": 1,
                        "end_line": 20,
                    },
                },
                {
                    "name": "kit_propose",
                    "arguments": {
                        "path": TARGET,
                        "expected_sha256": "@current",
                        "content": J.function_source(
                            ORIGIN / "references/raw" / TARGET, "mapping_raw"
                        ),
                    },
                },
            ]
        S.save(root.parent / "frontend.json", program)
    print("Registered3 offline controls and1 live unit; no model calls")


def run(case, used):
    assert used < 50
    registration = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in registration["pins"].items())
    if case == "live":
        for control in CASES[:3]:
            prior = S.read(BATCH / "cells" / control / "result.json")
            assert prior["expected_outcome"] is True
    root = BATCH / "cells" / case / "isolated"
    packet = S.read(root / ".agent/packet.json")
    prepared = root / ".agent/prepared" / packet["run_id"]
    result = command(
        [
            S.PYTHON,
            "-B",
            Path(__file__).with_name("strata_native_agent_host.py"),
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
    expected = (
        result["exit_code"] == 0 and summary["host_handoff_verified"]
        if case in {"control", "live"}
        else (
            result["exit_code"] == 2
            and not summary["host_handoff_verified"]
            and summary["actual"]["edits"] == 0
        )
    )
    S.save(
        root.parent / "result.json",
        {"expected_outcome": expected, "case": case, **summary},
    )
    print(result["stdout"], result["stderr"][-3000:], flush=True)
    assert expected, result


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
