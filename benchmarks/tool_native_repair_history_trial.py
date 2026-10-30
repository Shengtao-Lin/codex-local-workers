"""Clean-fixture native-history v1/v2 comparison; no mid-cohort updates."""

import argparse

import tool_native_history_trial as trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "tool-native-history-3"
ARMS = ("control-1", "candidate-1", "candidate-2", "control-2")
ADAPTERS = [
    "native_coder_adapter.py",
    "coder_native_block_adapter.py",
    "coder_native_history_adapter.py",
    "coder_native_repair_history_adapter.py",
]


def configure():
    trial.BASE, trial.ARMS = BASE, ARMS
    trial.TRANSPORTS = {
        arm: "coder_native_repair_history_adapter.py"
        if arm.startswith("candidate")
        else "coder_native_history_adapter.py"
        for arm in ARMS
    }


def assert_fresh_inputs(root, frozen):
    target = trial.compat.trial.TARGET
    if digest(root / target) != digest(frozen / target):
        raise ValueError("fresh arm must start from identical frozen production source")
    if read(root / ".agent/compat-packet.json")["review_feedback"]:
        raise ValueError(
            "fresh arm cannot receive previous failure's focused repair feedback"
        )


def prepare(arm):
    if not read(WORK / "tool-compatibility-3/fixture-static-preflight.json")["passed"]:
        raise ValueError(
            "own frozen project's protected static checks must pass before model calls"
        )
    if not (BASE / "registration.json").exists():
        write(
            BASE / "registration.json",
            {
                "arms_in_order": list(ARMS),
                "weekly_ceiling": 23,
                "axis": "Both correlated native BLOCK history; candidate additionally correlates VALIDATE's actual adjacent REPAIR_REQUIRED payload, unchanged bytes",
                "unchanged": "v8 clean protected fixture, 13 tests, all static checks, scope/high atomic risk, models, sampling, budgets",
                "adapter_sha256": {
                    path: digest(KIT / "benchmarks" / path) for path in ADAPTERS
                },
                "credit": "Fresh C/R implementation calls, no Explorer/Coordinator or recovery credit",
            },
        )
    trial.prepare(arm)
    root = BASE / arm
    assert_fresh_inputs(root, trial.compat.FROZEN)


def run(arm):
    verify_hashes(
        KIT / "benchmarks", read(BASE / "registration.json")["adapter_sha256"]
    )
    trial.run(arm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, required=True)
    args = parser.parse_args()
    configure()
    {"prepare": prepare, "run": run}[args.action](args.arm)
