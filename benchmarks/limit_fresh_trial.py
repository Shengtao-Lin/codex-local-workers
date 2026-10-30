"""Version-bound recovery after removing obsolete pre-format source observations."""

import argparse

import limit_focus_trial as focused
from capability_fit import WORK, freeze, write

trial = focused.trial
trial.BASE = WORK / "limit-fresh-1"
trial.SNAPSHOT = WORK / "limit-fresh-runtime-1"
trial.ARMS = ("semantic-fresh-1", "semantic-fresh-2")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        print(freeze(trial.SNAPSHOT.name))
    elif args.action == "prepare":
        trial.prepare(args.arm, clean_start=True, start_source=focused.static.START)
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "comparison": "Same source, guidance, tests, models and budgets as limit-focus-1",
                    "changed": "Pyright repair prompt keeps system/contract and only current repair evidence",
                    "credit": "Static recovery only, not original algorithm task success",
                },
            )
    else:
        trial.run(args.arm)
