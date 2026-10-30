"""Conditional complete-chain repeat after the matched diagnostic improvement."""

import os

import normal_task_trial as N
import supervised_feedback_trial as F
import supervised_repair_phase as P
import static_focus_matched as M

BATCH = M.BATCH.with_name("supervised-static-release-20261020-1")
ORDER = F.ORDER


def command(root, mode="unit", replay=None):
    return P.command(root, mode, replay) + ["--static-focus"]


def run(cell, used, observed):
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if cell not in ("json-1", "json-2"):
        if not all(
            (BATCH / "primary" / p / "supervised-review.json").exists()
            for p in ("json-1", "json-2")
        ):
            raise ValueError("Both JSON accepts required before conditional expansion")
    N.run(
        cell,
        used,
        observed,
        batch=BATCH,
        order=ORDER,
        build_command=command,
        usage_limit=40,
        batch_seconds=14400,
    )


if __name__ == "__main__":
    if M.S.read(M.BATCH / "decision.json")["status"] != "PASS_NARROW_DIAGNOSTIC":
        raise ValueError("Matched diagnostic not qualified")
    F.prepare(
        BATCH,
        command,
        F.BATCH / "candidate-preimages",
        "Minimal bounded-source repair phase with version-bound static diagnostics from existing parser. No extra API documentation or self-audit; same models, budgets, contracts, full checks and Reviewer. Exposed six-cell repeat, not holdout transfer.",
        extra_pins=[
            __file__,
            P.__file__,
            M.S.KIT / "benchmarks/static_focus_rules.py",
            M.S.KIT / "benchmarks/repair_phase_rules.py",
            M.S.KIT / "benchmarks/bounded_evidence_tasks.py",
        ],
        identity_prefix="static-release-20261020-1-",
        continue_rule="Complete two JSON cells on ordinary failure. If both independently accepted, complete four fixed ID/raw regressions; else four conditional NOT_RUN and HOLD. Infra/safety/40% stop; no replacements.",
        conditional_expansion={
            "initial": ["json-1", "json-2"],
            "requires": "both independent accepts",
            "then": ["ids-1", "raw-1", "raw-2", "ids-2"],
        },
    )
