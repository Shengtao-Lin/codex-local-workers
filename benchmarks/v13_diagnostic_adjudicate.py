"""Seal a completed failed diagnostic cohort; never infer model success."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys

from capability_fit import KIT, WORK, write


def seal(weekly_used):
    roots = sorted((WORK / "runs/complex-v2").glob("dgcmp2-*-d1/*"))
    assert len(roots) == 8
    rows = []
    for root in roots:
        result = json.loads((root / "result.json").read_text(encoding="utf-8"))
        assert (
            result["coder_status"] == "failed" and not result["implementation_passed"]
        )
        assert result["protected_inputs_unchanged"]
        experiment = json.loads((root / "experiment.json").read_text(encoding="utf-8"))
        coder = json.loads((root / ".agent/coder.json").read_text(encoding="utf-8"))
        archives = list((root / ".agent/tasks").glob("*/runs/*"))
        assert len(archives) == 1
        archive = archives[0]
        events = [
            json.loads(line)
            for line in (archive / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        requests = [e["facts"] for e in events if e["event"] == "model_request"]
        assert requests
        first = json.loads(
            (archive / "validation-attempt-1.json").read_text(encoding="utf-8")
        )["validation"]
        assert first["focused_tests"]["status"] == "failed"
        checks = first["configured_checks"]
        expected = 2 if experiment["failed_test_diagnostics"] else 0
        assert len(checks) == expected
        if expected:
            assert "F401" in json.dumps(checks)
        source = (root / "src/product/target.py").read_text(encoding="utf-8")
        row = {
            "workspace": str(root),
            "case": result["case"],
            "arm": result["arm"],
            "repetition": result["repetition"],
            "seconds": result["seconds"],
            "static_pass": result["static_checks_passed"],
            "unused_math_removed": "import math" not in source,
            "baseline_static_checks_executed": len(checks),
            "failure_reason": coder.get("failure_reason"),
            "tool_errors": sum(e["event"] == "tool_error" for e in events),
            "max_reported_context": max(
                r.get("reported_context_utilization", 0) or 0 for r in requests
            ),
            "diff_sha256": hashlib.sha256(
                (archive / "cumulative.diff").read_bytes()
            ).hexdigest(),
        }
        summary = (
            "Diagnostic comparison: reject incomplete semantic implementation. "
            + (
                "Rollback cancellation may replace original failure; suppress(Exception) remains."
                if result["case"] == "diag-save-cancel"
                else "Protected recursive deletion/alias boundaries remain failing; no feature acceptance."
            )
        )
        subprocess.run(
            [
                sys.executable,
                str(KIT / ".local-agents/record-review.py"),
                "--repo",
                str(root),
                "--task-id",
                archive.parent.parent.name,
                "--run-id",
                archive.name,
                "--decision",
                "replan",
                "--summary",
                summary,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        rows.append(row)
    write(
        WORK / "conclusion-v13diag-comparison-1.json",
        {
            "decision": "NO_REPEATABLE_SEMANTIC_GAIN_STOP_DIAGNOSTIC_COMPARISON_DIRECTION",
            "schedule_complete": True,
            "coder_calls": 8,
            "reviewer_calls": 0,
            "explorer_calls": 0,
            "coordinator_calls": 0,
            "infrastructure_failures": 0,
            "full_implementation_passed": {"current": "0/4", "candidate": "0/4"},
            "protected_inputs_unchanged": "8/8",
            "primary_decisions": "8 replan",
            "rows": rows,
            "weekly_used": weekly_used,
            "weekly_ceiling": 40,
            "cloud_tokens": None,
            "primary_active_time": None,
            "v2_1_gate_passed": False,
            "limitations": [
                "Two exposed development families, not unseen qualification",
                "Static command results archived; model consumption is not directly observable",
                "All failed Coder calls; Reviewer ability unassessed",
                "Elapsed time is failed Coder workflow only, not accepted feature cost",
            ],
            "next": "Keep accepted opt-in diagnosis fix. Stop generic prompt/budget tinkering; seek explicit product scope decision before a narrower qualification cohort.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weekly-used", type=float, required=True)
    seal(parser.parse_args().weekly_used)
