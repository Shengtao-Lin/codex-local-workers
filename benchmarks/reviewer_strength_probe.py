"""Fixed medium/high comparison under the same output cap; diagnostic only."""

import argparse
import copy
from pathlib import Path

import reviewer_matched_low_probe as L

B = L.B
OLD = L.BATCH
BATCH = OLD.parent / "r4-review-strength-20261016-1"
ORDER = [
    ("medium", "probe-01"),
    ("high", "probe-01"),
    ("medium", "probe-02"),
    ("high", "probe-02"),
    ("high", "probe-03"),
    ("medium", "probe-03"),
    ("high", "probe-04"),
    ("medium", "probe-04"),
]


def prepare(used):
    assert 0 <= used < 45
    assert B.read(OLD / "decision.json")["qualification"] == "HOLD"
    BATCH.mkdir(exist_ok=False)
    previous = B.read(OLD / "registration.json")
    rows = []
    for index, (strength, origin) in enumerate(ORDER, 1):
        old = next(r for r in previous["cells"] if r["id"] == origin)
        row = copy.deepcopy(old)
        row.update(id=f"cell-{index:02}", strength=strength, matched_low_origin=origin)
        messages = B.read(OLD / "cells" / origin / "messages.json")
        assert messages[0]["content"].count(L.TO) == 1
        messages[0]["content"] = messages[0]["content"].replace(
            L.TO, f"Reasoning strength: {strength}."
        )
        B.save(BATCH / "cells" / row["id"] / "messages.json", messages)
        row["messages_sha256"] = B.sha(BATCH / "cells" / row["id"] / "messages.json")
        rows.append(row)
    B.save(
        BATCH / "registration.json",
        {
            **previous,
            "cells": rows,
            "registered": 8,
            "feature_id": "reviewer-bounded-strength-contrast",
            "weekly_used_start": used,
            "previous_batch": str(OLD),
            "axis": "Only explicit system reasoning strength low -> medium/high. Model, sampling, context, auto tool choice, messages except that value, 4096 output cap and one call per cell stay fixed.",
            "criterion": "Each strength assessed separately: 4/4 including both causal defect detections and both correct references required for further formal-protocol qualification, never R4. If both qualify, prefer medium. Complete ordinary output-limit/semantic failures; stop safety/transport/drift/usage. No further strength or sampling sweep in this stage.",
            "limitation": "Known exposed single-function diagnostic, not a new holdout or general model benchmark.",
            "no_acceptance_or_holdout_credit": True,
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(OLD / "live-freeze.json")["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        B.KIT / "tests/test_reviewer_strength_probe.py",
                        BATCH / "registration.json",
                        BATCH / "controls.xml",
                        OLD / "decision.json",
                    )
                },
            }
        },
    )


def run(name, used):
    L.BATCH = BATCH
    try:
        L.run(name, used)
    finally:
        L.BATCH = OLD


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "freeze", "run"])
    p.add_argument("--case")
    p.add_argument("--used", type=int)
    args = p.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
