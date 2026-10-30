"""Prospective actual-archive evidence-handle control, including real negative."""

import argparse
import importlib.util

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "tool-reviewer-catalog-1"
SNAPSHOT = WORK / "continuation-weekly30-baseline-1"
ARTIFACTS = {
    "clean": (WORK / "tool-plain-result-2/fresh-1", "coder.json", "plain-config.json"),
    "hidden": (WORK / "tool-native-nudge-1/fresh-2", "coder.json", "nudge-config.json"),
}
ARMS = ("clean-control-1", "clean-catalog-1", "hidden-catalog-1", "hidden-control-1")
ADAPTERS = (
    "reviewer_sampling_probe_adapter.py",
    "reviewer_evidence_catalog_adapter.py",
    "reviewer_catalog_trial_adapter.py",
)


def register():
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    write(
        BASE / "registration.json",
        {
            "arms": ARMS,
            "weekly_ceiling": 30,
            "axis": "Citation transport only: original ranges versus IDs derived from actual read ledger, each <=20 contiguous lines; no source auto-read, clamping, fabricated quote or semantic decision",
            "fixed": "Same actual immutable eligible Coder archives, scope, inputs, model/context/temp1.0/sampling/output/turn/error/deadline budgets and original acceptance gates",
            "expected": "Clean may pass after real review. Hidden actual plain-result and extra-timer violations must not pass. Protocol failure is not successful defect detection.",
            "credit": "Reviewer-only prospective control; no Coder/Explorer/Coordinator or savings credit. No global promotion before semantic negative and regression qualification.",
            "files": {
                name: digest(KIT / "benchmarks" / name)
                for name in (*ADAPTERS, "tool_reviewer_catalog_trial.py")
            },
        },
    )


def prepare(arm):
    kind = arm.split("-")[0]
    root, coder, config_name = ARTIFACTS[kind]
    report = read(root / ".agent" / coder)
    if report["status"] != "ready_for_review":
        raise ValueError("actual eligible Coder archive required")
    spec = importlib.util.spec_from_file_location(
        "catalog_trial_unit", SNAPSHOT / ".local-agents/local-unit.py"
    )
    unit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unit)
    identity = unit.verify_handoff(root, report)
    write(
        BASE / (arm + ".request.json"),
        {"schema_version": 1, **identity, "review_id": "catalog-" + arm},
    )
    config = read(root / ".agent" / config_name)
    if config["reviewer_temperature"] != 1.0:
        raise ValueError("fixed temperature drift")
    write(BASE / (arm + ".config.json"), config)
    write(
        BASE / (arm + ".inputs.json"),
        {
            "source_sha256": digest(root / TARGET),
            "files": {
                name: digest(BASE / name)
                for name in (arm + ".request.json", arm + ".config.json")
            },
        },
    )


def run(arm):
    root = ARTIFACTS[arm.split("-")[0]][0]
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(KIT / "benchmarks", read(BASE / "registration.json")["files"])
    inputs = read(BASE / (arm + ".inputs.json"))
    verify_hashes(root, {TARGET: inputs["source_sha256"]})
    verify_hashes(BASE, inputs["files"])
    adapter = (
        "reviewer_catalog_trial_adapter.py"
        if "catalog" in arm
        else "reviewer_sampling_probe_adapter.py"
    )
    invoked = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks" / adapter),
            "--snapshot",
            str(SNAPSHOT),
            "--request",
            str(BASE / (arm + ".request.json")),
            "--config",
            str(BASE / (arm + ".config.json")),
            "--report",
            str(BASE / (arm + ".report.json")),
        ],
        timeout=900,
    )
    write(BASE / (arm + ".invocation.json"), invoked)
    print(
        {
            "arm": arm,
            "decision": read(BASE / (arm + ".report.json"))["decision"],
            "seconds": invoked["seconds"],
            "primary_acceptance": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    if args.action == "register":
        register()
    else:
        {"prepare": prepare, "run": run}[args.action](args.arm)
