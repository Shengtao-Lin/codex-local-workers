"""Matched fresh repair-context diagnostic; original archives remain complete."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, write

trial = recipe.trial
trial.BASE = WORK / "limit-reset-1"
trial.SNAPSHOT = WORK / "limit-prepass-runtime-1"
trial.ARMS = (
    "semantic-control-1",
    "semantic-reset-1",
    "semantic-reset-2",
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
                "coder_reset_failed_repair_context": "-reset-" in args.arm,
                "autoformat_on_diff_whitespace": True,
                "coder_diverse_failure_examples": False,
                "coder_typed_action_arguments": False,
                "coder_repair_focus_retention": "latest",
                "coder_post_edit_source_echo": False,
                "coder_require_implementation_plan": False,
                "reviewer_native_history": False,
                "reviewer_prepass_challenge": False,
            },
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms_in_order": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "changed_axis": "Failed post-edit validation with current prefetched source resets model history to system/packet/current repair evidence",
                    "unchanged": "Runtime scope/read/hash ledgers, full immutable validation history, repair/turn/deadline budgets, protected tests, recipe, models, formatter and one-shot LINE correction",
                    "hypothesis": "Removing model-authored wrong algorithms and obsolete drafts may reduce anchoring without supplying a solution",
                    "risk": "medium state/context; baseline is not a repair and no proof or acceptance is synthesized",
                    "credit": "Guided mechanism diagnostic, not unaided feature completion or release qualification",
                },
            )
    else:
        trial.run(args.arm)
