"""Explicit model-facing assessment and final-report tools, canonical gates retained."""

import argparse

import tool_reviewer_staged_trial as trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes
from tool_awaitable_trial import TARGET

BASE = WORK / "tool-reviewer-split-3"


def configure():
    trial.BASE = BASE
    trial.ADAPTER = "reviewer_split_staged_adapter.py"


def register():
    verify_hashes(trial.SNAPSHOT, read(trial.SNAPSHOT / "freeze.json")["files"])
    write(
        BASE / "registration.json",
        {
            "arms": trial.ARMS,
            "weekly_ceiling": 30,
            "axis": "Explicit flat ASSESS_CONTRACT and final-only REPORT model tools route to original staged canonical gates, versus monolithic report. Common required-native; no semantic examples.",
            "unchanged": "Same actual immutable Coder archives, protected tests, models, sampling, contexts, risk, total budgets and original final gates; one resident model.",
            "expected": "Actual clean must receive valid review; hidden ordinary mapping and separate timer defects must be causally rejected. Invalid reports are not detections.",
            "credit": "Read-only Reviewer qualification, not new Coder/Explorer/Coordinator success or savings. Provisional assessments never authorize acceptance.",
            "limitations": "Coherent protocol package qualification, not causal comparison against incomplete prior prototypes. Every stage/finding remains untrusted and full original final gates are enforced; no semantic acceptance or budget extension. Required reads/search/execution stay available until complete.",
            "files": {
                name: digest(KIT / "benchmarks" / name)
                for name in (
                    "tool_reviewer_split_trial.py",
                    "tool_reviewer_staged_trial.py",
                    "reviewer_split_staged_adapter.py",
                    "reviewer_staged_final_gate_adapter.py",
                    "reviewer_staged_assessment_adapter.py",
                    "reviewer_required_tool_adapter.py",
                    "reviewer_sampling_probe_adapter.py",
                )
            },
        },
    )


def prepare(arm):
    root, coder, config_name = trial.ARTIFACTS[arm.split("-")[0]]
    report = read(root / ".agent" / coder)
    if report["status"] != "ready_for_review":
        raise ValueError("actual eligible immutable Coder archive required")
    identity = trial.unit_module().verify_handoff(root, report)
    write(
        BASE / (arm + ".request.json"),
        {"schema_version": 1, **identity, "review_id": "split-3-" + arm},
    )
    config = read(root / ".agent" / config_name)
    if config["reviewer_temperature"] != 1.0:
        raise ValueError("registered current sampling changed")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS, default=trial.ARMS[0])
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        {"prepare": prepare, "run": trial.run}[args.action](args.arm)
