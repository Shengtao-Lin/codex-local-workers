"""Matched canonical field-shape hints; runtime authority unchanged."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, freeze, write

trial = recipe.trial
trial.BASE = WORK / "limit-schema-1"
SNAPSHOT = WORK / "limit-schema-runtime-1"
trial.ARMS = (
    "semantic-old-1",
    "semantic-typed-1",
    "semantic-typed-2",
    "semantic-old-2",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    trial.SNAPSHOT = (
        SNAPSHOT
        if args.arm and "-typed-" in args.arm
        else WORK / "limit-echo-runtime-1"
    )
    if args.action == "freeze":
        print(freeze(SNAPSHOT.name))
    elif args.action == "prepare":
        trial.prepare(
            args.arm,
            clean_start=True,
            config_overrides={
                "coder_repair_focus_retention": "latest",
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
                    "changed_axis": "Coder canonical known fields typed (single-line replacement excludes newlines); Reviewer citation range fields typed",
                    "unchanged": "Runtime validators, models, tests, guidance, budgets, latest focus retention, permissions",
                    "separate_dimensions": "Coder protocol versus semantics; Reviewer only enters after actual valid Coder",
                    "credit": "Diagnostic matched cohort, not release. Recipe remains Primary assistance.",
                },
            )
    else:
        trial.run(args.arm)
