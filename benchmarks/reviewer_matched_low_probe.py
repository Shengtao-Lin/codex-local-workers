"""Restore the formal Reviewer's exact reasoning directive in task-local probes."""

import argparse
import copy
from pathlib import Path

import reviewer_semantic_probe as P

B = P.B
OLD = P.BATCH
BATCH = OLD.parent / "r4-review-matched-low-20261016-1"
FROM = "Reasoning: low"
TO = "Reasoning strength: low."


def prepare(used):
    assert 0 <= used < 45
    assert B.read(OLD / "decision.json")["qualification"] == "HOLD"
    BATCH.mkdir(exist_ok=False)
    registration = copy.deepcopy(B.read(OLD / "registration.json"))
    registration.update(
        feature_id="reviewer-matched-low-directive",
        weekly_used_start=used,
        axis="Replace only malformed Reasoning: low with formal Reviewer's exact Reasoning strength: low. Tool choice remains auto; input evidence, native REPORT schema, model/sampling/context/output budget unchanged.",
        joint_intervention=None,
        previous_batch=str(OLD),
        limitation="Old task-local probes do not establish matched reasoning strength. Embedded template appends kwarg/default high absent a recognized strength directive; active rendered prompt is not captured.",
    )
    for row in registration["cells"]:
        messages = B.read(OLD / "cells" / row["id"] / "messages.json")
        assert messages[0]["content"].count(FROM) == 1
        messages[0]["content"] = messages[0]["content"].replace(FROM, TO)
        B.save(BATCH / "cells" / row["id"] / "messages.json", messages)
        row["messages_sha256"] = B.sha(BATCH / "cells" / row["id"] / "messages.json")
    B.save(BATCH / "registration.json", registration)


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")
    )
    pins = {
        **B.read(OLD / "live-freeze.json")["pins"],
        **{
            str(p): B.sha(p)
            for p in (
                Path(__file__),
                B.KIT / "tests/test_reviewer_matched_low.py",
                BATCH / "registration.json",
                BATCH / "controls.xml",
                BATCH / "reasoning-template-audit.json",
                OLD / "decision.json",
            )
        },
    }
    B.save(BATCH / "live-freeze.json", {"pins": pins})


def run(name, used):
    original = B.read

    def read(path):
        value = original(path)
        p = Path(path).resolve()
        if (
            p.parent.parent == (BATCH / "cells").resolve()
            and p.name == "result.json"
            and value.get("request_stats", {}).get("rejection_reason")
            == "output_token_limit"
        ):
            return {**value, "infra_failure": False}
        return value

    B.read = read
    P.BATCH = BATCH
    try:
        P.run(name, used)
    finally:
        B.read = original
        P.BATCH = OLD


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
