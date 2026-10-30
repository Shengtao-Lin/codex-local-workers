"""Same shaped clean-start task after the optional -B formatter recognition fix."""

import argparse

import limit_shaped_trial as shaped
from capability_fit import WORK, freeze, write

trial = shaped.trial
trial.BASE = WORK / "limit-format-1"
trial.SNAPSHOT = WORK / "limit-format-runtime-1"
trial.ARMS = ("semantic-format-1", "semantic-format-2")

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
                    "comparison": "Same clean source, shaped guidance, tests, models and budgets as limit-shaped-1",
                    "changed": "Frozen runtime recognizes optional Python -B in trusted Ruff format command",
                    "weekly_ceiling": 15,
                    "stop": "Two bounded experiments or weekly used 15%; no unchanged production retry",
                    "snapshot": str(trial.SNAPSHOT),
                    "primary_contribution": "Protected tests and advisory shape-matched algorithm example; no source answer in worker scope",
                },
            )
    else:
        if not trial.read(WORK / "limit-recovery-3/positive-preflight.json")["passed"]:
            raise ValueError("positive control required")
        trial.run(args.arm)
