"""Separate registered release candidate with fresh repair and anchor diagnosis."""

import argparse

import limit_shaped_trial as shaped
from capability_fit import WORK, freeze, write

trial = shaped.trial
trial.BASE = WORK / "limit-release-1"
trial.SNAPSHOT = WORK / "limit-release-runtime-1"
trial.ARMS = ("semantic-release-1", "semantic-release-2", "semantic-release-3")

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
                    "comparison": "Original algorithm baseline and same advisory shaped example",
                    "changed": "Localized/fresh Pyright recovery and bounded Reviewer anchor-repair hint",
                    "release_gate": "3/3 clean-start units with deterministic gates, independent Reviewer and Primary integration acceptance",
                    "failed_older_cohorts": "Never overwritten or relabelled",
                    "cloud_cost_savings": "Not proven; Primary authored tests and guidance remain intervention cost",
                },
            )
    else:
        trial.run(args.arm)
