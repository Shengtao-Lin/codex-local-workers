"""One-shot multiline transport correction with identical format preparation."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, freeze, write

trial = recipe.trial
trial.BASE = WORK / "limit-block-1"
trial.ARMS = (
    "semantic-control-1",
    "semantic-block-1",
    "semantic-block-2",
    "semantic-control-2",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    trial.SNAPSHOT = WORK / (
        "limit-block-runtime-1"
        if args.arm and "-block-" in args.arm
        else "reviewer-anchor-aware-runtime-1"
    )
    if args.action == "freeze":
        print(freeze("limit-block-runtime-1"))
    elif args.action == "prepare":
        trial.prepare(
            args.arm,
            clean_start=True,
            config_overrides={
                "autoformat_on_diff_whitespace": True,
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
                    "changed_axis": "After an observed multiline LINE rejection, remove LINE only from next composed transport allowlist",
                    "unchanged": "All validation, hash, edit scope and terminal gates; contract/recipe, formatter enabled in both arms, models and budgets",
                    "risk": "medium runtime state; no automatic edits, semantic implementation or widened authority",
                    "credit": "Guided mechanism diagnostic, separate from held-out capability qualification",
                },
            )
    else:
        trial.run(args.arm)
