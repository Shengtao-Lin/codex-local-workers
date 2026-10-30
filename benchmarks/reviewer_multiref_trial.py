"""Bounded multi-span recovery on the same independently validated Coder archive."""

import argparse

import reviewer_mode_trial as modes
from capability_fit import WORK, write

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--mode", choices=("native", "json"), required=True)
    args = parser.parse_args()
    snapshot = WORK / "limit-multiref-runtime-1"
    prefix = modes.ROOT / ".agent" / ("multiref-" + args.mode)
    if args.action == "prepare":
        config = modes.trial.read(modes.ROOT / ".agent/config.json")
        config.update(
            reviewer_native_tools=args.mode == "native", reviewer_max_tokens=4096
        )
        write(prefix.with_suffix(".config.json"), config)
        write(
            prefix.with_suffix(".request.json"),
            {
                "schema_version": 1,
                "task_id": "limit-fresh-1-semantic-fresh-1",
                "unit_id": "limit-selection",
                "run_id": "limit-fresh-1-semantic-fresh-1-a1",
                "review_id": "multiref-" + args.mode,
            },
        )
        write(
            prefix.with_suffix(".registration.json"),
            {
                "snapshot": str(snapshot),
                "native": args.mode == "native",
                "output_budget": 4096,
                "weekly_ceiling": 23,
                "credit": "Reviewer recovery only; not independent Coder/full-chain success",
            },
        )
    else:
        result = modes.trial.command(
            modes.ROOT,
            [
                str(modes.trial.PYTHON),
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
        print(result["output"][-3000:])
