"""Read actual immutable reports; never infer acceptance from test/model success."""

import argparse
import json
from pathlib import Path

from capability_fit import WORK, write


def inspect(root: Path, coder_name="coder.json"):
    path = root / ".agent" / coder_name
    if not path.exists():
        return {"workspace": str(root), "state": "pending"}
    coder = json.loads(path.read_text(encoding="utf-8"))
    archive = coder.get("evidence_refs", {}).get("run_archive")
    archive_root = (root / archive).resolve() if archive else None
    if archive_root is not None and not archive_root.is_relative_to(
        (root / ".agent/tasks").resolve()
    ):
        raise ValueError("archive outside canonical task history")
    review_path = archive_root / "review.json" if archive_root else None
    primary = (
        json.loads(review_path.read_text(encoding="utf-8"))
        if review_path and review_path.exists()
        else None
    )
    identity = coder.get("identity") or {}
    if primary and any(
        primary.get(key) != identity.get(key)
        for key in ("task_id", "unit_id", "run_id")
    ):
        raise ValueError("Primary review identity mismatch")
    events = archive_root / "events.jsonl" if archive_root else None
    model_started = bool(
        events
        and events.exists()
        and any(
            json.loads(line).get("event") == "model_request"
            for line in events.read_text(encoding="utf-8").splitlines()
        )
    )
    return {
        "workspace": str(root),
        "state": coder.get("status"),
        "failure_signature": coder.get("failure_signature"),
        "identity": coder.get("identity"),
        "primary_decision": primary.get("decision") if primary else None,
        "model_started": model_started,
        "report": str(path),
    }


def collect():
    rows = {}
    for cohort in (
        "roleq-six-1",
        "roleq-binding-comparison-1",
        "roleq-boundary-comparison-1",
        "roleq-temperature-comparison-1",
        "roleq-plain-json-comparison-1",
        "roleq-vocabulary-comparison-1",
        "roleq-vocabulary-comparison-2",
    ):
        manifest = json.loads(
            (WORK / cohort / "manifest.json").read_text(encoding="utf-8")
        )
        rows[cohort] = [inspect(Path(c["workspace"])) for c in manifest["cells"]]
    return {
        "classification": "Evidence index, not automatic qualification",
        "phase": "HOLD",
        "coordinator_started": False,
        "cohorts": rows,
        "qualification_requires": [
            "Every frozen fresh cell independently accepted",
            "Explorer success independent of Coder",
            "Reviewer effective hidden/clean reports",
            "Dependent multi-unit integration twice",
        ],
        "budget": {"weekly_used_latest": 24, "ceiling": 40},
        "cloud_tokens": None,
        "primary_active_time": None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        choices=("roleq-progress-1.json", "roleq-progress-2.json"),
        default="roleq-progress-1.json",
    )
    args = parser.parse_args()
    result = collect()
    write(WORK / args.output, result)
    print(
        json.dumps(
            {
                name: {
                    "accepted": sum(
                        row.get("primary_decision") == "accept" for row in rows
                    ),
                    "reports": sum(row["state"] != "pending" for row in rows),
                    "model_calls": sum(row.get("model_started", False) for row in rows),
                }
                for name, rows in result["cohorts"].items()
            }
        )
    )
