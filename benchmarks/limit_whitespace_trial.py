"""Matched opt-in trusted formatting experiment, not weaker acceptance."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, write

trial = recipe.trial
trial.BASE = WORK / "limit-whitespace-1"
trial.SNAPSHOT = WORK / "reviewer-anchor-aware-runtime-1"
trial.ARMS = (
    "semantic-control-1",
    "semantic-format-1",
    "semantic-format-2",
    "semantic-control-2",
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
                "autoformat_on_diff_whitespace": "-format-" in args.arm,
                "coder_diverse_failure_examples": False,
                "coder_typed_action_arguments": False,
                "coder_repair_focus_retention": "latest",
                "coder_post_edit_source_echo": False,
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
                    "changed_axis": "Existing opt-in trusted formatter before trailing-whitespace gate",
                    "unchanged": "Protected tests, contract/recipe, clean baseline, models, output/context budgets and all acceptance gates",
                    "hypothesis": "Mechanical whitespace failures currently prevent functional evidence; formatting should expose rather than mask semantic failures",
                    "risk": "medium: trusted execution on authorized changed Python paths, protected-input hash checks and complete revalidation",
                    "credit": "Guided diagnostic; any individual or recovered acceptance remains separate from fresh qualification",
                },
            )
    else:
        trial.run(args.arm)
