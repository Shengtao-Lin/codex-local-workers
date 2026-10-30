"""Same registered tasks/budget, UTF-8 report fix and safe two-form proposals."""

import normal_task_trial as N
import supervised_feedback_trial as F

BATCH = F.BATCH.with_name("supervised-bounded-20261019-1")
ORDER = F.ORDER


def command(root, mode="unit", replay=None):
    argv = N.command(root, mode, replay)
    argv.remove("--preserve-existing-imports")
    return argv + ["--bounded-source-output"]


if __name__ == "__main__":
    F.prepare(
        BATCH,
        command,
        F.BATCH / "candidate-preimages",
        "UTF-8 report read; function or unchanged-outside-target module accepted by same AST guard. Original compact feedback, unchanged model/budgets/contracts/checks. No literal-feedback option selected.",
    )
