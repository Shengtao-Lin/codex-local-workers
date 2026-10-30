"""Close ordinary rework separately from the failed fixed qualification gate."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import metadata_cycle_recovery as R


def close(used):
    T, batch = R.T, R.BATCH
    row = T.read(batch / "cells.json")["rework-1"]
    root = Path(row["root"])
    cell = root.parent
    packet = T.read(root / ".agent/packet.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    result = T.read(cell / "result.json")
    responses = list(archive.glob("proposal-response-*.json"))
    assert len(responses) == 1
    attempts = [T.read(p) for p in sorted(archive.glob("validation-attempt-*.json"))]
    assert len(attempts) == 3
    assert attempts[1]["validation"]["configured_checks"][0]["id"] == "ruff-format"
    assert attempts[1]["validation"]["configured_checks"][0]["status"] == "failed"
    last_check = attempts[2]["validation"]["configured_checks"][-1]
    assert last_check["id"] == "ruff-check" and "RUF013" in last_check["output"]
    assert T.read(batch / "independent-full-check.json")["exit_code"] == 0
    tests = ET.parse(batch / "independent-full-junit.xml").findall(".//testcase")
    assert len(tests) == 18 and not any(t.find("failure") is not None or t.find("error") is not None for t in tests)
    assert result["checks"] == [0, 0, 1, 1] and result["reviewer_decision"] is None
    record = R.S.D.S.O.M.command([R.S.D.S.O.M.PYTHON, "-B", root / ".local-agents/record-review.py",
        "--repo", root, "--task-id", packet["task_id"], "--run-id", packet["run_id"],
        "--decision", "replan", "--summary", "Ordinary isolated recovery repaired the confirmed cyclic-input examples (18 tests passed), but introduced RUF013/Optional type errors. Initial+post-edit Ruff-format failure+recursive postformat validation consumed3 slots, so no second proposal saw those errors. No Reviewer/acceptance; retain old formal failure and all new evidence."], root)
    assert record["exit_code"] == 0, record
    T.save(cell / "primary-decision.json", {"decision": "replan", "canonical_review": str(archive / "review.json"),
        "sha256": T.sha(archive / "review.json"), "semantic_takeover": False})
    pins = T.read(batch / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    baseline = T.read(batch / "baseline.json")
    permitted = {"benchmarks/metadata_cycle_recovery.py", "benchmarks/static_span_semantic_probe.py",
                 "benchmarks/static_span_close.py", "docs/local-model-harness-convergence-plan.md"}
    drift = [p for p, sha in baseline["files"].items() if p not in permitted and T.sha(R.KIT / p) != sha]
    assert not drift
    T.save(batch / "preservation.json", {"inherited_drift": drift, "formal_candidate_pins_unchanged": True,
        "earlier_fixed_tests_and_scores_unchanged": True, "new_cycle_test_readonly": True,
        "production_changes": False, "siblings": "read-only", "commit_push": False,
        "own_postclose_scripts_formatted_only": ["static_span_close.py", "static_span_semantic_probe.py"]})
    T.save(batch / "grid-results.json", [{**result, "case": "rework-1", "independent_behavior_tests": "18/18",
        "primary_decision": "replan", "canonical_archive": str(archive), "actual_coder_requests": 1,
        "validation_attempts": 3, "ruff_error_seen_by_model": False}])
    T.save(batch / "decision.json", {"status": "HOLD_STATIC_VALIDATION", "registered": 1, "executed": 1,
        "not_run": 0, "goal_complete": False, "product_release": False, "original_formal_gate_restored": False,
        "conclusion": "Same frozen harness; model repaired confirmed cycle cases but added implicit Optional. A non-whitespace Ruff formatting failure still consumes a slot before one-shot formatter recursive revalidation. Final static error not shown to a second proposal; do not call this evidence that the model cannot repair RUF013.",
        "weekly_used_start": 3, "weekly_used_end": used, "weekly_used_ceiling": 15,
        "next_unique_recommendation": "Authorize an independently frozen mechanical candidate that unifies guarded formatting preparation instead of separate whitespace/Ruff-format branches, then normalizes supported static header diagnostics without increasing scope or budgets. Offline negative/cost controls first; do not patch the closed candidate or promote the local partial success."})
    print(json.dumps(T.read(batch / "decision.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
