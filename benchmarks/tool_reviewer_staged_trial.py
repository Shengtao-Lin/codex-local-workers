"""Matched provisional-obligation Reviewer protocol; semantic negatives retained."""

import argparse
import importlib.util

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "tool-reviewer-staged-1"
SNAPSHOT = WORK / "reviewer-single-ref-runtime-15"
ARTIFACTS = {
    "clean": (WORK / "tool-plain-result-3/fresh-1", "coder.json", "plain-config.json"),
    "hidden": (WORK / "tool-native-nudge-1/fresh-2", "coder.json", "nudge-config.json"),
}
ARMS = (
    "clean-control-1",
    "clean-candidate-1",
    "clean-candidate-2",
    "clean-control-2",
    "hidden-control-1",
    "hidden-candidate-1",
    "hidden-candidate-2",
    "hidden-control-2",
)
ADAPTER = "reviewer_staged_assessment_adapter.py"


def unit_module():
    spec = importlib.util.spec_from_file_location(
        "sampling_trial_unit", SNAPSHOT / ".local-agents/local-unit.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def register():
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    write(
        BASE / "registration.json",
        {
            "arms": ARMS,
            "weekly_ceiling": 30,
            "axis": "One coherent staged-review protocol: provisional source-backed obligation assessments then original full final gates, versus monolithic report; common required-native transport, no semantic examples",
            "unchanged": "Same actual immutable Coder archives, source, tests, model, context, temperature 1.0, sampling, turn/error/time budgets and all final acceptance gates; one model resident. REPORT protocol schema differs only for the registered staged axis.",
            "expected": "Clean v12 actual correct implementation may pass; hidden actual v10 plain mapping and extra deadline defects must not pass. Protocol failure is not successful defect detection.",
            "credit": "Independent read-only matched Reviewer qualification, no new Coder/Explorer/Coordinator or savings credit; repeated actual hidden passes remain false passes",
            "limitations": "Provisional records never authorize acceptance or split Coder atomic unit. Same original final obligations, source/version/ordering/check gates and total budgets. No global promotion before real positive/negative qualification.",
            "files": {
                name: digest(KIT / "benchmarks" / name)
                for name in (
                    ADAPTER,
                    "reviewer_sampling_probe_adapter.py",
                    "reviewer_required_tool_adapter.py",
                    "tool_reviewer_staged_trial.py",
                )
            },
        },
    )


def prepare(arm):
    kind = arm.split("-")[0]
    root, coder, config_name = ARTIFACTS[kind]
    report = read(root / ".agent" / coder)
    if report["status"] != "ready_for_review":
        raise ValueError("actual eligible Coder archive required")
    identity = unit_module().verify_handoff(root, report)
    write(
        BASE / (arm + ".request.json"),
        {"schema_version": 1, **identity, "review_id": "staged-" + arm},
    )
    config = read(root / ".agent" / config_name)
    if config["reviewer_temperature"] != 1.0:
        raise ValueError("registered temperature baseline drift")
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
    invoked = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(
                KIT
                / "benchmarks"
                / (
                    ADAPTER
                    if "candidate" in arm
                    else "reviewer_required_tool_adapter.py"
                )
            ),
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
