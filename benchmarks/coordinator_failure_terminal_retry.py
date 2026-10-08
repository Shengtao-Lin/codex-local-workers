"""Explicit scripted transport termination after real validation, not fake success."""

import argparse
from pathlib import Path

import coordinator_failure_context_retry as retry
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-failure-recovery-4"


def configure():
    retry.BASE = BASE
    prepare = retry.original.mixed.prepare

    def fresh(case, repetition, config, batch, suite="v1"):
        return prepare(
            case, repetition, config, batch.replace("failure2-", "failure3-"), suite
        )

    retry.original.mixed.prepare = fresh
    retry.configure()
    loader = retry.original.load_worker

    def load(snapshot):
        worker = loader(snapshot)
        runtime = worker.WorkerRuntime

        class TerminalRuntime(runtime):
            def __init__(self, repo, packet, config, client):
                super().__init__(repo, packet, config, client)
                complete = client.complete

                def bounded_complete(messages):
                    try:
                        return complete(messages)
                    except StopIteration as exc:
                        raise worker.WorkerError(
                            "diagnostic scripted transport ends after failed validation; not a local LLM failure"
                        ) from exc

                client.complete = bounded_complete

        worker.WorkerRuntime = TerminalRuntime
        return worker

    retry.original.load_worker = load


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
        retry.original.prepare()
        write(
            BASE / "terminal-registration.json",
            {
                "driver_sha256": digest(Path(__file__)),
                "context_driver_sha256": digest(Path(retry.__file__)),
                "previous_incomplete_cohort": "coordinator-failure-recovery-3",
                "observed_gate": "Actual seven-test validation failed; required-edit gate correctly rejected repeated VALIDATE. Script responses exhausted without terminal archive; prior partial trace retained, not granted recovery or success.",
                "changed_axis": "Script exhaustion becomes explicit WorkerError transport termination so actual runtime owns terminal failed record. No source/test/runtime/model/budget changes",
                "scripted_worker_local_llm_credit": False,
            },
        )
    else:
        registration = read(BASE / "terminal-registration.json")
        if (
            digest(Path(__file__)) != registration["driver_sha256"]
            or digest(Path(retry.__file__)) != registration["context_driver_sha256"]
        ):
            raise ValueError("terminal fixture driver drift")
        if args.action == "explore":
            retry.original.explore(args.label)
        elif args.action == "adjudicate":
            retry.original.adjudicate(args.label, args.summary)
        elif args.action == "inject":
            retry.original.inject()
            root, _, _, packet, _ = retry.original.context()
            archive = (
                root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
            )
            report = read(archive / "handoff.json")
            junit = (report.get("validation") or {}).get("focused_tests", {}).get(
                "junit"
            ) or {}
            if (
                read(archive / "completed.json")["status"] != "failed"
                or junit.get("executed") != 7
                or junit.get("failures", 0) < 1
            ):
                raise ValueError(
                    "real terminal failure and executed failed tests required"
                )
            write(
                root / ".agent/verified-injected-failure.json",
                {
                    "completed_sha256": digest(archive / "completed.json"),
                    "handoff_sha256": digest(archive / "handoff.json"),
                    "actual_junit": junit,
                    "local_coder_model_credit": False,
                    "failure_kind": "real semantic validation failure followed by scripted transport termination",
                },
            )
        elif args.action == "authorize":
            retry.original.authorize(args.summary)
        else:
            retry.original.step(args.action == "recover")
