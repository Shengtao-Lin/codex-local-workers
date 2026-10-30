"""Compare fresh optimization with recovery of an actual failed model draft."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, write

trial = recipe.trial
trial.BASE = WORK / "limit-draft-1"
trial.SNAPSHOT = WORK / "limit-prepass-runtime-2"
trial.ARMS = (
    "semantic-fresh-1",
    "semantic-draft-1",
    "semantic-draft-2",
    "semantic-fresh-2",
)
SEED = WORK / "limit-sampling-1/semantic-author-1" / trial.COMMON


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        trial.prepare(
            args.arm,
            clean_start=True,
            start_source=SEED if "-draft-" in args.arm else None,
            config_overrides={
                "autoformat_on_diff_whitespace": True,
                "coder_diverse_failure_examples": False,
                "coder_typed_action_arguments": False,
                "coder_reset_failed_repair_context": False,
                "coder_repair_focus_retention": "latest",
                "coder_post_edit_source_echo": False,
                "coder_require_implementation_plan": False,
                "reviewer_native_history": False,
                "reviewer_prepass_challenge": False,
                "coder_temperature": 0.1,
                "coder_top_p": 0.9,
                "coder_top_k": 40,
                "coder_repeat_penalty": 1.0,
            },
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms_in_order": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "draft_origin": str(SEED),
                    "draft_sha256": trial.digest(SEED),
                    "changed_axis": "Initial source state: legacy full sort versus an immutable actual failed model draft with incorrect two-field selection key and an optional count static issue",
                    "unchanged": "All five contracts, protected tests, model, current sampling, runtime, recipe, budgets, scope and automatic Reviewer gate",
                    "question": "Can the bounded worker repair a near-complete draft more reliably than it can derive the complete optimization? No exact patch is supplied.",
                    "credit": "Draft arms are diagnostic recovery in fresh isolated calls, NOT clean-start optimization, inherited archive reuse, task-level retry success, or Primary-free algorithm discovery. Old failures remain failures.",
                    "stop": "Four registered calls only; not repeat until pass. Any success requires independent closure and Primary review.",
                },
            )
    else:
        trial.run(args.arm)
