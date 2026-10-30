"""Native tool-history-only recovery probe; no independent chain credit."""

import argparse

import limit_recovery_trial as trial
from capability_fit import WORK, freeze, write

SNAPSHOT = WORK / "review-history-runtime-1"
ROOTS = {
    "fresh": WORK / "limit-fresh-1/semantic-fresh-1",
    "plan": WORK / "limit-plan-2/semantic-plan-1",
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--artifact", choices=ROOTS, default="fresh")
    parser.add_argument("--repetition", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    root = ROOTS[args.artifact]
    label = "history-r" + str(args.repetition)
    prefix = root / ".agent" / label
    if args.action == "freeze":
        print(freeze(SNAPSHOT.name))
    elif args.action == "prepare":
        packet = trial.read(root / ".agent/packet.json")
        config = trial.read(root / ".agent/config.json")
        config.update(
            reviewer_native_history=True,
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
                "snapshot": str(SNAPSHOT),
                "weekly_ceiling": 23,
                "changed": "Successful native calls retain assistant.tool_calls plus correlated role=tool observations. Invalid REPORT remains redacted.",
                "unchanged": "Muse, 4096 budget, sampling, contexts, artifact, contract and citation gates",
                "credit": "Reviewer recovery only; not independent Coder/full-chain success",
            },
        )
    else:
        result = trial.command(
            root,
            [
                str(trial.PYTHON),
                "-B",
                str(SNAPSHOT / ".local-agents/local-review.py"),
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
