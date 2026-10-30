"""Combine previously isolated dependency evidence and explicit repair-phase support."""

import supervised_feedback_trial as F
import supervised_reference_trial as R
import supervised_repair_phase as P

BATCH = P.BATCH.with_name("supervised-combined-20261020-1")
ORDER = F.ORDER
command = P.command


if __name__ == "__main__":
    if not (P.BATCH / "decision.json").exists():
        raise ValueError("Finish fixed repair-phase batch before combining candidates")
    F.prepare(
        BATCH,
        command,
        F.BATCH / "candidate-preimages",
        "Composition of measured controls: bounded source/UTF-8 report, existing API documentation evidence and explicit implement/repair phase. Same tasks/model/budget/checks/Reviewer. Exposed repeat; original results not replaced; no gold snippets or extra semantic hints.",
        configure_cell=R.configure,
        extra_pins=[
            __file__,
            R.__file__,
            P.__file__,
            F.S.KIT / "benchmarks/repair_phase_rules.py",
            F.S.KIT / "benchmarks/stdlib_reference.py",
        ],
    )
