"""Immutable outcome/feedback audit of the approved fixed scheduling batch."""

import argparse
import ast
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import capture_fixture_support as F
import scheduling_trial as S

T, BATCH = S.T, S.BATCH


def close(used):
    interface = F.load(S.KIT / ".local-agents/proposal-interface.py", "schedule_close_interface")
    rows = T.read(BATCH / "cells.json")
    grid = []
    for name in S.ORDER:
        row = rows[name]
        root = Path(row["root"])
        cell = root.parent
        packet = T.read(root / ".agent/packet.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        requests = [T.read(p) for p in sorted(archive.glob("proposal-request-*.json"))]
        responses = [T.read(p) for p in sorted(archive.glob("proposal-response-*.json"))]
        attempts = [T.read(p) for p in sorted(archive.glob("validation-attempt-*.json"))]
        wires = [T.read(p)["body"] for p in sorted((cell / "wire").glob("*-request.json"))
                 if T.read(p)["url"].endswith("/chat/completions")]
        assert len(wires) == len(requests) == len(responses)
        assert all(w["response_format"]["json_schema"]["name"] == "experimental_whole_function_v1" for w in wires)
        assert all(w["response_format"]["json_schema"]["strict"] is True for w in wires)
        assert len(attempts) == 3
        assert all(json.loads(r["raw"]).keys() == {"replacement"} for r in responses)
        events = [json.loads(line) for line in (archive / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        assert sum(e["event"] == "autoformat" for e in events) == 1
        result = T.read(cell / "result.json")
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        assert len(tests) == 12 and not any(t.find("failure") is not None or t.find("error") is not None for t in tests)
        assert not result["protected_drift"] and not result["eligible_for_primary"]
        checks = T.read(cell / "checks/results.json")
        assert "reportMissingParameterType" in checks[3]["stdout"]
        is_new = name.startswith("new-")
        if is_new:
            assert len(requests) == 2
            facts = interface.restore_literal(requests[1]["messages"][1]["content"])
            assert "reportMissingParameterType" in json.dumps(facts["validation_failure"])
            assert "Type annotation is missing for parameter" in json.dumps(facts["validation_failure"])
            assert "def check_finite(obj):" in facts["target"]["source"]
            assert requests[1]["binding"]["source"] == facts["target"]["source"]
            replacement = json.loads(responses[1]["raw"])["replacement"]
            helper = next(n for n in ast.walk(ast.parse(replacement))
                          if isinstance(n, ast.FunctionDef) and n.name == "check_finite")
            assert helper.args.args[0].annotation is None
            assert attempts[2]["validation"]["configured_checks"][0]["id"] == "ruff-format"
            assert attempts[2]["validation"]["configured_checks"][0]["status"] == "failed"
            diagnosis = "Type error/source displayed in second request; second proposal keeps missing annotation and reintroduces formatting failure. Feedback-to-repair failed in this bounded protocol."
        else:
            assert len(requests) == 1
            assert attempts[1]["validation"]["focused_tests"]["stage"] == "diff_quality"
            diagnosis = "Original schedule consumes third slot after autoformat, before model can respond to the type error."
        # Exact packet facts/test inputs match across arms except run identity;
        # first validation excerpts naturally contain different archive paths.
        summary = "Fixed scheduling diagnostic replan: " + diagnosis
        record = S.O.M.command([S.O.M.PYTHON, "-B", root / ".local-agents/record-review.py",
            "--repo", root, "--task-id", packet["task_id"], "--run-id", packet["run_id"],
            "--decision", "replan", "--summary", summary], root)
        assert record["exit_code"] == 0, record
        T.save(cell / "primary-decision.json", {"decision": "replan", "summary": summary,
            "canonical_review": str(archive / "review.json"), "sha256": T.sha(archive / "review.json"),
            "semantic_takeover": False})
        grid.append({"case": name, **result, "diagnosis": diagnosis,
            "actual_chat_requests": len(requests), "validation_attempts": 3,
            "formatter_commands": 1,
            "focused_pytest_executions": sum(a["validation"]["focused_tests"].get("status") != "not_run" for a in attempts),
            "private_and_visible_tests": "12/12", "canonical_archive": str(archive),
            "reported_input_tokens": [r["stats"]["reported_input_tokens"] for r in responses],
            "finish_reasons": [r["stats"]["finish_reason"] for r in responses],
            "second_request_type_error_visible": is_new,
            "second_proposal_fixed_type_error": False if is_new else None})
    for n in (1, 2, 3):
        a, b = [T.read(Path(rows[f"{arm}-{n}"]["root"]) / ".agent/packet.json") for arm in ("old", "new")]
        a.pop("run_id"), b.pop("run_id")
        assert a == b
        a, b = [T.read(Path(rows[f"{arm}-{n}"]["root"]) / ".agent/config.json") for arm in ("old", "new")]
        a.pop("experimental_prevalidation_format"), b.pop("experimental_prevalidation_format")
        assert a == b
    T.save(BATCH / "grid-results.json", grid)
    baseline = T.read(BATCH / "baseline.json")
    permitted = {"benchmarks/scheduling_trial.py", "benchmarks/scheduled_coder_entry.py",
                 "benchmarks/scheduled_unit_entry.py", "docs/local-model-harness-convergence-plan.md"}
    drift = [p for p, sha in baseline["files"].items() if p not in permitted and T.sha(S.KIT / p) != sha]
    pins = T.read(BATCH / "freeze.json")["pins"]
    assert not drift and all(T.sha(p) == sha for p, sha in pins.items())
    T.save(BATCH / "preservation.json", {"inherited_drift": drift, "all_frozen_pins_match": True,
        "production_runtime_modified": False, "sibling_writes": False, "commit_push": False,
        "old_failures_unchanged": True, "paired_contracts_and_configs_verified": True})
    T.save(BATCH / "metrics.json", {"actual_coder_requests": sum(g["actual_chat_requests"] for g in grid),
        "reviewer_calls": 0, "old_complete_chains": "0/3", "new_complete_chains": "0/3",
        "old_request_counts": [1, 1, 1], "new_request_counts": [2, 2, 2],
        "old_validation_slots": [3, 3, 3], "new_validation_slots": [3, 3, 3],
        "old_focused_pytest_executions": [2, 2, 2], "new_focused_pytest_executions": [3, 3, 3],
        "effective_type_repairs_after_visible_error": "0/3", "formatting_regressions_on_second_proposal": "3/3",
        "wall_seconds": sum(g["seconds"] for g in grid),
        "primary_active_seconds": None, "cloud_tokens": None,
        "weekly_used_start": 2, "weekly_used_end": used, "weekly_used_ceiling": 15})
    T.save(BATCH / "decision.json", {"status": "HOLD_FIXED_COMPARISON_COMPLETE", "registered": 6,
        "executed": 6, "not_run": 0, "goal_complete": False, "product_release": False,
        "fresh_transfer_credit": False,
        "conclusion": "New schedule removes the no-feedback opportunity blocker, but actual model fails to repair the visible missing parameter annotation in all3 repetitions and regenerates unformatted source. Both arms0/3 full chain. No evidence of JSON/patch/handoff/context/HTTP400 failure here; Reviewer untested.",
        "stop_reason": "Authorized fixed comparison reached clear negative conclusion; no in-batch changes, not usage exhaustion",
        "weekly_used_end": used, "weekly_used_ceiling": 15,
        "next_unique_recommendation": "Do not increase budgets or repeat this candidate. Isolate error comprehension from whole-function regeneration using an independently registered minimal-repair diagnostic before deciding the next harness change; keep this task exposed and all original acceptance constraints."})
    print(json.dumps(T.read(BATCH / "decision.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", required=True, type=int)
    close(parser.parse_args().used)
