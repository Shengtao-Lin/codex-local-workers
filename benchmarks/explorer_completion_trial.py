"""Four fresh Explorer-only calls; same questions/configuration as convergence-1."""

import argparse
from pathlib import Path

import qualification_matrix_v6 as existing
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "explorer-completion-1"
SNAPSHOT = WORK / "explorer-completion-runtime-1"
CELLS = ("label-rollup-r1", "async-receipt-r1", "label-rollup-r2", "async-receipt-r2")


def configure():
    existing.BASE, existing.SNAPSHOT = BASE, SNAPSHOT
    existing.configure()
    return existing.previous.prior.MATRIX


def prepare():
    existing.BASE, existing.SNAPSHOT = BASE, SNAPSHOT
    existing.prepare()
    baseline = WORK / "convergence-runtime-1"
    for name in ("worker-runtime.py", "reviewer-runtime.py", "config.json"):
        relative = ".local-agents/" + name
        if digest(SNAPSHOT / relative) != digest(baseline / relative):
            raise ValueError("Coder/Reviewer/config must remain frozen")
    write(
        BASE / "experiment.json",
        {
            "cells": CELLS,
            "weekly_used_start": 33,
            "weekly_used_ceiling": 40,
            "axis": "Generic locate-mode completion guidance and persistent required paths only",
            "same_questions_and_case_configs": True,
            "no_new_known_answer_anchors": True,
            "coder_reviewer_coordinator_calls": 0,
            "unused_prepared_units_receive_no_credit": True,
            "decision": "Four independently complete answers required; otherwise HOLD and stop this candidate",
            "history": "Do not overwrite convergence-1 strict Explorer 2/4",
            "driver_sha256": digest(Path(__file__)),
            "global_config_sha256": digest(KIT / ".local-agents/config.json"),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("identity", nargs="?", choices=CELLS)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        registration = read(BASE / "experiment.json")
        if digest(Path(__file__)) != registration["driver_sha256"]:
            raise ValueError("driver drift")
        matrix = configure()
        manifest = matrix.verify()
        cell = next(c for c in manifest["cells"] if c["id"] == args.identity)
        root = Path(cell["root"])
        if (root / ".agent/explorer.json").exists():
            raise FileExistsError("historical call cannot be replayed")
        matrix.explore(args.identity)
        verify_hashes(root, cell["hashes"])
