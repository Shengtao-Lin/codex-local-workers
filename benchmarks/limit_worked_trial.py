"""Different hypothesis: clean original source plus worked non-target heap example."""

import argparse

import limit_recovery_v3 as version
from capability_fit import WORK, write

trial = version.trial
trial.BASE = WORK / "limit-worked-1"
trial.ARMS = ("semantic-clean-1", "semantic-clean-2")
trial.EXAMPLE = (
    "Advisory worked example for unrelated score rows, not target source: "
    "rows=[(7,0,'red'),(7,1,'blue'),(7,2,'green')]. "
    "heapq.nsmallest(2,rows,key=lambda row: row[:2]) gives red,blue; "
    "heapq.nlargest(2,rows,key=lambda row: row[:2]) gives green,blue. "
    "The position is positive for both helpers; descending selection itself reverses it. "
    "Keep the payload outside the comparison key. Build positions with enumerate once, not list.index. "
    "Here target records have two primary keys, so a decoration with timestamp,identity,position,payload "
    "has FOUR fields: update both key extraction and payload extraction consistently. "
    "Precompute timestamp then identity for every record before invoking any heap helper. "
    "Before passing policy.limit to a helper requiring int, narrow its optional type using the "
    "existing validated-policy invariant. Preserve all/random/percentage unchanged. "
    "Any alternate implementation satisfying protected equivalence/cost/type checks remains allowed."
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", required=True, choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "prepare":
        trial.prepare(args.arm, clean_start=True)
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms": list(trial.ARMS),
                    "hypothesis": "Clean source and worked structural guidance",
                    "not_matched_to_recovery_cohort": "Both starting source and guidance changed",
                    "same_models_budgets_tests": True,
                    "weekly_ceiling": 15,
                    "stop": "Two bounded implementations, no repeated unchanged failure recovery",
                    "primary_contribution": "Algorithm pattern/example and protected tests, no target implementation edit",
                },
            )
    else:
        if not trial.read(WORK / "limit-recovery-3/positive-preflight.json")["passed"]:
            raise ValueError("fully passing positive control required")
        trial.run(args.arm)
