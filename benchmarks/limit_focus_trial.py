"""Registered static recovery under localized Pyright focus; immutable older cohorts."""

import argparse

import limit_static_trial as static
from capability_fit import WORK, freeze, write

trial = static.trial
trial.BASE = WORK / "limit-focus-1"
trial.SNAPSHOT = WORK / "limit-focus-runtime-1"
trial.ARMS = ("semantic-focus-1", "semantic-focus-2")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        print(freeze(trial.SNAPSHOT.name))
    elif args.action == "prepare":
        trial.prepare(args.arm, clean_start=True, start_source=static.START)
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "comparison": "Same initial source, tests, guidance, models and budgets as limit-static-1",
                    "changed": "Localized causal Pyright repair_focus and scoped next-action requirement",
                    "credit": "Static recovery only, not clean-start algorithm success",
                },
            )
    else:
        trial.run(args.arm)
