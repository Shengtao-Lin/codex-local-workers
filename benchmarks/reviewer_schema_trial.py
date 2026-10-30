"""Typed citation transport recovery; preserves all source/semantic gates."""

import argparse

import limit_recovery_trial as trial
from capability_fit import WORK, write

ROOTS = {
    "fresh": WORK / "limit-fresh-1/semantic-fresh-1",
    "plan": WORK / "limit-plan-2/semantic-plan-1",
    "control": WORK / "limit-tagged-1/semantic-control-1",
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--artifact", choices=ROOTS, required=True)
    parser.add_argument(
        "--variant",
        choices=("old", "typed", "anchor-aware", "citation-repair"),
        required=True,
    )
    parser.add_argument("--repetition", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    snapshots = {
        "old": "limit-echo-runtime-1",
        "typed": "limit-schema-runtime-1",
        "anchor-aware": "reviewer-anchor-aware-runtime-1",
        "citation-repair": "limit-citation-runtime-1",
    }
    snapshot = WORK / snapshots[args.variant]
    root = ROOTS[args.artifact]
    label = f"schema-{args.variant}-r{args.repetition}"
    prefix = root / ".agent" / label
    if args.action == "prepare":
        packet = trial.read(root / ".agent/packet.json")
        config = trial.read(root / ".agent/config.json")
        config.update(
            reviewer_native_history=False,
            reviewer_native_tools=True,
            reviewer_max_tokens=4096,
        )
        write(prefix.with_suffix(".config.json"), config)
        write(
            prefix.with_suffix(".request.json"),
            {
                "schema_version": 1,
                "task_id": packet["task_id"],
                "unit_id": packet["unit_id"],
                "run_id": packet["run_id"],
                "review_id": label,
            },
        )
        write(
            prefix.with_suffix(".registration.json"),
            {
                "snapshot": str(snapshot),
                "weekly_ceiling": 23,
                "changed_axis": (
                    "After actual mixed source_ref/source_refs rejection, one-request canonical citation schema presentation; runtime still rejects mixed/unread/stale reports"
                    if args.variant == "citation-repair"
                    else "Current already-read anchor hint avoids requesting duplicate READ"
                    if args.variant == "anchor-aware"
                    else "Actual citation range schema fields versus opaque objects"
                ),
                "unchanged": "Artifact, fresh context, Muse, native transport/history, 4096 output, sampling, citation and acceptance gates",
                "credit": "Recovery only, not independent end-to-end Coder success",
            },
        )
    else:
        result = trial.command(
            root,
            [
                str(trial.PYTHON),
                "-B",
                str(snapshot / ".local-agents/local-review.py"),
                "--request",
                str(prefix.with_suffix(".request.json")),
                "--config",
                str(prefix.with_suffix(".config.json")),
                "--report",
                str(prefix.with_suffix(".report.json")),
            ],
            timeout=1500,
        )
        write(prefix.with_suffix(".invocation.json"), result)
        print(result["output"][-2000:])
