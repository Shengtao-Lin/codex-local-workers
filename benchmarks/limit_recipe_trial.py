"""Executable unrelated worked example: assisted optimization, not unaided credit."""

import argparse

import limit_release_trial as released
from capability_fit import WORK, write

trial = released.trial
trial.BASE = WORK / "limit-recipe-1"
trial.ARMS = ("semantic-recipe-1", "semantic-recipe-2", "semantic-recipe-3")
trial.EXAMPLE = """Advisory executable worked example for unrelated job scheduling:
import heapq
def choose_jobs(jobs, count, newest, priority, queue):
    rows = [(priority(job), queue(job), position, job)
            for position, job in enumerate(jobs)]
    choose = heapq.nlargest if newest else heapq.nsmallest
    chosen = choose(count, rows, key=lambda row: row[:3])
    return [row[3] for row in chosen]
This evaluates both callbacks once per job before comparisons and compares only
priority, queue, POSITIVE original position. nlargest already orders the complete
key descending: no post-selection reverse or sort-by-position. Payload is never
compared. With red,blue,green tied in both keys, oldest count2 returns red,blue;
newest count2 returns green,blue. Source API differs from this example: honor its
validated optional-count invariant before calling heap helpers, preserve all
other policies and errors, and validate tests plus static checks. Do not copy
unverified surrounding code. This is advisory, not a required implementation.
The independently verified hard contract remains authoritative."""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "prepare":
        trial.prepare(args.arm, clean_start=True)
        if not (trial.BASE / "registration.json").exists():
            write(
                trial.BASE / "registration.json",
                {
                    "arms": list(trial.ARMS),
                    "weekly_ceiling": 23,
                    "comparison": "Same clean baseline, tests, models and runtime as limit-release-1",
                    "changed": "Executable unrelated job-scheduling worked example instead of prose-only example",
                    "credit": "Primary-authored algorithm recipe is assistance cost; not unaided coding or proven cloud savings",
                    "release_gate": "3/3 real Coder/Reviewer/Primary chains, then held-out transfer; old failures not replaced",
                },
            )
    else:
        trial.run(args.arm)
