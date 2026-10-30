"""Versioned fully linted/formatted protected acceptance; v1/v2 retained."""

import argparse

import limit_recovery_trial as trial
from capability_fit import KIT, WORK

trial.BASE = WORK / "limit-recovery-3"
trial.FROZEN = KIT / "benchmarks/fixtures/limit-recovery-v3"
trial.SUPPORT = (
    KIT / "benchmarks/fixtures/limit-recovery-extra/test_limit_recovery_v3.py"
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run", "controls"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        trial.freeze()
    elif args.action == "prepare":
        trial.prepare(args.arm)
    elif args.action == "controls":
        import limit_recovery_controls as controls

        controls.trial = trial
        # controls imports v2, which mutates the shared module; restore v3 identity.
        trial.BASE = WORK / "limit-recovery-3"
        trial.FROZEN = KIT / "benchmarks/fixtures/limit-recovery-v3"
        trial.SUPPORT = (
            KIT / "benchmarks/fixtures/limit-recovery-extra/test_limit_recovery_v3.py"
        )
        controls.main()
    else:
        if not trial.read(trial.BASE / "positive-preflight.json")["passed"]:
            raise ValueError("positive control required before model cohort")
        trial.run(args.arm)
