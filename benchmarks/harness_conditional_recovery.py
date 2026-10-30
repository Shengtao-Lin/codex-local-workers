"""One conditional known-low contrast, all first-request facts and gates fixed."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import harness_bounded_recovery as C

B, R, E = C.B, C.R, C.E
CONTROL = C.BATCH
BATCH = CONTROL.parent / "r4-conditional-recovery-20261017-1"
ADAPTER = B.KIT / "benchmarks/reviewer_conditional_recovery.py"


def prepare(used):
    assert B.read(CONTROL / "decision.json")["qualification"] == "HOLD"
    original_save = B.save

    def save(path, value):
        if Path(path).name == "experiment-request.json":
            value["review_id"] = value["review_id"].replace(
                "bounded-v1-", "conditional-v1-", 1
            )
        if Path(path) == BATCH / "registration.json":
            value.update(
                {
                    "feature_id": "conditional-known-low-recovery",
                    "axis": "Only recovery request changes exact system instruction medium to already-tested low. All first requests identical; same fixed observations, native REPORT schema, model, temperature0, 4096 response cap, shared16/4/600 budget.",
                    "hypothesis": "Plain required-REPORT recovery still produced only reasoning. Known-low fallback may terminate after a first cap without weakening semantic gates. No further values or candidates in this batch.",
                    "dependencies": [
                        str(CONTROL / "decision.json"),
                        str(CONTROL / "recovery-audit.json"),
                    ],
                    "criterion": "Original sixteen report-quality 16/16 AND real regressions4/4 with correct None/status cause, no broken suggested alternatives. No new holdout/Coder/R4 credit. Record unchanged first-request failures and random differences, do not attribute uncapped improvements to conditional fallback.",
                    "control_caveat": "Pinned previous batch, not simultaneous randomization; first requests unchanged, so differences there cannot establish effect of recovery instruction.",
                }
            )
        return original_save(path, value)

    with (
        patch.object(C, "BATCH", BATCH),
        patch.object(C, "ADAPTER", ADAPTER),
        patch.object(C, "CONTROL", CONTROL),
        patch.object(B, "save", save),
    ):
        C.prepare(used)


def freeze():
    tree = ET.parse(BATCH / "offline-controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + k) for k in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(CONTROL / "live-freeze.json")["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        B.KIT / "tests/test_reviewer_conditional_recovery.py",
                        CONTROL / "decision.json",
                        CONTROL / "recovery-audit.json",
                        BATCH / "registration.json",
                        BATCH / "offline-controls.xml",
                    )
                },
            }
        },
    )


def audit():
    with patch.object(C, "BATCH", BATCH):
        C.audit()


def run(name, used):
    with patch.object(C, "BATCH", BATCH), patch.object(C, "ADAPTER", ADAPTER):
        C.run(name, used)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "freeze", "run"])
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
