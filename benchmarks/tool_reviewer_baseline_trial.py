"""Bounded baseline-context qualification; prior controls are not randomized effect proof."""

import argparse

import tool_reviewer_canonical_trial as trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest

BASE = WORK / "tool-reviewer-baseline-1"


def configure():
    trial.BASE = BASE
    trial.PREFIX = "baseline"
    trial.ADAPTER = "reviewer_baseline_adapter.py"


def register():
    write(
        BASE / "registration.json",
        {
            "arms_in_order": [
                "hidden-candidate-r1",
                "clean-candidate-r1",
                "clean-candidate-r2",
                "hidden-candidate-r2",
            ],
            "weekly_ceiling": 23,
            "adapter_sha256": digest(KIT / "benchmarks/reviewer_baseline_adapter.py"),
            "axis": "Actual hash-verified archived preimages shown as explicitly historical comparison context, with no current read or citation credit",
            "unchanged": "Same real eligible clean/hidden archives, runtime-7, Muse/context/budgets/scope/semantic gates, ordinary citation schema",
            "historical_controls": "canonical control arms; not concurrent randomized causal-effect evidence",
            "credit": "Reviewer qualification only; no new Coder, Explorer, feature acceptance or savings",
            "expected_hidden": "Async final awaitable consumed a second time, violating preservation; original versus artifact identity controls establish concrete regression",
            "expected_clean": "Invocation awaited once, sync factory stays off-thread within original single deadline",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--kind", choices=("hidden", "clean"), default="hidden")
    parser.add_argument("--repetition", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        {"prepare": trial.prepare, "run": trial.run}[args.action](
            args.kind, "candidate", args.repetition
        )
