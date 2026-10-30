"""One bounded phase-only diagnostic; no task-specific repair hint."""

import os
import xml.etree.ElementTree as ET

import bounded_evidence_support as S
import failure_source_trial as F
import normal_task_trial as N

BATCH = F.BATCH.with_name("initial-repair-20261020-2")
ORDER = F.ORDER


def command(root, mode="coder", replay=None):
    argv = F.command(root, mode, replay)
    if "--failure-source" not in argv:
        argv.append("--failure-source")
    if "-B-" in root.parent.name:
        argv.append("--repair-start")
    return argv


def run(cell, used, observed):
    require_controls()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if cell not in ORDER[:4] and not all(
        S.read(BATCH / "live-results" / c / "result.json")["all_independent_pass"]
        for c in ("for-B-1", "all-B-1")
    ):
        raise ValueError("Both initial B repairs required before repeats")
    N.run(
        cell,
        used,
        observed,
        batch=BATCH,
        order=ORDER,
        build_command=command,
        usage_limit=50,
        batch_seconds=10800,
    )


def require_controls():
    cases = list(ET.parse(BATCH / "phase-controls.xml").iter("testcase"))
    if len(cases) != 3 or any(
        c.find(tag) is not None
        for c in cases
        for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("All three phase controls required before preparation/live")


if __name__ == "__main__":
    require_controls()
    F.prepare(
        BATCH,
        command,
        extra_pins=[
            __file__,
            S.KIT / "benchmarks/initial_repair_rules.py",
            BATCH / "phase-controls.xml",
        ],
        descriptions={
            "A": "Both arms receive same real failed-test source; initial header remains Implement",
            "B": "Only initial failed-start header becomes Repair CURRENT starting implementation, explicitly no prior Worker edit; no facts/counters changed",
        },
        conditional={
            "first": ORDER[:4],
            "then": ORDER[4:],
            "requires": "both initial B cells independent checked and source-correct",
        },
    )
