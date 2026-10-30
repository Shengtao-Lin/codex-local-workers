"""Versioned correction of Primary acceptance formatting; keep v1 history."""

import argparse

import limit_recovery_trial as trial
from capability_fit import KIT, WORK

trial.BASE = WORK / "limit-recovery-2"
trial.FROZEN = KIT / "benchmarks/fixtures/limit-recovery-v2"
trial.SUPPORT = (
    KIT / "benchmarks/fixtures/limit-recovery-extra/test_limit_recovery_v2.py"
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=trial.ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        trial.freeze()
    elif args.action == "prepare":
        trial.prepare(args.arm)
    else:
        trial.run(args.arm)
