"""One joint fixed-observation/recovery candidate, not a retry of old invocations."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import harness_observed_facts as C
import reviewer_fixed_observations as OBS

B, R, E = C.B, C.R, C.E
CONTROL = C.BATCH
BATCH = OBS.BATCH
ADAPTER = B.KIT / "benchmarks/reviewer_bounded_recovery.py"


def prepare(used):
    assert B.read(CONTROL / "decision.json")["qualification"] == "HOLD"
    original_save = B.save

    def save(path, value):
        if Path(path).name == "experiment-request.json":
            value["review_id"] = value["review_id"].replace(
                "facts-v1-", "bounded-v1-", 1
            )
        if Path(path) == BATCH / "registration.json":
            value.update(
                {
                    "feature_id": "fixed-observations-shared-budget-recovery",
                    "owned_contract_ids": [
                        "fixed-source-facts",
                        "no-semantic-oracle",
                        "shared-request-error-deadline",
                        "one-shot-output-cap-recovery",
                    ],
                    "axis": "Joint candidate: fixed Primary factual observations for all four pure families; one output-cap-only recovery using required REPORT within original shared 16 requests/4 errors/600 seconds and 4096 tokens per response. No partial analysis used, no model execution action.",
                    "hypothesis": "Ground actual boundary behavior without inventing test-creation obligations; prevent a single empty output-cap response from prematurely ending an otherwise budgeted call. Joint result cannot isolate contribution of each change.",
                    "dependencies": [str(CONTROL / "decision.json")],
                    "criterion": "Original 16/16 and exposed real 4/4 substantive correctness, both faulty real sources must identify actual None/status defect. First output-cap failures remain separately counted. No new Coder/holdout or R4 credit.",
                    "authority": "Model still REPORT only. Inputs/targets/commands fixed by Primary. No production runtime change, no budget increase, no retry HTTP/timeout or second cap.",
                    "control_caveat": "Pinned prior factual-input batch; not simultaneous randomized comparison. No additional candidates or resampling in this batch.",
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
                **B.read(OBS.SEAL)["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        Path(OBS.__file__),
                        B.KIT / "tests/test_reviewer_bounded_recovery.py",
                        OBS.SEAL,
                        CONTROL / "decision.json",
                        CONTROL / "grid-results.json",
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
