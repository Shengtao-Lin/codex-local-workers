"""Preserve different actual failure families in bounded repair evidence."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, write

trial = recipe.trial
trial.BASE = WORK / "limit-failure-1"
trial.SNAPSHOT = WORK / "reviewer-anchor-aware-runtime-1"
trial.ARMS = (
    "semantic-control-1",
    "semantic-diverse-1",
    "semantic-diverse-2",
    "semantic-control-2",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS, required=True)
    parser.add_argument("--formatted", action="store_true")
    args = parser.parse_args()
    if args.formatted:
        trial.BASE = WORK / "limit-failure-2"
        trial.SNAPSHOT = WORK / "limit-prepass-runtime-2"
    if args.action == "prepare":
        trial.prepare(
            args.arm,
            clean_start=True,
            config_overrides={
                "coder_diverse_failure_examples": "-diverse-" in args.arm,
                "coder_typed_action_arguments": False,
                "coder_repair_focus_retention": "latest",
                "coder_post_edit_source_echo": False,
                "coder_require_implementation_plan": False,
                "reviewer_native_history": False,
                "autoformat_on_diff_whitespace": args.formatted,
                "coder_reset_failed_repair_context": False,
                "reviewer_prepass_challenge": False,
            },
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms_in_order": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "changed_axis": "First-eight JUnit failures versus one representative per actual test-function family before bounded fill",
                    "unchanged": "Protected full JUnit, source/contract/recipe, models, budgets, latest focus, baseline semantics; formatter and one-shot LINE correction identical in both arms",
                    "followup": (
                        "Earlier cohort never reached post-edit pytest due to whitespace; this cohort enables trusted formatting in both arms to expose the intended axis"
                        if args.formatted
                        else None
                    ),
                    "gate": "No fabricated expected values or inferred symbols; only existing messages/locations; no unaided/release credit from this diagnostic",
                },
            )
    else:
        trial.run(args.arm)
