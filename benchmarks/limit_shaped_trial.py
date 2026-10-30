"""Shape-matched worked example after failed cross-shape transfer; no source answer."""

import argparse

import limit_worked_trial as worked
from capability_fit import WORK, write

trial = worked.trial
trial.BASE = WORK / "limit-shaped-1"
trial.ARMS = ("semantic-shaped-1", "semantic-shaped-2")
trial.EXAMPLE = (
    "Advisory shape-matched example for unrelated job ranking. A row is (priority,queue,arrival_position,job). "
    "rows=[(7,'q',0,'red'),(7,'q',1,'blue'),(7,'q',2,'green')]. "
    "heapq.nsmallest(2,rows,key=lambda row: row[:3]) returns red,blue. "
    "heapq.nlargest(2,rows,key=lambda row: row[:3]) returns green,blue. "
    "All THREE comparable fields INCLUDING positive position belong to the key; payload is field 3 (zero-based). "
    "No negative keys and no extra reverse are needed: nlargest orders the entire comparable key descending. "
    "Target analogue: (timestamp,identity,original_position,payload). Precompute it ONCE using enumerate, "
    "calling timestamp then identity once per input record before any comparison. Both selectors must "
    "include original_position, exclude payload, and extract payload consistently. No list.index, duplicate "
    "callback evaluation, datetime conversion/negation, or post-selection reverse. Narrow the optional "
    "limit to int under the validated policy invariant before heap helper calls. This is advisory; any "
    "alternative preserving every protected contract remains permitted. Validate and fix exact static diagnostics."
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
                    "hypothesis": "Match example and target tuple arity",
                    "comparison": "Same clean source, model, budget and protected tests as limit-worked-1",
                    "changed": "Advisory shape-matched example only",
                    "weekly_ceiling": 15,
                    "stop": "Two bounded experiments; no blind rework",
                    "production_work": "Original algorithm task remains not accepted; experiments separate",
                },
            )
    else:
        if not trial.read(WORK / "limit-recovery-3/positive-preflight.json")["passed"]:
            raise ValueError("positive control required")
        trial.run(args.arm)
