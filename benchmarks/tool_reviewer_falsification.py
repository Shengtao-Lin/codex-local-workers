"""Registered real-artifact controls for provisional rework falsification."""

import argparse

import tool_reviewer_transfer as transfer
from capability_fit import WORK, freeze, write

BASE = WORK / "tool-reviewer-falsification-1"
SNAPSHOT = WORK / "tool-reviewer-runtime-5"
ARMS = tuple(
    f"{mode}-{variant}-r{r}"
    for r in (1, 2)
    for mode in ("control", "falsify")
    for variant in ("hidden", "clean")
)


def configure():
    transfer.BASE = BASE
    transfer.SNAPSHOT = SNAPSHOT
    transfer.ARMS = ARMS


def register():
    if not SNAPSHOT.exists():
        freeze(SNAPSHOT.name)
    write(
        BASE / "registration.json",
        {
            "arms_in_order": list(ARMS),
            "weekly_ceiling": 23,
            "axis": "Only reviewer_finding_challenge false/true; prepass false in both",
            "runtime": str(SNAPSHOT),
            "common_runtime_fixes": [
                "structural contract consistency",
                "bounded citation range feedback",
            ],
            "sources": "Actual accepted clean artifact and actual failed shared-deadline artifact, immutable hashes checked before call",
            "model": "Same Muse, contexts, sampling, budgets, serial single residency",
            "tests": "Two ordinary normal paths; twelve-test protected oracle outside readable scope",
            "credit": "Reviewer-only diagnostic, synthetic Coder archive; no E/C calls, fresh-chain acceptance or cloud savings",
            "grading": "Primary causal adjudication; no keyword grading, invalid reports count separately",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "run"))
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    configure()
    register() if args.action == "register" else transfer.run(args.arm)
