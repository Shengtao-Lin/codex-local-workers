"""One joint staged-review candidate; fail closed without host semantic inference."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import harness_typed_observations as C
import reviewer_discriminating_status as D

B, R, E = C.B, C.R, C.E
CONTROL = C.BATCH
BATCH = CONTROL.parent / "r4-contract-first-20261017-1"
ADAPTER = B.KIT / "benchmarks/reviewer_contract_first.py"


def prepare(used):
    assert B.read(D.BATCH / "decision.json")["qualification"] == "PASS_COMPONENT"
    original_save = B.save

    def save(path, value):
        if Path(path).name == "experiment-request.json":
            value["review_id"] = value["review_id"].replace(
                "typed-v1-", "contract-first-v1-", 1
            )
        if Path(path) == BATCH / "registration.json":
            value.update(
                {
                    "feature_id": "contract-first-shared-budget-review",
                    "axis": "Joint architectural candidate: source-blind contract-status prediction on supported real profile before mandatory full REPORT; explicit claim/actual mismatch cannot become verified. Original16 receive unchanged semantic input/schema. A single low/required recovery profile remains sticky after first cap, second cap stops. Original16 total requests/4 total errors/600 seconds/4096 per response shared across phases, not expanded.",
                    "dependencies": [
                        str(CONTROL / "decision.json"),
                        str(D.BATCH / "decision.json"),
                    ],
                    "hypothesis": "Matched discriminating prediction4/4 in both arms shows narrow capability. Decompose normative inference from source judgment instead of adding wording/fields. Untrusted predictions are not gold, a positive proof, test execution, risk classification or acceptance.",
                    "criterion": "Original16/16 full report quality AND exposed real4/4, correct None/status findings and observation judgments. No automatic defect or acceptance from predictions. No new Coder/holdout/R4 credit. Complete fixed batch, never patch or resample within it.",
                    "owned_contract_ids": [
                        "source-blind-prediction-provenance",
                        "explicit-cross-phase-consistency",
                        "original-deterministic-source-gates",
                        "global-request-error-deadline",
                    ],
                    "scope_limitation": "Only approved collect-tools observation profile with one owned contract enters prediction phase. Other profiles keep existing REPORT. Closed source-version table is diagnostic, not portable production capability.",
                    "execution_order": "Real regressions first, then original16; fixed before live to test critical failure early within remaining account quota. Not selected by outcomes.",
                }
            )
            value["cells"] = [
                r for r in value["cells"] if r["group"] == "exposed-real"
            ] + [r for r in value["cells"] if r["group"] == "original-sixteen"]
        return original_save(path, value)

    with (
        patch.object(C, "BATCH", BATCH),
        patch.object(C, "ADAPTER", ADAPTER),
        patch.object(C, "CONTROL", CONTROL),
        patch.object(B, "save", save),
    ):
        C.prepare(used)


def freeze():
    tree = ET.parse(BATCH / "controls-combined.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + k) for k in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(CONTROL / "live-freeze.json")["pins"],
                **B.read(D.BATCH / "live-freeze.json")["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        B.KIT / "tests/test_reviewer_contract_first.py",
                        CONTROL / "decision.json",
                        D.BATCH / "decision.json",
                        BATCH / "registration.json",
                        BATCH / "controls.xml",
                        BATCH / "controls-final.xml",
                        BATCH / "controls-combined.xml",
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
