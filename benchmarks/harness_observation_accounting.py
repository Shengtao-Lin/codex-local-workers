"""One report-coverage candidate; original contracts, observations and limits fixed."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import harness_conditional_recovery as C

B, R, E = C.B, C.R, C.E
CONTROL = C.BATCH
BATCH = CONTROL.parent / "r4-observation-accounting-20261017-1"
ADAPTER = B.KIT / "benchmarks/reviewer_observation_accounting.py"


def prepare(used):
    assert B.read(CONTROL / "decision.json")["qualification"] == "HOLD"
    original_save = B.save

    def save(path, value):
        if Path(path).name == "experiment-request.json":
            value["review_id"] = value["review_id"].replace(
                "conditional-v1-", "accounting-v1-", 1
            )
        if Path(path) == BATCH / "registration.json":
            value.update(
                {
                    "feature_id": "complete-observation-semantic-accounting",
                    "axis": "Only REPORT gains explicit per-observation semantic assessments. All semantic input values/system/model/conditional recovery/16 requests/4 errors/600 seconds/4096 response tokens unchanged. Host rejects missing/duplicate/contradictory model states, never computes expected outputs or contract semantics.",
                    "hypothesis": "False pass listed five falsy observations but silently omitted None. Require explicit coverage to distinguish omission from a concrete wrong interpretation; added schema complexity may hurt and remains a measured risk.",
                    "dependencies": [
                        str(CONTROL / "decision.json"),
                        str(CONTROL / "recovery-audit.json"),
                    ],
                    "criterion": "Original sixteen report-quality16/16 AND real regressions4/4 with causal None/status findings. Every observation accounted for; a valid schema does not imply semantic correctness. No R4/Coder/holdout credit. One fixed candidate, no resampling.",
                    "owned_contract_ids": [
                        "complete-observation-coverage",
                        "explicit-state-consistency",
                        "no-host-semantic-inference",
                        "unchanged-authority-and-budget",
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
                        B.KIT / "tests/test_reviewer_observation_accounting.py",
                        CONTROL / "decision.json",
                        CONTROL / "recovery-audit.json",
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
