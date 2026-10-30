"""Collect immutable counts after Primary dispositions; never accept a unit."""

import argparse
import json
from datetime import datetime
from pathlib import Path

import bounded_evidence_support as S


def usage(paths, field):
    records = [S.read(path).get(field) for path in paths]
    totals = {}
    for key in ("prompt_tokens", "completion_tokens"):
        values = [(r or {}).get("response_usage", {}).get(key) for r in records]
        totals[key] = (
            sum(values) if values and all(type(v) is int for v in values) else None
        )
    return totals


def collect(batch):
    registration = S.read(batch / "registration.json")
    assert all(S.sha(p) == digest for p, digest in registration["pins"].items()), (
        "candidate drift"
    )
    rows = S.read(batch / "cells.json")
    cells = {}
    for label in registration["order"]:
        row = rows[label]
        result_path = batch / "live-results" / label / "result.json"
        if not result_path.exists():
            cells[label] = {"status": "NOT_RUN", "accepted": False}
            continue
        root = Path(row["root"])
        identity = row["identity"]
        task = root / ".agent/tasks" / identity["task_id"]
        archive = task / "runs" / identity["run_id"]
        result = S.read(result_path)
        primary = S.read(archive / "review.json")
        assert all(
            S.sha(root / p) == digest
            for p, digest in row["files"].items()
            if p != row["target"]
        ), "protected drift"
        accepted = primary["decision"] == "accept"
        if accepted:
            assert (
                result["all_independent_pass"]
                and result["summary"]["reviewer_decision"] == "pass_to_primary"
            )
            assert not result["assisted"] and not result["protected_drift"]
        review = task / "reviews" / ("auto-" + identity["run_id"])
        reviewer_usage, reviewer_requests, reviewer_seconds = None, 0, None
        if review.exists():
            reviewer_usage = usage(
                sorted(review.glob("phase-response-*.json")), "request_stats"
            )
            budget = review / "contract-first-budget.json"
            reviewer_requests = (
                S.read(budget)["actual_requests"] if budget.exists() else None
            )
            events_path = review / "events.jsonl"
            if events_path.exists():
                events = [
                    json.loads(line)
                    for line in events_path.read_text(encoding="utf-8").splitlines()
                ]
                times = {
                    event["event"]: datetime.fromisoformat(event["at"])
                    for event in events
                }
                if "review_completed" in times and "review_prepared" in times:
                    reviewer_seconds = (
                        times["review_completed"] - times["review_prepared"]
                    ).total_seconds()
        requests = [S.read(p) for p in sorted(archive.glob("proposal-request-*.json"))]
        ledger = result.get("ledger") or {}
        actual = ledger.get("actual") or {}
        assert actual.get("edits") == actual.get("post_edit_checks")
        cells[label] = {
            "status": result["coder_status"],
            "accepted": accepted,
            "topic": row.get("topic"),
            "arm": row.get("arm"),
            "Primary_decision": primary["decision"],
            "reviewer": result["summary"]["reviewer_decision"],
            "independent_pass": result["all_independent_pass"],
            "seconds": result["seconds"],
            "coder_seconds": ledger.get("seconds"),
            "reviewer_seconds": reviewer_seconds,
            "load_seconds": None,
            "coder_counters": actual,
            "reviewer_requests": reviewer_requests,
            "static_focus_requests": sum(
                "CURRENT_STATIC_DIAGNOSTIC\n" in req["messages"][1]["content"]
                for req in requests
            ),
            "coder_tokens": usage(
                sorted(archive.glob("proposal-response-*.json")), "stats"
            ),
            "reviewer_tokens": reviewer_usage,
            "assisted": result["assisted"],
            "protected_drift": result["protected_drift"],
            "Primary_record": str(archive / "review.json"),
        }
    executed = sum(cell["status"] != "NOT_RUN" for cell in cells.values())
    metrics = {
        "registered": len(cells),
        "executed": executed,
        "not_run": len(cells) - executed,
        "accepted": sum(cell["accepted"] for cell in cells.values()),
        "cells": cells,
        "Primary_active_seconds": None,
        "cloud_tokens": None,
        "economic_saving": "not established; no Primary-only paired comparison",
        "counting": "Each cell is separate; no pooling with prior batches. Controlled repairs and new behavior tasks remain distinct.",
    }
    S.save(batch / "metrics.json", metrics)
    print(
        json.dumps(
            {k: metrics[k] for k in ("registered", "executed", "not_run", "accepted")}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch")
    args = parser.parse_args()
    batch = (S.KIT / "benchmarks/work/harness-convergence" / args.batch).resolve()
    assert batch.parent == (S.KIT / "benchmarks/work/harness-convergence").resolve()
    collect(batch)
