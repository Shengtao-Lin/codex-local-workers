"""Registered hidden/clean Reviewer qualification, separate from Coder credit."""

import argparse

from capability_fit import KIT, WORK, write
from complex_reviewer_challenge import run

BASE = WORK / "limit-reviewer-controls-1"
SOURCE = (
    KIT
    / "benchmarks/work/mixed-v1/complex-v2/coverage-1/atomic-evidence-publish-round-1"
)
SNAPSHOT = WORK / "limit-block-runtime-1"
ARMS = {
    f"{family}-{variant}-r{repetition}": (family, variant)
    for repetition in (1, 2)
    for family in ("rollback", "lock-release")
    for variant in ("hidden", "clean")
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "run"))
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--candidate-version", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    if args.candidate:
        BASE = WORK / f"limit-reviewer-challenge-{args.candidate_version}"
        SNAPSHOT = WORK / f"limit-prepass-runtime-{args.candidate_version}"
    if args.action == "register":
        write(
            BASE / "registration.json",
            {
                "arms_in_order": list(ARMS),
                "runtime_snapshot": str(SNAPSHOT),
                "weekly_ceiling": 23,
                "goal": "No clean false positive and causal source-backed hidden detection across two families twice",
                "oracle": "Primary-only outside packet scope; actual oracle must distinguish both variants",
                "grading": "Structural keyword triage is not effective detection; Primary must independently adjudicate each hidden finding",
                "credit": "Synthetic Coder archive, Coder not invoked, no complete-chain acceptance credit",
                "changed_mechanism": (
                    "One-shot adversarial boundary challenge after a valid provisional pass; no auto-verified claims or additional execution authority"
                    if args.candidate
                    else "Typed citation shapes and already-read current anchor feedback; unchanged semantic/citation/ordering checks"
                ),
                "models_and_residency": "Existing Muse and single residency; source config and model budgets retained",
            },
        )
    else:
        if not (BASE / "registration.json").is_file():
            raise ValueError("register before the first invocation")
        if (BASE / f"{args.arm}.json").exists():
            raise ValueError("arm already completed; never overwrite a result")
        family, variant = ARMS[args.arm]
        result = run(
            SOURCE,
            variant,
            SNAPSHOT,
            family,
            ordering=True,
            prepass_challenge=args.candidate,
        )
        write(BASE / f"{args.arm}.json", result)
        print(result)
