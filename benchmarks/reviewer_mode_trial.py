"""Protocol/budget probes against one immutable validated Coder draft."""

import argparse

import limit_recovery_trial as trial
from capability_fit import WORK, write

ROOT = WORK / "limit-fresh-1/semantic-fresh-1"
SNAPSHOT = WORK / "limit-parts-runtime-1"
MODES = {"json-4096": (False, 4096), "native-6144": (True, 6144)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--mode", choices=MODES, required=True)
    args = parser.parse_args()
    prefix = ROOT / ".agent" / ("mode-" + args.mode)
    native, budget = MODES[args.mode]
    if args.action == "prepare":
        config = trial.read(ROOT / ".agent/config.json")
        config.update(reviewer_native_tools=native, reviewer_max_tokens=budget)
        write(prefix.with_suffix(".config.json"), config)
        write(
            prefix.with_suffix(".request.json"),
            {
                "schema_version": 1,
                "task_id": "limit-fresh-1-semantic-fresh-1",
                "unit_id": "limit-selection",
                "run_id": "limit-fresh-1-semantic-fresh-1-a1",
                "review_id": "mode-" + args.mode,
            },
        )
        write(
            prefix.with_suffix(".registration.json"),
            {
                "native": native,
                "output_budget": budget,
                "model": config["reviewer_model"],
                "context": config["reviewer_context_length"],
                "snapshot": str(SNAPSHOT),
                "weekly_ceiling": 23,
                "credit": "Same validated Coder artifact; reviewer recovery, not independent full-chain success",
            },
        )
    else:
        result = trial.command(
            ROOT,
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
        print(result["output"][-3000:])
