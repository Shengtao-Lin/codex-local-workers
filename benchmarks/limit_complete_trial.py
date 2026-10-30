"""Clean-start optimization release candidate; recovery passes never count here."""

import argparse

import limit_shaped_trial as shaped
from capability_fit import WORK, write

trial = shaped.trial
trial.BASE = WORK / "limit-complete-1"
trial.SNAPSHOT = WORK / "limit-fresh-runtime-1"
trial.ARMS = ("semantic-complete-1", "semantic-complete-2", "semantic-complete-3")

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
                    "comparison": "Same original algorithm baseline and shape-matched guidance as limit-shaped-1",
                    "changed": "Frozen formatter recognition, localized Pyright focus and version-fresh repair context",
                    "release_gate": "All three independent clean-start Coder/Reviewer units plus Primary integration pass; recovery-only runs never replace failures",
                    "coordinator": "No decomposition needed for one cohesive unit",
                },
            )
    else:
        trial.run(args.arm)
