"""Primary-authorized new packet revision adding a missing protected boundary."""

import argparse
import hashlib
import json
from pathlib import Path

from complex_fixture_cases import transaction_case

KIT = Path(__file__).resolve().parents[1]


def prepare(root, task_id, parent_run_id, run_id):
    root = root.resolve()
    root.relative_to((KIT / "benchmarks/work/mixed-v1").resolve())
    for value in (task_id, parent_run_id, run_id):
        if not value or any(
            char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in value
        ):
            raise ValueError("invalid identity")
    parent = root / ".agent/tasks" / task_id / "runs" / parent_run_id
    if not (parent / "completed.json").is_file():
        raise ValueError("parent must be completed")
    packet = json.loads((parent / "packet.json").read_text(encoding="utf-8"))
    if packet.get("task_id") != task_id or packet.get("unit_id") != "atomic-publish":
        raise ValueError("unexpected parent identity")
    target = root / ".agent" / f"{run_id}-packet.json"
    if target.exists() or (root / ".agent/tasks" / task_id / "runs" / run_id).exists():
        raise ValueError("run identity already exists")
    packet = {key: value for key, value in packet.items() if not key.startswith("_")}
    for key in ("parent_run_id", "preserve_contract"):
        packet.pop(key, None)
    protected = "tests/test_rollback_failure.py"
    with (root / protected).open("x", encoding="utf-8") as stream:
        stream.write(transaction_case()["files"][protected])
    packet.update(
        run_id=run_id,
        attempt=packet["attempt"] + 1,
        packet_revision=packet["packet_revision"] + 1,
        plan_revision=packet["plan_revision"] + 1,
    )
    packet["focused_tests"].append(protected)
    packet["scope"]["readonly"].append(protected)
    packet["review_feedback"] = [
        {
            "finding_id": "rollback-masks-original-exception",
            "contract_id": "atomic-publish",
            "text": "Inherited Reviewer finding and Primary executed probe both confirm rollback failure masks the original write/commit error. The new protected boundary test now reproduces it in VALIDATE. Repair exception propagation in publish.py while retaining all previously passing behavior. Original hard contract and writable scope unchanged. Prior run: "
            + parent_run_id,
        }
    ]
    with target.open("x", encoding="utf-8") as stream:
        json.dump(packet, stream, indent=2)
    with target.with_suffix(".provenance.json").open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "parent_run_id": parent_run_id,
                "protected_test": protected,
                "sha256": hashlib.sha256((root / protected).read_bytes()).hexdigest(),
                "reason": "Primary-proven contract gap; new packet revision, not mutation of archived validation.",
            },
            stream,
            indent=2,
        )
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--parent", required=True)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    print(prepare(args.root, args.task, args.parent, args.run))
