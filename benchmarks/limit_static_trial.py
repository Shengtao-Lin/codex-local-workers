"""Independent bounded static recovery, not original algorithm-success credit."""

import argparse

import limit_format_trial as formatted
from capability_fit import WORK, write

trial = formatted.trial
trial.BASE = WORK / "limit-static-1"
trial.ARMS = ("semantic-static-1",)
trial.EXAMPLE = (
    "Focused repair based on independently observed diagnostics of this exact draft: "
    "35 protected tests already pass. Pyright reports at heapq.nlargest/nsmallest that "
    "policy.limit is int | None but n requires int. Narrow that value under the validated "
    "limit-policy invariant before helper calls, preserving the working algorithm and all "
    "callback/ordering semantics. Ruff format --check also reports this file would be "
    "reformatted; trusted automatic formatting is enabled. Validate immediately after "
    "the narrow source repair; address exact diagnostics, not a new algorithm redesign."
)
START = WORK / "limit-shaped-1/semantic-shaped-1" / trial.COMMON

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    arm = trial.ARMS[0]
    if args.action == "prepare":
        trial.prepare(arm, clean_start=True, start_source=START)
        write(
            trial.BASE / "registration.json",
            {
                "arms": list(trial.ARMS),
                "source": str(START),
                "source_sha256": trial.digest(START),
                "intervention": "Exact static traceback guidance and fixed formatter recognition",
                "credit": "Static recovery only, never original clean-start optimization success",
                "weekly_ceiling": 15,
                "stop": "One bounded recovery then evidence-backed decision",
            },
        )
    else:
        trial.run(arm)
