"""Primary disposition/closure for the fixed direct-report diagnostic, no workers."""

import subprocess
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import reviewer_direct_trial as D


def main():
    batch = D.BATCH
    registration = S.read(batch / "registration.json")
    assert all(S.sha(p) == h for p, h in registration["pins"].items())
    cells = S.read(batch / "cells.json")
    assert cells == S.read(batch / "material/cells.json")
    json_accept = S.read(batch / "primary/json-1/primary.json")
    assert json_accept["decision"] == "accept"
    row = cells["message-1"]
    root = Path(row["root"])
    name = row["identity"]["run_id"]
    assert row["identity"]["task_id"] == row["identity"]["unit_id"] == name
    review_path = root / ".agent/tasks" / name / "reviews" / ("auto-" + name) / "handoff.json"
    report = S.read(review_path)
    assert report["decision"] == "rework" and [f["id"] for f in report["findings"]] == ["F1"]
    result = S.read(batch / "live-results/message-1/result.json")
    assert not result["all_independent_pass"] and not result["stop_batch"]
    disposition_path = batch / "primary/message-1/disposition.json"
    S.save(disposition_path, {
        "schema_version": 1, "authority": "primary", "identity": report["identity"],
        "report_sha256": S.sha(review_path), "resolution": "cleared",
        "evidence": ["Primary inspected full source/diff and independent two failures: id=1.5 incorrectly returns '1.5' instead of alternate integer ID or complete-message fallback. Both int,float branches cause the violation."],
        "findings": [{"finding_id": "F1", "disposition": "confirmed_defect", "evidence": "Contract explicitly excludes floats; actual source lines13/22 include float, independent test_every_invalid_primary_falls_through[1.5] and test_complete_fallback_and_explicit_compatibility fail."}],
    })
    command = [S.PYTHON, "-B", root / ".local-agents/record-review.py", "--repo", root, "--task-id", name, "--run-id", name, "--decision", "rework", "--summary", "Primary confirms F1 float-ID defect against source and independent failures; no automatic retry in this fixed batch.", "--config", root / ".agent/config.json", "--disposition", disposition_path]
    recorded = T.run(command, root)
    S.save(batch / "primary/message-1/record-command.json", recorded)
    assert recorded["exit_code"] == 0, recorded
    rows = []
    totals = {k: 0 for k in ("model_requests", "edits", "initial_checks", "post_edit_checks", "protocol_recoveries", "noops")}
    reviewer_calls = reviewer_protocol = reviewer_output = 0
    seconds = 0
    for cell in D.ORDER:
        row = cells[cell]
        root = Path(row["root"])
        identity = row["identity"]
        name = identity["run_id"]
        result = S.read(batch / "live-results" / cell / "result.json")
        assert not result["protected_drift"] and not result["interrupted"]
        actual = result["ledger"]["actual"]
        for k in totals:
            totals[k] += actual[k]
        seconds += result["seconds"]
        reviewed = result["summary"]["reviewer_started"]
        review = S.read(root / ".agent/reviewer-report.json") if reviewed else {}
        budget = S.read(root / ".agent/tasks" / name / "reviews" / ("auto-" + name) / "contract-first-budget.json") if reviewed else {}
        reviewer_calls += budget.get("actual_requests", 0)
        reviewer_protocol += budget.get("protocol_errors", 0)
        reviewer_output += budget.get("output_limit_failures", 0)
        rows.append({"cell": cell, "identity": identity, "coder": result["coder_status"], "coder_actual": actual, "independent_complete": result["all_independent_pass"], "reviewer": review.get("decision", "NOT_RUN"), "primary": "accept" if cell == "json-1" else "rework" if reviewed else "replan", "seconds": result["seconds"]})
    preservation = {
        "production_drift": [p for p, h in S.read(batch / "baseline.json")["production"].items() if S.sha(p) != h],
        "origin_drift": [k for k, v in S.read(batch / "origins.json").items() if S.sha(v["path"]) != v["sha256"]],
        "protected_drift": [],
    }
    assert not any(preservation.values())
    S.save(batch / "metrics.json", {"registered": 3, "executed": 3, "not_run": 0, "accepted": 1, "rows": rows, "coder_totals": totals, "reviewer": {"started": 2, "requests": reviewer_calls, "valid_reports": 2, "pass": 1, "rework": 1, "confirmed_true_positive": 1, "observed_false_pass": 0, "protocol_errors": reviewer_protocol, "output_limit_failures": reviewer_output}, "unit_seconds": seconds, "cloud_tokens": "unknown", "Primary_active_seconds": "unknown", "preservation": preservation})
    S.save(batch / "decision.json", {"status": "HOLD_FULL_CHAIN_WITH_PROMISING_REVIEWER_TRANSPORT", "gate": "3/3 complete independent accepts", "accepted": 1, "executed": 3, "reviewer_transport": "2/2 started reviews completed in one request each, no truncations/protocol errors; one correct rework corroborated by independent tests", "coder_failures": ["message accepts float IDs despite explicit contract exclusion; Reviewer and independent checks caught it", "destination uses Unicode isdigit for ASCII-only contract, then emits replacement arrays on three requests; only one effective edit, no Reviewer launch"], "qualification": "No promotion or default enablement. Old6-cell batch remains failed1/6 with5 NOT_RUN; old matrix PASS scope unchanged. New candidate remains experimental.", "next": "Freeze this Reviewer candidate; address Coder recovery separately using archived feedback/schema evidence, not more Reviewer prompting or hidden-test hints. Do not treat 1/3 as stable release."})
    print("Closed 3/3 executions:1 accept,1 confirmed Reviewer rework,1 Coder failure; production/origin drift0")


if __name__ == "__main__":
    main()
