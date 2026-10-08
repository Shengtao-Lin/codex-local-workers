"""Faithful scripted-client metadata; preserve earlier fixture diagnostic failures."""

import argparse
import json
from pathlib import Path

import coordinator_failure_recovery as original
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-failure-recovery-3"


def configure():
    original.BASE = BASE
    prepare = original.mixed.prepare

    def fresh(case, repetition, config, batch, suite="v1"):
        return prepare(
            case, repetition, config, batch.replace("failure1-", "failure2-"), suite
        )

    original.mixed.prepare = fresh
    loader = original.load_worker

    def load(snapshot):
        worker = loader(snapshot)
        runtime = worker.WorkerRuntime

        class ContextualRuntime(runtime):
            def __init__(self, repo, packet, config, client):
                client.context_length = config["coder_context_length"]
                client.max_tokens = config["coder_max_tokens"]
                client.context_safety_margin = config["model_context_safety_margin"]
                super().__init__(repo, packet, config, client)

        worker.WorkerRuntime = ContextualRuntime
        return worker

    original.load_worker = load


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "adjudicate",
            "inject",
            "observe",
            "authorize",
            "recover",
        ),
    )
    parser.add_argument("--label", choices=("initial", "recovery"), default="initial")
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        original.prepare()
        write(
            BASE / "retry-registration.json",
            {
                "driver_sha256": digest(Path(__file__)),
                "previous_cohort": "coordinator-failure-recovery-2",
                "previous_failure": "Scripted client's missing context_length correctly rejected by budgeted runtime before any validation; not model quality or successful validation fault injection",
                "changed_axis": "Scripted client carries unchanged trusted context/max-output/margin metadata; fresh task/workspace identities. No runtime, question, contract, model or budget change",
                "model_credit_for_scripted_worker": False,
            },
        )
    else:
        if (
            digest(Path(__file__))
            != read(BASE / "retry-registration.json")["driver_sha256"]
        ):
            raise ValueError("retry driver drift")
        if args.action == "explore":
            original.explore(args.label)
        elif args.action == "adjudicate":
            original.adjudicate(args.label, args.summary)
        elif args.action == "inject":
            original.inject()
            root, _, _, packet, _ = original.context()
            archive = (
                root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
            )
            report = read(archive / "handoff.json")
            validation = report.get("validation") or {}
            junit = validation.get("focused_tests", {}).get("junit") or {}
            if (
                report["status"] != "failed"
                or junit.get("executed", 0) != 7
                or junit.get("failures", 0) < 1
            ):
                raise ValueError("real seven-test semantic validation failure required")
            write(
                root / ".agent/verified-injected-failure.json",
                {
                    "completed_sha256": digest(archive / "completed.json"),
                    "handoff_sha256": digest(archive / "handoff.json"),
                    "actual_junit": junit,
                    "local_coder_model_credit": False,
                },
            )
            print(
                json.dumps({"verified_real_validation_failure": True, "junit": junit})
            )
        elif args.action == "authorize":
            original.authorize(args.summary)
        else:
            original.step(args.action == "recover")
