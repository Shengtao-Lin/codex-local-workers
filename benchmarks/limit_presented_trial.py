"""Normal-budget recipe after prefetched source read is registered as evidence."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, freeze, write

trial = recipe.trial
trial.BASE = WORK / "limit-presented-1"
trial.SNAPSHOT = WORK / "limit-presented-runtime-1"
trial.ARMS = ("semantic-presented-1", "semantic-presented-2", "semantic-presented-3")

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
                    "comparison": "Same clean source, executable recipe, tests and normal 4096 output budget as limit-recipe-1",
                    "changed": "Fully displayed current source in repair prefetch is registered as read evidence; stale/truncated lines remain denied",
                    "release_gate": "3/3 independent units plus Reviewer and Primary integration; no Primary implementation",
                    "pending": "Reviewer mode probes remain separate recovery evidence",
                },
            )
    else:
        trial.run(args.arm)
