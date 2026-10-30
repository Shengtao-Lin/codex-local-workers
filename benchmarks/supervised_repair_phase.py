"""Fixed repair-phase test on exposed tasks with the unchanged aligned budget."""

import supervised_bounded_trial as B
import supervised_feedback_trial as F

BATCH = B.BATCH.with_name("supervised-repair-phase-20261020-1")
ORDER = F.ORDER


def command(root, mode="unit", replay=None):
    return B.command(root, mode, replay) + ["--focused-repair"]


if __name__ == "__main__":
    if not (
        B.BATCH.with_name("supervised-reference-20261019-1") / "decision.json"
    ).exists():
        raise ValueError("Previous fixed batch not closed")
    F.prepare(
        BATCH,
        command,
        F.BATCH / "candidate-preimages",
        "Bounded-source candidate with explicit host implement/repair phase and literal failure display. No API reference, task-specific fix, new role, model or budget. Exposed six-cell repeat; ordinary failures complete diagnostics; gate unchanged.",
        extra_pins=[__file__, F.S.KIT / "benchmarks/repair_phase_rules.py"],
    )
