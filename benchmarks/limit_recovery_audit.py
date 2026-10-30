"""Audit separately registered recovery cohorts; never rewrite failed histories."""

import argparse
import json

import limit_recovery_trial as trial
from capability_fit import KIT, WORK, write

COHORTS = {
    "limit-recovery-3": ("control-1", "semantic-1", "semantic-2"),
    "limit-worked-1": ("semantic-clean-1", "semantic-clean-2"),
    "limit-shaped-1": ("semantic-shaped-1", "semantic-shaped-2"),
    "limit-format-1": ("semantic-format-1", "semantic-format-2"),
    "limit-static-1": ("semantic-static-1",),
}


def observe(root):
    packet = trial.read(root / ".agent/packet.json")
    report = trial.read(root / ".agent/coder.json")
    archive = root / report["evidence_refs"]["run_archive"]
    if report["identity"]["run_id"] != packet["run_id"]:
        raise ValueError("run identity mismatch")
    expected = dict(trial.read(root / ".agent/manifest.json")["files"])
    for change in report["changed_files"]:
        if change["path"] != trial.COMMON:
            raise ValueError("unexpected worker edit")
        expected[change["path"]] = change["final_sha256"]
    trial.verify_hashes(root, expected)
    attempts = []
    for path in sorted(archive.glob("validation-attempt-*.json")):
        value = trial.read(path)
        attempts.append(
            {
                "path": str(path),
                "sha256": trial.digest(path),
                "edit_revision": value["edit_revision"],
                "validation": value["validation"],
            }
        )
    events = [
        json.loads(line) for line in (archive / "events.jsonl").read_text().splitlines()
    ]
    requests = [e["facts"] for e in events if e["event"] == "model_request"]
    reviewer_path = root / ".agent/reviewer.json"
    return {
        "root": str(root),
        "identity": report["identity"],
        "status": report["status"],
        "failure_signature": report["failure_signature"],
        "actual_cumulative_diff": (archive / "cumulative.diff").read_text(
            encoding="utf-8"
        ),
        "attempts": attempts,
        "model_requests": len(requests),
        "max_context_utilization": max(
            (e.get("reported_context_utilization", 0) for e in requests), default=0
        ),
        "autoformat_events": [e for e in events if e["event"] == "autoformat"],
        "seconds": trial.read(root / ".agent/invocation.json")["seconds"],
        "reviewer": trial.read(reviewer_path) if reviewer_path.exists() else None,
        "primary": trial.read(archive / "review.json")
        if (archive / "review.json").exists()
        else None,
        "protected_inputs_unchanged": True,
    }


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--record-failed-decisions", action="store_true")
    args = parser.parse_args()
    frozen = KIT / "benchmarks/fixtures/limit-recovery-v3"
    provenance = trial.read(frozen / "provenance.json")
    trial.verify_hashes(frozen, provenance["files"])
    trial.verify_hashes(trial.SOURCE, provenance["sibling_current_hashes"])
    audit = trial.read(WORK / "limit-recovery-3/historical-audit.json")
    # The saved original byte-level task inventory is authoritative, not last-* pointers.
    historical = trial.TASK
    history_copy = WORK / "limit-recovery-3/historical-task"
    for path in history_copy.rglob("*"):
        if path.is_file() and trial.digest(path) != trial.digest(
            historical / path.relative_to(history_copy)
        ):
            raise ValueError("sibling history changed")
    for name in ("real-adapter-live-baseline-1", "limit-format-runtime-1"):
        snapshot = WORK / name
        trial.verify_hashes(snapshot, trial.read(snapshot / "freeze.json")["files"])
    if args.record_failed_decisions:
        for name, arms in COHORTS.items():
            for arm in arms:
                root = WORK / name / arm
                result = observe(root)
                if result["status"] != "failed":
                    raise ValueError(
                        "Success requires separate substantive Primary review"
                    )
                if result["primary"] is None:
                    identity = result["identity"]
                    decision = trial.command(
                        root,
                        [
                            str(trial.PYTHON),
                            "-B",
                            str(
                                WORK
                                / "limit-format-runtime-1/.local-agents/record-review.py"
                            ),
                            "--repo",
                            str(root),
                            "--task-id",
                            identity["task_id"],
                            "--run-id",
                            identity["run_id"],
                            "--decision",
                            "takeover",
                            "--summary",
                            "Registered bounded experiment ended with actual deterministic/protocol failures. Not accepted; preserve partial changes and all evidence. No unchanged retry or sibling implementation authorized. Original algorithm and static recovery credit remain separate.",
                        ],
                    )
                    if decision["exit"]:
                        raise ValueError(decision["output"])
    cohorts = {
        name: [observe(WORK / name / arm) for arm in arms]
        for name, arms in COHORTS.items()
    }
    facts = {
        "cohorts": cohorts,
        "original_history": audit,
        "exclude": {
            "limit-recovery-1": "Primary protected-test lint defect",
            "limit-recovery-2": "Primary protected-test format defect; no model calls",
        },
        "sibling_source_and_history_unchanged": True,
        "immutable_runtime_snapshots_unchanged": True,
        "positive_control": trial.read(
            WORK / "limit-recovery-3/positive-preflight.json"
        ),
        "cloud_savings": None,
        "warning": "Different starts/guidance are separate cohorts. Static recovery and Primary oracle are not original algorithm success.",
    }
    write(WORK / "limit-format-1/facts-1.json", facts)
    print(
        json.dumps(
            {
                name: [(r["status"], r["seconds"]) for r in rows]
                for name, rows in cohorts.items()
            }
        )
    )


if __name__ == "__main__":
    main()
