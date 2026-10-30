"""Single-axis tool-choice diagnostic; reuses frozen semantic-probe inputs."""

import argparse
import copy
from pathlib import Path

import reviewer_semantic_probe as P

B = P.B
OLD = P.BATCH
BATCH = OLD.parent / "r4-review-required-probe-20261016-1"


def required_client(base):
    class RequiredClient(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.native_tool_choice = "required"

    return RequiredClient


def prepare(used):
    assert 0 <= used < 45
    assert B.read(OLD / "decision.json")["qualification"] == "HOLD"
    BATCH.mkdir(exist_ok=False)
    registration = copy.deepcopy(B.read(OLD / "registration.json"))
    registration.update(
        feature_id="reviewer-required-report-probe",
        weekly_used_start=used,
        axis="Only tool_choice auto -> required. Exact messages/tools/model/sampling/output limit unchanged; four new calls, previous 3/4 HOLD retained.",
        joint_intervention=None,
        previous_batch=str(OLD),
    )
    for row in registration["cells"]:
        messages = B.read(OLD / "cells" / row["id"] / "messages.json")
        B.save(BATCH / "cells" / row["id"] / "messages.json", messages)
        assert (
            B.sha(BATCH / "cells" / row["id"] / "messages.json")
            == row["messages_sha256"]
        )
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
                B.KIT / "tests/test_reviewer_required_probe.py",
                BATCH / "registration.json",
                BATCH / "controls.xml",
                OLD / "decision.json",
            )
        },
    }
    B.save(BATCH / "live-freeze.json", {"pins": pins})


def run(name, used):
    original_load = P.H.R.load

    def load(path, module_name):
        module = original_load(path, module_name)
        if module_name == "semantic_probe_worker":
            module.LMStudioClient = required_client(module.LMStudioClient)
        return module

    P.H.R.load = load
    P.BATCH = BATCH
    try:
        P.run(name, used)
    finally:
        P.H.R.load = original_load
        P.BATCH = OLD


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "freeze", "run"])
    p.add_argument("--used", type=int)
    p.add_argument("--case")
    args = p.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
