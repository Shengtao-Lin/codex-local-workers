"""Paired post-edit evidence experiment; one changed axis, normal budgets."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, freeze, write

trial = recipe.trial
trial.BASE = WORK / "limit-echo-1"
trial.SNAPSHOT = WORK / "limit-echo-runtime-1"
trial.ARMS = (
    "semantic-control-1",
    "semantic-echo-1",
    "semantic-echo-2",
    "semantic-control-2",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        print(freeze(trial.SNAPSHOT.name))
    elif args.action == "prepare":
        trial.prepare(
            args.arm,
            clean_start=True,
            config_overrides={
                "coder_post_edit_source_echo": "-echo-" in args.arm,
            },
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms_in_order": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "comparison": "Fresh clean source; same recipe, models, 4096 output budgets, latest frozen runtime",
                    "changed_axis": "Actual bounded post-edit source echo off/on; plan/diverse-failures/native-history remain off",
                    "credit": "Primary recipe is assistance; no unaided coding/cloud-saving claim",
                    "release_gate": "Paired improvement must be followed by held-out independent complete-chain qualification",
                },
            )
    else:
        trial.run(args.arm)
