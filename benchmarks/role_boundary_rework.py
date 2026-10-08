"""Guided factual boundary feedback, preserving canonical parent contracts."""

import argparse
import json

from capability_fit import WORK, write


def prepare(case, repetition):
    root = WORK / "roleq-six-1/runs/v1/roleq1" / f"{case}-round-{repetition}"
    original = json.loads(
        (root / ".agent/qual-unit-reference.json").read_text(encoding="utf-8")
    )
    if case == "window-groups":
        feedback = "Primary executed fact: isinstance(True, int) is True in Python, but the unchanged hard contract requires an EXACT integer width. The protected test_invalid[True] requires ValueError even when items is empty. Reject bool explicitly or otherwise enforce exact integer semantics, retaining the existing valid slices and invalid-input behavior. This is guided semantic recovery, not unseen success."
    elif case == "timeout-roundtrip":
        feedback = "Primary verified current source conflates absent timeout_ms with present None. Default 1000 applies ONLY to missing key; present None must raise ValueError. True and False are both bool, not accepted integers. Preserve exact zero and fractional seconds. The protected invalid None failure is an error-path contract, not permission to default it. This is guided semantic recovery, not unseen success."
    else:
        raise ValueError("unsupported bounded rework")
    child = {
        key: original[key]
        for key in (
            "schema_version",
            "task_id",
            "unit_id",
            "plan_revision",
            "packet_revision",
        )
    }
    child.update(
        run_id=original["run_id"].replace("-a1", "-a2"),
        parent_run_id=original["run_id"],
        preserve_contract=True,
        attempt=2,
        plan_revision=2,
        packet_revision=2,
        review_feedback=[
            {
                "finding_id": "primary-boundary-fact",
                "contract_id": "qual-unit",
                "text": feedback,
            }
        ],
    )
    write(root / ".agent/boundary-a2.json", child)
    print(root / ".agent/boundary-a2.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", choices=("window-groups", "timeout-roundtrip"), required=True
    )
    parser.add_argument("--repetition", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    prepare(args.case, args.repetition)
