"""Matched existing repair-context retention; no new runtime behavior."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, write

trial = recipe.trial
trial.BASE = WORK / "limit-retention-1"
trial.SNAPSHOT = WORK / "limit-echo-runtime-1"
trial.ARMS = (
    "semantic-all-1",
    "semantic-latest-1",
    "semantic-latest-2",
    "semantic-all-2",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        trial.prepare(
            args.arm,
            clean_start=True,
            config_overrides={
                "coder_repair_focus_retention": "latest"
                if "-latest-" in args.arm
                else "all",
                "coder_post_edit_source_echo": False,
                "coder_diverse_failure_examples": False,
                "coder_require_implementation_plan": False,
                "reviewer_native_history": False,
            },
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms_in_order": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "changed_axis": "Existing coder_repair_focus_retention all versus latest",
                    "held_constant": "Clean frozen source, protected tests, recipe, models, native tools, budgets and runtime",
                    "qualification": "A paired diagnostic, not independent release or unaided/cloud-saving credit",
                },
            )
    else:
        trial.run(args.arm)
