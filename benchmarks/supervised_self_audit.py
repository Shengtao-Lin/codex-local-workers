"""Conditional fixed trial of bounded Coder self-review using existing resources."""

import os

import normal_task_trial as N
import supervised_feedback_trial as F
import supervised_repair_phase as P

BATCH = P.BATCH.with_name("supervised-self-audit-20261020-1")
ORDER = F.ORDER


def command(root, mode="unit", replay=None):
    return P.command(root, mode, replay) + ["--self-audit"]


def run(cell, used, observed):
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if cell not in ("json-1", "json-2"):
        for earlier in ("json-1", "json-2"):
            if not (BATCH / "primary" / earlier / "supervised-review.json").exists():
                raise ValueError(
                    "Conditional four-cell expansion requires both JSON accepts"
                )
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
    if not (
        P.BATCH.with_name("supervised-combined-20261020-1") / "decision.json"
    ).exists():
        raise ValueError("Prior fixed batch must close")
    F.prepare(
        BATCH,
        command,
        F.BATCH / "candidate-preimages",
        "Minimal explicit repair phase plus Coder self-review after passing checks. Identical source ends audited handoff; changed source invalidates checks and consumes the same 3-edit/3-post-check/12-request/900-second total. Same proposal schema, no API docs or specific fix hints; unchanged Reviewer.",
        extra_pins=[
            __file__,
            F.S.KIT / "benchmarks/self_audit_rules.py",
            F.S.KIT / "benchmarks/repair_phase_rules.py",
            F.S.KIT / "benchmarks/bounded_evidence_tasks.py",
            BATCH / "candidate-preimages/bounded_evidence_tasks.py",
        ],
        continue_rule="Complete the two JSON diagnostics even on ordinary failure. Only if both independently accepted, execute four registered ID/raw regressions. Otherwise retain four conditional NOT_RUN, HOLD, no replacement. Infra/safety/40% stop throughout.",
        conditional_expansion={
            "initial": ["json-1", "json-2"],
            "requires": "both independent supervised accepts",
            "then": ["ids-1", "raw-1", "raw-2", "ids-2"],
        },
        identity_prefix="self-audit-20261020-1-",
        replay_repeats=2,
        reuse_prepared=True,
    )
