"""New independent reviews after a reproduced correction-retention runtime fix."""

import argparse
import importlib.util

from capability_fit import KIT, WORK, freeze, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "tool-reviewer-retention-1"
SNAPSHOT = WORK / "tool-report-retention-runtime-9"
ARTIFACTS = {
    "clean": (
        WORK / "tool-context-scope-1/fresh-1",
        "coder-a2.json",
        "scope-rework-config-a2.json",
    ),
    "hidden": (WORK / "tool-native-block-1/control-1", "coder.json", "config.json"),
}


def register():
    if not SNAPSHOT.exists():
        freeze(SNAPSHOT.name)
    write(
        BASE / "registration.json",
        {
            "arms": ["clean", "hidden"],
            "weekly_ceiling": 23,
            "fix": "Retain latest trusted report correction across duplicate-read/context compaction; retire after validated report, including deferred execution",
            "models": "Same Muse/config/context/sampling/budget, single residency",
            "input": "Actual eligible canonical Coder archives, unchanged code and validation input hashes; no correction of submitted model report",
            "expected": "clean may pass after source review; hidden async double-consumption must not pass, regardless of genuine citations",
            "credit": "Independent Reviewer qualification after fix; no fresh Coder, Explorer, Coordinator or savings credit; prior failures retained",
            "driver_sha256": digest(
                KIT / "benchmarks/tool_reviewer_retention_trial.py"
            ),
        },
    )


def prepare(kind):
    root, coder, configuration = ARTIFACTS[kind]
    report = read(root / ".agent" / coder)
    if report["status"] != "ready_for_review":
        raise ValueError("Actual eligible Coder archive required")
    spec = importlib.util.spec_from_file_location(
        "retention_unit", SNAPSHOT / ".local-agents/local-unit.py"
    )
    unit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unit)
    identity = unit.verify_handoff(root, report)
    request = {
        "schema_version": 1,
        **identity,
        "review_id": "retention-" + kind + "-r1",
    }
    write(BASE / (kind + ".request.json"), request)
    write(BASE / (kind + ".config.json"), read(root / ".agent" / configuration))
    write(
        BASE / (kind + ".inputs.json"),
        {
            "source_sha256": digest(root / TARGET),
            "files": {
                name: digest(BASE / name)
                for name in (kind + ".request.json", kind + ".config.json")
            },
        },
    )


def run(kind):
    root, _, _ = ARTIFACTS[kind]
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(
        KIT / "benchmarks",
        {
            "tool_reviewer_retention_trial.py": read(BASE / "registration.json")[
                "driver_sha256"
            ]
        },
    )
    inputs = read(BASE / (kind + ".inputs.json"))
    verify_hashes(root, {TARGET: inputs["source_sha256"]})
    verify_hashes(BASE, inputs["files"])
    invoked = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-review.py"),
            "--request",
            str(BASE / (kind + ".request.json")),
            "--config",
            str(BASE / (kind + ".config.json")),
            "--report",
            str(BASE / (kind + ".report.json")),
        ],
        timeout=900,
    )
    write(BASE / (kind + ".invocation.json"), invoked)
    print(
        {
            "kind": kind,
            "decision": read(BASE / (kind + ".report.json"))["decision"],
            "seconds": invoked["seconds"],
            "primary_acceptance": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--kind", choices=ARTIFACTS, default="clean")
    args = parser.parse_args()
    if args.action == "register":
        register()
    else:
        {"prepare": prepare, "run": run}[args.action](args.kind)
