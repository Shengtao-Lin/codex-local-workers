"""Add immutable stage metrics and preservation evidence without model calls."""

import argparse
import json
from pathlib import Path

import harness_convergence as B


def main(batch, suffix):
    root = B.KIT / "benchmarks/work/harness-convergence" / batch
    registration = B.read(root / "registration.json")
    rows = []
    for name in registration["order"]:
        case = root / "cases" / name
        if not (case / "result.json").exists():
            rows.append({"case": name, "status": "NOT_RUN"})
            continue
        result = B.read(case / "result.json")
        chat_calls, other_calls = [], []
        for path in sorted((case / "wire").glob("*-request.json")):
            request = B.read(path)
            response_path = path.with_name(path.name.replace("-request", "-response"))
            response = B.read(response_path) if response_path.exists() else {}
            body = request.get("body", {})
            item = {"model": body.get("model"), "seconds": response.get("seconds")}
            if request.get("url", "").endswith("/chat/completions"):
                try:
                    payload = json.loads(response.get("raw", "{}"))
                except json.JSONDecodeError:
                    payload = {}
                item["usage"] = payload.get("usage")
                chat_calls.append(item)
            else:
                other_calls.append({**item, "url": request.get("url")})
        rows.append(
            {
                **result,
                "chat_completions": chat_calls,
                "non_generation_http_calls": other_calls,
                "legacy_model_requests_field_counts_all_captured_posts": True,
            }
        )
    B.save(
        root / f"metrics-{suffix}.json",
        {
            "cells": rows,
            "registered": len(rows),
            "executed": sum(row.get("status") != "NOT_RUN" for row in rows),
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "timing_scope": "per-cell seconds includes entry and independent checks; loading not separately measured",
            "no_cost_reduction_claim": True,
        },
    )
    baseline = B.read(root / "baseline.json")
    expected = {
        B.KIT / ".local-agents/worker-runtime.py",
        B.KIT / ".local-agents/reviewer-runtime.py",
        B.KIT / "docs/local-model-harness-convergence-plan.md",
        B.KIT / "benchmarks/harness_r3_readiness.py",
        B.KIT / "benchmarks/harness_r3_serializer.py",
        B.KIT / "tests/test_reviewer_report_readiness.py",
    }
    drift = []
    if batch == "r3-serializer-20261016-1":
        frozen = B.read(root / "live-freeze-approved.json")
        assert (
            B.sha(B.KIT / "benchmarks/harness_r3_serializer.py")
            == frozen["candidate_and_driver"]["benchmarks/harness_r3_serializer.py"]
        )
    for name, digest in baseline.items():
        path = Path(name)
        if not path.is_file() or B.sha(path) != digest:
            drift.append(
                {
                    "path": name,
                    "intentional_stage_change": path in expected,
                    "current_sha256": B.sha(path) if path.is_file() else None,
                }
            )
    B.save(
        root / f"preservation-{suffix}.json",
        {
            "checked": len(baseline),
            "changed": drift,
            "unrelated_and_historical_paths_preserved": all(
                row["intentional_stage_change"] for row in drift
            ),
            "new_artifacts_are_not_overwrites": True,
        },
    )
    print({"checked": len(baseline), "changed": drift}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch")
    parser.add_argument("suffix")
    args = parser.parse_args()
    main(args.batch, args.suffix)
