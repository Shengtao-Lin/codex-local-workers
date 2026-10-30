"""Create the opt-in wire archive before freezing any Worker input."""

import argparse
import os
from pathlib import Path

import strata_boundary_trial as B

BATCH = B.P.I.BASE / "strata-boundary-20261023-3"


def save(path, value):
    path = Path(path)
    if (
        path.name == "config.json"
        and ".agent" in path.parts
        and "prepared" not in path.parts
    ):
        (path.parent / "strata-wire").mkdir(parents=True, exist_ok=True)
    if path == BATCH / "registration.json":
        value = dict(value)
        value["prerequisite"] = (
            "Offline reference and old-draft negative controls pass; logging directory created before freeze. -1 timeout and -2 missing-directory failures retained, zero actual provider calls."
        )
        value["pins"][str(Path(__file__))] = B.S.sha(__file__)
    return B.save(path, value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=B.J.ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    assert args.weekly_used < 40
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    B.BATCH = B.MODEL.BATCH = B.FIRST.BATCH = BATCH
    B.FIRST.ENTRY = B.MODEL.ENTRY
    B.FIRST.configure()
    B.FIRST.ORIGINAL_SAVE = save
    B.J.TASKS.tasks = B.tasks
    if args.mode == "prepare":
        B.J.prepare(args.weekly_used)
    else:
        assert all(
            (BATCH / "negative-controls" / c / "result.json").exists()
            for c in ("message-1", "message-2")
        )
        rows = B.S.read(BATCH / "cells.json")
        assert all(
            (Path(r["root"]) / ".agent/strata-wire").is_dir() for r in rows.values()
        )
        B.P.TARGET = rows[args.cell]["target"]
        B.P.run(args.cell, args.weekly_used)
