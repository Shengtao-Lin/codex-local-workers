"""Explicit model-facing assessment and final-report tools, canonical gates retained."""

import argparse

import tool_reviewer_staged_trial as trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "tool-reviewer-investigation-5"


def configure():
    trial.BASE = BASE
    trial.ADAPTER = "reviewer_dependency_investigation_adapter.py"


def register():
    verify_hashes(trial.SNAPSHOT, read(trial.SNAPSHOT / "freeze.json")["files"])
    write(
        BASE / "registration.json",
        {
            "arms": trial.ARMS,
            "weekly_ceiling": 30,
            "axis": "Single-range-array staged versus monolithic report. Both require actual declared dependency investigation before final report and citation in each declared assessment regardless of status. No semantic examples or truth defaults.",
            "unchanged": "Same actual immutable Coder archives, protected tests, models, sampling, contexts, risk, total budgets and original final gates; one resident model.",
            "expected": "Actual clean must receive valid review; hidden ordinary mapping and separate timer defects must be causally rejected. Invalid reports are not detections.",
            "credit": "Read-only Reviewer qualification, not new Coder/Explorer/Coordinator success or savings. Provisional assessments never authorize acceptance.",
            "limitations": "Coherent protocol package qualification, not causal comparison against incomplete prior prototypes. Every stage/finding remains untrusted and full original final gates are enforced; no semantic acceptance or budget extension. Required reads/search/execution stay available until complete.",
            "files": {
                name: digest(KIT / "benchmarks" / name)
                for name in (
                    "tool_reviewer_investigation_trial.py",
                    "tool_reviewer_staged_trial.py",
                    "reviewer_range_staged_adapter.py",
                    "reviewer_dependency_evidence_adapter.py",
                    "reviewer_dependency_investigation_adapter.py",
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
        {"schema_version": 1, **identity, "review_id": "investigation-5-" + arm},
    )
    config = read(root / ".agent" / config_name)
    config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "caller-context",
            "path": "reference/asyncio_threads.py",
            "anchors": ["copy_context", "ctx.run"],
        }
    ]
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


def run(arm):
    root = trial.ARTIFACTS[arm.split("-")[0]][0]
    verify_hashes(trial.SNAPSHOT, read(trial.SNAPSHOT / "freeze.json")["files"])
    verify_hashes(KIT / "benchmarks", read(BASE / "registration.json")["files"])
    inputs = read(BASE / (arm + ".inputs.json"))
    verify_hashes(root, {TARGET: inputs["source_sha256"]})
    verify_hashes(BASE, inputs["files"])
    adapter = trial.ADAPTER
    invoked = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks" / adapter),
            "--snapshot",
            str(trial.SNAPSHOT),
            *(["--staged"] if "candidate" in arm else []),
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
    report_path = BASE / (arm + ".report.json")
    if not report_path.exists():
        print(
            {
                "arm": arm,
                "classification": "infrastructure_missing_report",
                "seconds": invoked["seconds"],
                "exit": invoked["exit"],
                "primary_acceptance": False,
            }
        )
        return 2
    print(
        {
            "arm": arm,
            "decision": read(report_path)["decision"],
            "seconds": invoked["seconds"],
            "primary_acceptance": False,
        }
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS, default=trial.ARMS[0])
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        if args.action == "run":
            raise SystemExit(run(args.arm))
        prepare(args.arm)
