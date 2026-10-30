"""Separate inspection archives from live handoffs; never erase dispatch markers."""

import argparse

import feedback_reviewer_controls as V1
from feedback_recovery_trial_v2 import BATCH


def prepare():
    V1.BATCH = BATCH
    original = V1.T.run

    def run(argv, root, timeout=120):
        if "--inspect-only" in argv:
            return {
                "exit_code": 0,
                "status": "REUSED_EXACT_VERSION_INPUT_INSPECTION",
                "evidence": "feedback-recovery-20261018-1/reviewer-controls/*/inspection.json",
                "note": "Inspect-only claims unique dispatch. Fresh canonical gates were verified; do not spend their dispatch before live.",
            }
        return original(argv, root, timeout)

    V1.T.run = run
    V1.prepare()
    V1.S.save(
        BATCH / "reviewer-controls/amendment.json",
        {
            "old_launches": "Both negative startup attempts failed before first model turn; review_id and run dispatch were already claimed by inspect-only. No model-quality outcome.",
            "change": "Fresh independently generated scripted Coder archives; reuse old authenticated input inspection, never delete or overwrite any claim",
            "scope": "Same contract, code, tests, config, Reviewer and budgets; identity/root paths only change",
            "pin": {__file__: V1.S.sha(__file__)},
            "require": "One substantive negative and one positive review; zero model Coder calls",
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("--label", choices=["negative", "positive"])
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--usage-observed-at", type=float)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare()
        print("Fresh control handoffs prepared, dispatch unclaimed")
    else:
        V1.BATCH = BATCH
        amendment = V1.S.read(BATCH / "reviewer-controls/amendment.json")
        assert all(V1.S.sha(p) == sha for p, sha in amendment["pin"].items())
        V1.run(args.label, args.weekly_used, args.usage_observed_at)
