"""Matched second candidate: change ONLY Coder-visible Reviewer feedback."""

import shutil
import time
from pathlib import Path

import bounded_evidence_support as S
import reviewer_bounded_trial as R

BATCH = (
    S.KIT / "benchmarks/work/harness-convergence/reviewer-locator-feedback-20261020-1"
)


def prepare(used):
    assert S.read(R.BATCH / "decision.json")["gate_met"] is False
    shutil.copytree(R.BATCH / "private", BATCH / "private")
    R.prepare(
        batch=BATCH,
        used=used,
        feedback_mode="location-only",
        controls_path=BATCH / "offline-controls.xml",
        expected_controls=15,
        extra_pins=[__file__],
    )
    old, new = S.read(R.BATCH / "cells.json"), S.read(BATCH / "cells.json")
    matched = []
    for cell in R.ORDER:
        a, b = Path(old[cell]["root"]), Path(new[cell]["root"])
        assert S.sha(a / ".agent/packet.json") == S.sha(b / ".agent/packet.json")
        parent = old[cell]["parent_identity"]
        relative = Path(".agent/tasks") / parent["task_id"] / "runs" / parent["run_id"]
        for name in (
            "packet.json",
            "handoff.json",
            "post-state.json",
            "cumulative.diff",
        ):
            assert S.sha(a / relative / name) == S.sha(b / relative / name)
        # Raw arm now contains its failed child edits; starting bytes are the
        # still-immutable original parent post-state, not that final draft.
        expected = S.read(a / relative / "post-state.json")["validation_inputs"][
            new[cell]["target"]
        ]["sha256"]
        assert S.sha(b / new[cell]["target"]) == expected
        matched.append(
            {
                "cell": cell,
                "start_sha256": expected,
                "parent_archive_same": True,
                "hard_packet_same": True,
            }
        )
    S.save(
        BATCH / "matched-inputs.json",
        {
            "rows": matched,
            "raw_comparator": R.BATCH.name,
            "only_model_input_change": "Coder sees finding IDs/contract IDs/path/line/category, not prose interpretation or suggested fix. Canonical inherited packet and fresh Reviewer retain original raw feedback. No Primary semantic curation.",
            "limits": "Sequential exposed comparison, not randomized new-task evidence. Same four units/order/model/credits/checks; no result pooling or old failure rewriting.",
        },
    )
    print("Matched inputs confirmed; location-only feedback candidate frozen")


def run(cell, used, observed):
    assert time.time() - observed <= 120
    R.run(cell, used, observed, batch=BATCH)
