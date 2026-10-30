"""One lossless-input contrast, keeping model/report protocol and all gates fixed."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import harness_observation_accounting as C

B, R, E = C.B, C.R, C.E
CONTROL = C.BATCH
BATCH = CONTROL.parent / "r4-typed-observations-20261017-1"
ADAPTER = B.KIT / "benchmarks/reviewer_typed_observations.py"


def prepare(used):
    assert B.read(CONTROL / "decision.json")["qualification"] == "HOLD"
    original_save = B.save

    def save(path, value):
        if Path(path).name == "experiment-request.json":
            value["review_id"] = value["review_id"].replace(
                "accounting-v1-", "typed-v1-", 1
            )
        if Path(path) == BATCH / "registration.json":
            value.update(
                {
                    "feature_id": "lossless-observation-event-input",
                    "axis": "Only real-family observations replace result_input scalar/shared_setup summary with complete original sealed typed event input. Actual outputs/source/hard contracts/tests/system/native schema/conditional recovery/model/budgets unchanged; first16 inputs identical.",
                    "hypothesis": "Model falsely described null as absent result event, and another compared observed behavior to implementation instead of contract. Test whether restoring actual event presence fixes the first issue; do not assume it fixes normative reasoning.",
                    "dependencies": [
                        str(CONTROL / "decision.json"),
                        str(CONTROL / "observation-audit.json"),
                    ],
                    "criterion": "Original16/16 complete report-quality AND exposed real4/4 with correct per-observation interpretation and None/status findings. No missing-event fiction, broken repair advice, hidden resampling or new Coder/holdout/R4 credit.",
                    "owned_contract_ids": [
                        "lossless-input-projection",
                        "unchanged-observation-results",
                        "no-oracle",
                        "fixed-source-and-budget",
                    ],
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
    tree = ET.parse(BATCH / "offline-controls-final.xml")
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
                        B.KIT / "tests/test_reviewer_typed_observations.py",
                        CONTROL / "decision.json",
                        CONTROL / "observation-audit.json",
                        BATCH / "registration.json",
                        BATCH / "offline-controls.xml",
                        BATCH / "offline-controls-final.xml",
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
