"""Single pre-registered decoding contrast, not a sampling-parameter search."""

import argparse
from pathlib import Path
from unittest.mock import patch

import harness_semantic_transport as H

B, R, E = H.B, H.R, H.E
BATCH = H.BATCH.parent / "r4-semantic-greedy-20261017-1"
TEMPERATURE_ONE = H.BATCH
ADAPTER = B.KIT / "benchmarks/reviewer_semantic_greedy.py"


def prepare(used):
    assert B.read(TEMPERATURE_ONE / "decision.json")["qualification"] == "HOLD"
    original_save = B.save

    def save(path, value):
        if Path(path).name == "experiment-request.json":
            value["review_id"] = value["review_id"].replace(
                "transport-v2-", "greedy-v1-", 1
            )
        if Path(path) == BATCH / "registration.json":
            value["feature_id"] = "semantic-reviewer-single-greedy-contrast"
            value["axis"] = (
                "Only effective Reviewer temperature 1 -> 0; same repaired harness, prompt/schema/source/contracts/model/limits. Coder trusted config unchanged; effective wire setting explicitly archived."
            )
            value["dependencies"] = [str(TEMPERATURE_ONE / "decision.json")]
            value["hypothesis"] = (
                "Repeated identical inputs changed issue classification and exhausted output. Test one fixed greedy setting; improved reliability is unproven. No further temperature/strength/sampling values in this stage."
            )
            value["control_caveat"] = (
                "Pinned same-session repaired-harness temperature-one batch, not new simultaneous randomized controls."
            )
            value["criterion"] = (
                "Original 16/16 substantive correctness AND real regression 4/4; no worse than temperature-one. No retries, no more profiles. Failure closes this profile and requires a broader capability/contract decision before further live."
            )
            for row in value["cells"]:
                cell = TEMPERATURE_ONE / "cells" / row["id"]
                row["same_session_control"] = {
                    str(cell / p): B.sha(cell / p)
                    for p in ("result.json", "reviewer.json")
                }
        return original_save(path, value)

    with (
        patch.object(H, "BATCH", BATCH),
        patch.object(H, "ADAPTER", ADAPTER),
        patch.object(B, "save", save),
    ):
        H.prepare(used)


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
                **B.read(TEMPERATURE_ONE / "live-freeze.json")["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        B.KIT / "tests/test_reviewer_semantic_greedy.py",
                        TEMPERATURE_ONE / "decision.json",
                        TEMPERATURE_ONE / "grid-results.json",
                        BATCH / "registration.json",
                        BATCH / "offline-controls.xml",
                    )
                },
            }
        },
    )


def audit():
    with patch.object(H, "BATCH", BATCH):
        H.audit()


def run(name, used):
    with patch.object(H, "BATCH", BATCH), patch.object(H, "ADAPTER", ADAPTER):
        H.run(name, used)


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
