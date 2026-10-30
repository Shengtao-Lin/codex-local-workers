"""Matched exploratory candidate: one local pre-edit contract self-check."""

import argparse

import limit_recipe_trial as recipe
from capability_fit import WORK, freeze, write

trial = recipe.trial
trial.BASE = WORK / "limit-plan-1"
trial.SNAPSHOT = WORK / "limit-plan-runtime-1"
trial.ARMS = ("semantic-plan-1", "semantic-plan-2", "semantic-plan-3")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    parser.add_argument("--candidate", choices=("1", "2"), default="1")
    args = parser.parse_args()
    if args.candidate == "2":
        trial.BASE = WORK / "limit-plan-2"
        trial.SNAPSHOT = WORK / "limit-plan-runtime-2"
    if args.action == "freeze":
        print(freeze(trial.SNAPSHOT.name))
    elif args.action == "prepare":
        trial.prepare(
            args.arm,
            clean_start=True,
            config_overrides={"coder_require_implementation_plan": True},
        )
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "comparison": "limit-multiref-1; unchanged models, 4096 output budget, frozen source/tests and algorithm guidance",
                    "changed": "Pre-edit local PLAN_IMPLEMENTATION with all owned contracts, current source/test reads and baseline validation",
                    "candidate": args.candidate,
                    "candidate_1_exclusion": "Primary experiment omitted PLAN_IMPLEMENTATION from transport schema. Preserved as implementation defect, not worker capability failure.",
                    "credit": "Plan is untrusted; assistance costs and all failures retained",
                    "release_gate": "3/3 independent complete units, then held-out transfer and Primary integration",
                },
            )
    else:
        trial.run(args.arm)
