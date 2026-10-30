"""Output-budget probe; do not pretend it is an unchanged-budget comparison."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, freeze, write

trial = recipe.trial
trial.BASE = WORK / "limit-budget-1"
trial.SNAPSHOT = WORK / "limit-parts-runtime-1"
trial.ARMS = ("semantic-budget-1", "semantic-budget-2")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        print(freeze(trial.SNAPSHOT.name))
    elif args.action == "prepare":
        trial.prepare(
            args.arm, clean_start=True, config_overrides={"coder_max_tokens": 6144}
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "comparison": "Same recipe/source/tests/role models and turn/repair limits; Coder output 4096 -> 6144",
                    "changed": "Bounded output budget plus metadata-only response partition logging",
                    "credit": "Budget intervention, not normal-budget success; no production default budget change",
                },
            )
    else:
        trial.run(args.arm)
