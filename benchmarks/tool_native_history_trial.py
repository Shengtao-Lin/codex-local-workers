"""Matched native history experiment, retaining all real C/R gates and failures."""

import argparse
import importlib.util

import tool_compatibility_trial as compat
from capability_fit import KIT, WORK, write
from inherited_context_recovery import read
from layer_isolation import command, verify_hashes

BASE = WORK / "tool-native-history-1"
ARMS = ("control-1", "history-1", "history-2", "control-2")
TRANSPORTS = {}


def prepare(arm):
    compat.BASE, compat.ARMS = BASE, ARMS
    if (
        read(WORK / "tool-compatibility-2/accepted-control/.agent/positive.json")[
            "passed"
        ]
        is not True
    ):
        raise ValueError("13-test independent positive control required")
    if not (BASE / "registration.json").exists():
        write(
            BASE / "registration.json",
            {
                "arms_in_order": list(ARMS),
                "weekly_ceiling": 23,
                "axis": "Both native BLOCK-only; candidate correlates observed native calls and unchanged adjacent observations as tool history",
                "unchanged": "13 protected tests; model/context/sampling/budgets/scope/high risk; no additional source authority",
                "explorer": "Not invoked; already located. No full E/C/R credit.",
                "promotion": "Benchmark-only; no compatibility preflight or synthetic success credit",
            },
        )
    compat.prepare(arm)


def run(arm):
    root = BASE / arm
    snapshot = compat.SNAPSHOT
    verify_hashes(snapshot, read(snapshot / "freeze.json")["files"])
    argv = [
        str(compat.trial.PYTHON),
        "-B",
        str(
            KIT
            / "benchmarks"
            / (
                TRANSPORTS.get(
                    arm,
                    "coder_native_history_adapter.py"
                    if arm.startswith("history")
                    else "coder_native_block_adapter.py",
                )
            )
        ),
        "--snapshot",
        str(snapshot),
        "--packet",
        str(root / ".agent/compat-packet.json"),
        "--config",
        str(root / ".agent/compat-config.json"),
        "--report",
        str(root / ".agent/coder.json"),
    ]
    result = command(root, argv, timeout=1500)
    write(root / ".agent/coder-invocation.json", result)
    report = read(root / ".agent/coder.json")
    if result["exit"] == 0 and report["status"] == "ready_for_review":
        spec = importlib.util.spec_from_file_location(
            "native_history_unit", snapshot / ".local-agents/local-unit.py"
        )
        unit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unit)
        identity = unit.verify_handoff(root, report)
        write(
            root / ".agent/review-request.json",
            {
                "schema_version": 1,
                **identity,
                "review_id": identity["run_id"] + "-review",
            },
        )
        reviewer = command(
            root,
            [
                str(compat.trial.PYTHON),
                "-B",
                str(snapshot / ".local-agents/local-review.py"),
                "--request",
                str(root / ".agent/review-request.json"),
                "--config",
                str(root / ".agent/compat-config.json"),
                "--report",
                str(root / ".agent/reviewer.json"),
            ],
            timeout=900,
        )
        write(root / ".agent/reviewer-invocation.json", reviewer)
    print(
        {
            "arm": arm,
            "coder_status": report["status"],
            "seconds": result["seconds"],
            "primary_acceptance": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, required=True)
    args = parser.parse_args()
    {"prepare": prepare, "run": run}[args.action](args.arm)
