"""Create-only compact closure from canonical current trial evidence."""

import argparse
import json
from datetime import datetime
from pathlib import Path

import bounded_evidence_support as S

BASE = S.KIT / "benchmarks/work/harness-convergence"


def project(used, batch_name="strata-project-20261023-2"):
    assert batch_name in {"strata-project-20261023-2", "strata-boundary-20261023-3"}
    batch = BASE / batch_name
    reg = S.read(batch / "registration.json")
    rows = []
    for cell in reg["order"]:
        result = S.read(batch / "live-results" / cell / "result.json")
        root = batch / "cells" / cell / "isolated"
        identity = batch.name + "-" + cell
        review = S.read(
            root / ".agent/tasks" / identity / "runs" / identity / "review.json"
        )
        coder = S.read(root / ".agent/unit-report.json")
        reviewer_path = root / ".agent/reviewer-report.json"
        reviewer = S.read(reviewer_path) if reviewer_path.exists() else {}
        row = {
            "cell": cell,
            "coder": result["coder_status"],
            "ledger": result["ledger"],
            "Reviewer": result["summary"]["reviewer_decision"],
            "Reviewer_model_calls": reviewer.get("reviewer_model_calls"),
            "configured_independent_checks_pass": result["all_independent_pass"],
            "Primary": review["decision"],
            "Primary_summary": review["summary"],
            "protected_drift": result["protected_drift"],
            "seconds": result["seconds"],
            "final_source_sha256": result["final_source_sha256"],
        }
        assert coder["identity"]["run_id"] == identity
        totals = {k: 0 for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
        for path in (root / ".agent/strata-wire").glob("*.response.json"):
            usage = S.read(path).get("usage", {})
            for key in totals:
                totals[key] += usage.get(key, 0)
        row["local_usage"] = totals
        rows.append(row)
    accepted = sum(r["Primary"] == "accept" for r in rows)
    metrics = {
        "registered": 4,
        "executed": len(rows),
        "accepted": accepted,
        "not_run": 4 - len(rows),
        "rows": rows,
        "seconds": sum(r["seconds"] for r in rows),
        "Primary_active_seconds": None,
        "cloud_tokens": None,
        "cold_load_seconds": None,
        "local_model_switches": 0,
        "protected_test_assistance": batch_name == "strata-boundary-20261023-3",
        "weekly_used_observed": used,
        "weekly_stop": 40,
    }
    S.save(batch / "metrics.json", metrics)
    S.save(
        batch / "decision.json",
        {
            "status": (
                "PASS_EXPOSED_PROTECTED_REGRESSION"
                if batch_name == "strata-boundary-20261023-3"
                else "PASS_NARROW_PROJECT_BATCH"
            )
            if accepted == 4
            else "HOLD_FULL_CONTRACT",
            "registered": 4,
            "executed": len(rows),
            "accepted": accepted,
            "not_run": 4 - len(rows),
            "gate_unchanged": True,
            "historical_failures_preserved": True,
            "model_profile": "thinking-v1; actual128K/client64K,total12288/thinking4096,medium,official thinking sampling",
            "limits": "Two exposed task contracts, repeats not holdouts; no proof of causal context gain or cloud savings. Boundary batch adds Primary-authored protected regression cases and is test-assisted, not an unassisted capability gain. Old batches unchanged. No global switching, Coordinator or production enablement.",
            "metrics": "metrics.json",
            "weekly_used_observed": used,
            "weekly_stop": 40,
        },
    )
    print(
        json.dumps(
            {"accepted": accepted, "executed": len(rows), "seconds": metrics["seconds"]}
        )
    )


def explorer(batch_name, used):
    assert batch_name in {f"strata-explorer-20261023-{i}" for i in range(1, 6)}
    batch = BASE / batch_name
    rows = []
    for cell, registered in S.read(batch / "registration.json")["rows"].items():
        root = Path(registered["root"])
        report = S.read(root / ".agent/explorer-report.json")
        events = [
            json.loads(line)
            for line in (root / report["diagnostic_log"])
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        usage = {
            key: 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        }
        responses = list((root / ".agent/strata-wire").glob("*.response.json"))
        for path in responses:
            observed = S.read(path).get("usage", {})
            for key in usage:
                usage[key] += observed.get(key, 0)
        rows.append(
            {
                "cell": cell,
                "runtime_status": report["status"],
                "failure_reason": report.get("failure_reason"),
                "budget": report["budget_usage"],
                "provider_requests": len(
                    list((root / ".agent/strata-wire").glob("*.request.json"))
                ),
                "local_usage": usage,
                "seconds": (
                    datetime.fromisoformat(events[-1]["at"])
                    - datetime.fromisoformat(events[0]["at"])
                ).total_seconds(),
                "protected_drift": S.read(batch / cell / "protected-check.json")[
                    "drift"
                ],
            }
        )
    S.save(
        batch / "metrics.json",
        {
            "registered": len(rows),
            "executed": len(rows),
            "rows": rows,
            "weekly_used_observed": used,
            "weekly_stop": 40,
            "Primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    print(json.dumps({"batch": batch_name, "rows": rows}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["project", "explorer"])
    parser.add_argument("--batch")
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "project":
        project(args.weekly_used, args.batch or "strata-project-20261023-2")
    else:
        explorer(args.batch, args.weekly_used)
