"""Prepare authentic scripted Coder archives without consuming review dispatch."""

import argparse
import time
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import reviewer_profile_screen as V

BATCH = I.BASE / "reviewer-profile-screen-20261022-2"


def prepare(used):
    original_command, original_save = I.command, S.save

    def command(root, mode="unit", replay=None):
        # Only scripted live-control drafts skip the offline Reviewer inspection.
        # Independent full-chain replay fixtures still exercise the normal unit.
        if replay is not None and "cells" in Path(root).parts:
            mode = "coder"
        return original_command(root, mode, replay)

    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                preparation_correction="Scripted Coder-only application leaves host-review-dispatch absent; no deleted locks or altered archives",
                prior_batch="reviewer-profile-screen-20261022-1: hash-1 rejected before model request; remaining two NOT_RUN",
            )
            value["pins"][str(Path(__file__))] = S.sha(__file__)
            for cell, row in S.read(BATCH / "cells.json").items():
                identity = row["identity"]["run_id"]
                run = Path(row["root"]) / ".agent/tasks" / identity / "runs" / identity
                assert not (run / "host-review-dispatch.json").exists(), cell
        original_save(path, value)

    V.BATCH = BATCH
    I.command, S.save = command, save
    try:
        V.prepare(used)
    finally:
        I.command, S.save = original_command, original_save


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=V.ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    V.BATCH = BATCH
    if a.mode == "prepare":
        old = I.BASE / "reviewer-profile-screen-20261022-1"
        if not (old / "decision.json").exists():
            S.save(old / "decision.json", {
                "status": "HOLD_PREPARATION_DISPATCH_CONSUMED",
                "executed_model_reviews": 0,
                "hash-1": "Infrastructure dispatch rejection before first model turn",
                "binding-1": "NOT_RUN",
                "collector-1": "NOT_RUN",
                "preservation": "No dispatch records removed; new batch uses Coder-only archive generation",
            })
        prepare(a.weekly_used)
    else:
        V.run(a.cell, a.weekly_used, time.time())
