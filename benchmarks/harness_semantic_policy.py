"""One canonical-policy restoration, holding the previous decoding profile fixed."""

import argparse
from pathlib import Path
from unittest.mock import patch

import harness_semantic_greedy as G

B, R, E = G.B, G.R, G.E
CONTROL = G.BATCH
BATCH = CONTROL.parent / "r4-canonical-policy-20261017-1"
ADAPTER = B.KIT / "benchmarks/reviewer_semantic_policy.py"


def prepare(used):
    assert B.read(CONTROL / "decision.json")["qualification"] == "HOLD"
    original_save = B.save

    def save(path, value):
        if Path(path).name == "experiment-request.json":
            value["review_id"] = value["review_id"].replace(
                "greedy-v1-", "policy-v1-", 1
            )
        if Path(path) == BATCH / "registration.json":
            value["feature_id"] = "canonical-review-policy-restoration"
            value["axis"] = (
                "Only task-local verdict_definitions restored from frozen formal system_prompt. Source/contracts/scenarios/schema/system prompt/model/temperature0/budgets unchanged. No examples or expected answers."
            )
            value["hypothesis"] = (
                "Minimal brief dropped explicit category definitions. Source-proved behavior became invented mandatory tests. Restore existing policy rather than adding case instructions; success remains unproven."
            )
            value["dependencies"] = [str(CONTROL / "decision.json")]
            value["criterion"] = (
                "Original sixteen 16/16 substantive judgments and four exposed real regressions 4/4. No resampling, no further policy candidate in this batch. Same pinned control inputs; no new Coder/holdout or R4 credit."
            )
            value["control_caveat"] = (
                "Pinned same-session temperature-zero control, not new randomized simultaneous control."
            )
        return original_save(path, value)

    with (
        patch.object(G, "BATCH", BATCH),
        patch.object(G, "ADAPTER", ADAPTER),
        patch.object(G, "TEMPERATURE_ONE", CONTROL),
        patch.object(B, "save", save),
    ):
        G.prepare(used)


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
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        B.KIT / "tests/test_reviewer_semantic_policy.py",
                        CONTROL / "decision.json",
                        CONTROL / "grid-results.json",
                        BATCH / "registration.json",
                        BATCH / "offline-controls.xml",
                    )
                },
            }
        },
    )


def audit():
    with patch.object(G, "BATCH", BATCH):
        G.audit()


def run(name, used):
    with patch.object(G, "BATCH", BATCH), patch.object(G, "ADAPTER", ADAPTER):
        G.run(name, used)


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
