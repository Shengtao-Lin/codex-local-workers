"""Read-only-to-models postflight receipts for the approved frozen batch."""

import argparse
from pathlib import Path

import bounded_evidence_support as S
import function_repeat_trial as F


def collect():
    cells = S.read(F.BATCH / "cells.json")
    rows = []
    for cell in F.ORDER:
        row = cells[cell]
        root = Path(row["root"])
        review = (
            root
            / ".agent/tasks"
            / row["identity"]["task_id"]
            / "reviews"
            / ("auto-" + row["identity"]["run_id"])
        )
        records = {}
        for pattern, key in (
            ("phase-response-*.json", "request_stats"),
            ("output-limit-failure-*.json", "diagnostics"),
        ):
            for path in review.glob(pattern):
                number = int(path.stem.rsplit("-", 1)[1])
                data = S.read(path)
                usage = (data.get(key) or {}).get("response_usage")
                if number in records and records[number] != usage:
                    raise ValueError("Conflicting per-request usage")
                records[number] = usage
        report = (
            S.read(root / ".agent/reviewer-report.json")
            if (root / ".agent/reviewer-report.json").exists()
            else {}
        )
        rows.append(
            {
                "cell": cell,
                "Reviewer_decision": report.get("decision"),
                "requests_with_record": len(records),
                "usage_records": sum(isinstance(u, dict) for u in records.values()),
                "prompt_tokens": sum(
                    (u or {}).get("prompt_tokens", 0) for u in records.values()
                )
                if records
                else None,
                "completion_tokens": sum(
                    (u or {}).get("completion_tokens", 0) for u in records.values()
                )
                if records
                else None,
                "output_limits": len(list(review.glob("output-limit-failure-*.json"))),
                "effective_decoding": report.get("reviewer_decoding_experiment"),
                "current_source_sha256": S.sha(root / row["target"]),
            }
        )
    S.save(
        F.BATCH / "live-reviewer-metrics.json",
        {
            "cells": rows,
            "recorded_requests": sum(r["requests_with_record"] for r in rows),
            "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in rows),
            "completion_tokens": sum(r["completion_tokens"] or 0 for r in rows),
            "output_limits": sum(r["output_limits"] for r in rows),
            "semantic_resampling_after_valid_report": 0,
            "counts_limit": "Requests without stats, if any, are not assumed zero usage; Primary cloud/active time unknown. No savings claim.",
        },
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    collect()
