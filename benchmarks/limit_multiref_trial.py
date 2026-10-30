"""New immutable candidate: separate prefetch evidence and bounded multi-span review."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, freeze, write

trial = recipe.trial
trial.BASE = WORK / "limit-multiref-1"
trial.SNAPSHOT = WORK / "limit-multiref-runtime-1"
trial.ARMS = ("semantic-multiref-1", "semantic-multiref-2", "semantic-multiref-3")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        print(freeze(trial.SNAPSHOT.name))
    elif args.action == "prepare":
        trial.prepare(args.arm, clean_start=True)
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "changed": "Runtime-prefetched edit evidence does not consume explicit read budget; Reviewer supports up to three separately verified bounded source spans",
                    "comparison": "Same clean baseline, executable advisory recipe, models and normal 4096 output budgets",
                    "credit": "Assisted algorithm task, no unaided or cloud-saving claim",
                    "release_gate": "3/3 independent complete units plus held-out transfer and independent Primary integration review",
                },
            )
    else:
        trial.run(args.arm)
