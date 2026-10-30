"""New immutable cohort after observed staged review missed its final report."""

import argparse

import tool_reviewer_staged_trial as trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes
from tool_awaitable_trial import TARGET

BASE = WORK / "tool-reviewer-staged-final-2"


def configure():
    trial.BASE = BASE
    trial.ADAPTER = "reviewer_staged_final_gate_adapter.py"


def register():
    verify_hashes(trial.SNAPSHOT, read(trial.SNAPSHOT / "freeze.json")["files"])
    write(
        BASE / "registration.json",
        {
            "arms": trial.ARMS,
            "weekly_ceiling": 30,
            "axis": "Coherent staged assessment plus explicit final-only phase and stage-consistent instructions, versus monolithic report. Common required-native; no semantic examples.",
            "unchanged": "Same actual immutable Coder archives, protected tests, models, sampling, contexts, risk, total budgets and original final gates; one resident model.",
            "expected": "Actual clean must receive valid review; hidden ordinary mapping and separate timer defects must be causally rejected. Invalid reports are not detections.",
            "credit": "Read-only Reviewer qualification, not new Coder/Explorer/Coordinator success or savings. Provisional assessments never authorize acceptance.",
            "limitations": "Package comparison, not isolation of final-only versus prompt consistency. First staged cohort stopped after mechanical non-finalization; old failure retained. Required reads/search/approved executions must complete before final-only phase, and final rework/escalate stay legal.",
            "files": {
                name: digest(KIT / "benchmarks" / name)
                for name in (
                    "tool_reviewer_staged_final_trial.py",
                    "tool_reviewer_staged_trial.py",
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
        {"schema_version": 1, **identity, "review_id": "staged-final-2-" + arm},
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
