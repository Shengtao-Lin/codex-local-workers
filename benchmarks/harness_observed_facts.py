"""One fixed factual-observation contrast; no new model execution permissions."""

import argparse
from pathlib import Path
from unittest.mock import patch

import harness_semantic_policy as C
import reviewer_observation_probe as OBS

B, R, E = C.B, C.R, C.E
CONTROL = C.BATCH
BATCH = CONTROL.parent / "r4-observed-facts-20261017-1"
ADAPTER = B.KIT / "benchmarks/reviewer_observed_facts.py"


def prepare(used):
    assert B.read(CONTROL / "decision.json")["qualification"] == "HOLD"
    assert B.read(OBS.BATCH / "decision.json")["model_calls"] == 0
    original_save = B.save

    def save(path, value):
        if Path(path).name == "experiment-request.json":
            value["review_id"] = value["review_id"].replace(
                "policy-v1-", "facts-v1-", 1
            )
        if Path(path) == BATCH / "registration.json":
            value["feature_id"] = "sealed-factual-observation-input"
            value["axis"] = (
                "Only approved_observations added: Primary-executed actual outcomes, exact source/module hashes, no expected results. Same canonical policy/system/schema/temperature0/model/budgets/hard contracts and tests."
            )
            value["hypothesis"] = (
                "Ground repeated False-versus-None reasoning errors in actual observations. No model-selected inputs or new execution action; not a static-only review qualification."
            )
            value["dependencies"] = [
                str(CONTROL / "decision.json"),
                str(OBS.BATCH / "observation-seal.json"),
            ]
            value["criterion"] = (
                "Original sixteen 16/16 substantive judgments AND four exposed real regressions 4/4, with causal None/state detection in both faulty implementations. No resampling or extra candidate. No R4/new Coder/holdout credit."
            )
            value["authority"] = (
                "Primary fixed observations only. Model still has REPORT only; it cannot choose a target, new data inputs, interpreter, source path or command."
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
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "offline-controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + t) for t in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(CONTROL / "live-freeze.json")["pins"],
                **B.read(OBS.BATCH / "observation-seal-v2.json")["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        B.KIT / "tests/test_reviewer_observed_facts.py",
                        OBS.BATCH / "observation-seal-v2.json",
                        OBS.BATCH / "decision.json",
                        CONTROL / "decision.json",
                        CONTROL / "grid-results.json",
                        BATCH / "registration.json",
                        BATCH / "prelive-amendment.json",
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
