"""Close the nine-proposal diagnostic; no unit acceptance or score rewriting."""

import argparse
import ast
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import repair_representation_diagnostic as D

T, BATCH = D.T, D.BATCH


def close(used):
    fixture = T.read(BATCH / "fixture.json")
    rows = T.read(BATCH / "cells.json")
    grid, adjudications, users = [], [], []
    for name in D.ORDER:
        cell = Path(rows[name]["root"]).parent
        result = T.read(cell / "result.json")
        response = T.read(cell / "response.json")
        request = T.read(cell / "request.json")
        wire_requests = [T.read(p)["body"] for p in sorted((cell / "wire").glob("*-request.json"))
                         if T.read(p)["url"].endswith("/chat/completions")]
        assert len(wire_requests) == 1
        wire = wire_requests[0]
        assert wire["messages"] == request["messages"]
        users.append(wire["messages"][1]["content"])
        assert wire["model"] == "qwen/qwen3-coder-30b" and wire["max_tokens"] == 4096
        assert wire["response_format"]["json_schema"]["strict"] is True
        assert not result["protected_drift"] and not result["accepted_unit"] and not result["complete_chain"]
        stats = response["stats"]
        assert stats["finish_reason"] == "stop"
        arm = name.split("-")[0]
        if arm == "diagnose":
            diagnosis = T.read(cell / "diagnosis.json")
            # These source-backed checks anchor Primary's manual adjudication;
            # this is not an auto semantic judge or a gold injected into prompts.
            assert diagnosis["affected_symbol"] == "check_finite"
            assert "obj" in diagnosis["cause"] and "annotation" in diagnosis["cause"]
            assert "obj" in diagnosis["required_change"] and "annotation" in diagnosis["required_change"]
            adjudications.append({"sample": name, "decision": "correct_narrow_diagnosis",
                "reason": "Correctly attributes Pyright failure to unannotated obj in check_finite and proposes adding its type annotation. Does not change contract/checks or treat passing tests as acceptance.",
                "source_evidence": {"fixture_sha256": T.sha(BATCH / "fixture.json"),
                    "line": fixture["span"]["line"], "quote": fixture["span"]["source"],
                    "actual_check": "reportMissingParameterType"},
                "answer_forwarded_to_other_arms": False})
            layer = {"diagnosis_correct": True, "applied": False}
        else:
            source = (Path(rows[name]["root"]) / fixture["binding"]["path"]).read_text(encoding="utf-8")
            helper = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == "check_finite")
            assert helper.args.args[0].annotation is not None
            checks = T.read(cell / "checks/results.json")
            tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
            assert len(tests) == 12 and not any(t.find("failure") is not None or t.find("error") is not None for t in tests)
            assert result["applied"]
            if arm == "span":
                assert result["checks"] == [0, 0, 0, 0]
                assert source == (BATCH / "snapshot.py").read_text(encoding="utf-8").replace(
                    fixture["span"]["source"], json.loads(response["raw"])["replacement"], 1)
            else:
                assert result["checks"] == [0, 1, 0, 0]
                assert "would be reformatted" in checks[1]["stdout"]
            layer = {"diagnosis_correct": None, "applied": True,
                     "target_type_error_fixed": True, "behavior_tests": "12/12",
                     "all_checks_passed": result["all_checks_passed"]}
        grid.append({**result, **layer, "reported_input_tokens": stats["reported_input_tokens"],
            "reported_output_tokens": stats["response_usage"]["completion_tokens"],
            "finish_reason": stats["finish_reason"],
            "request_sha256": T.sha(cell / "request.json"),
            "raw_response_sha256": T.sha(cell / "response.json")})
    assert len(set(users)) == 1 and users[0] == fixture["user_message"]
    T.save(BATCH / "primary-adjudications.json", adjudications)
    T.save(BATCH / "grid-results.json", grid)
    T.save(BATCH / "usage-record-correction.json", {
        "affected_samples": ["whole-3", "span-3", "diagnose-3"],
        "recorded_started_used": 2, "latest_actual_used_observed_before_these_samples": used,
        "reason": "Launcher retained previous --used2 although the immediately preceding account query returned3. Preserve original started records and append correction rather than edit history.",
        "threshold_compliance_changed": False, "weekly_used_ceiling": 15})
    pins = T.read(BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    baseline = T.read(BATCH / "baseline.json")
    permitted = {"benchmarks/repair_representation_diagnostic.py", "tests/test_repair_representation.py",
                 "docs/local-model-harness-convergence-plan.md"}
    drift = [p for p, sha in baseline["files"].items() if p not in permitted and T.sha(D.KIT / p) != sha]
    assert not drift
    T.save(BATCH / "preservation.json", {"inherited_drift": drift, "all_frozen_pins_match": True,
        "same_user_message_sha256": hashlib.sha256(users[0].encode()).hexdigest(),
        "all_nine_same_input": True, "production_changes": False, "siblings": "read-only",
        "commit_push": False, "old_failures_unchanged": True, "gold_in_model_input": False})
    T.save(BATCH / "metrics.json", {"actual_chat_requests": 9, "compatibility_probes": 0,
        "diagnosis": {"correct": 3, "total": 3},
        "whole": {"applied": 3, "type_error_fixed": 3, "all_checks_passed": 0, "total": 3},
        "span": {"applied": 3, "type_error_fixed": 3, "all_checks_passed": 3, "total": 3},
        "reviewer_calls": 0, "complete_chains": 0, "accepted_units": 0,
        "reported_input_tokens": sum(g["reported_input_tokens"] for g in grid),
        "reported_output_tokens": sum(g["reported_output_tokens"] for g in grid),
        "wall_seconds": sum(g["seconds"] for g in grid), "primary_active_seconds": None, "cloud_tokens": None,
        "weekly_used_start": 2, "weekly_used_end": used, "weekly_used_ceiling": 15,
        "usage_interpretation": "Account-wide increase, not measured experiment-specific cloud token cost"})
    T.save(BATCH / "decision.json", {"status": "PASS_NARROW_REPRESENTATION_DIAGNOSTIC",
        "registered": 9, "executed": 9, "not_run": 0,
        "goal_complete": False, "product_release": False, "fresh_transfer_credit": False,
        "conclusion": "On identical anchored input the model correctly explains the error3/3; both repair arms fix the actual type defect3/3, but whole-function output regresses Ruff formatting3/3 while span-only output passes all fixed checks3/3. Supports edit-granularity burden for this exposed static repair, not a claim of global model inability.",
        "confounds_and_limits": "All arms have the same added error-derived span hint, absent from the preceding closed scheduling batch. Do not attribute cross-batch type-repair improvement solely to output format. Single exposed task, correlated low-temperature repeats, diagnosis output schema differs by design. No Reviewer, end-to-end runtime, fresh task or cost qualification.",
        "weekly_used_end": used, "weekly_used_ceiling": 15,
        "stop_reason": "Fixed nine-proposal diagnostic complete; no extra samples",
        "next_unique_action": "Separately authorize/register a default-off formal loop candidate: exact error-derived header span only after eligible static failure; whole-function initial proposal unchanged; same budgets, guarded formatting, canonical validation and qualified Reviewer. Offline negatives/entry first, then fixed complete-chain repetitions. Unsupported/ambiguous diagnostics must not gain arbitrary edit scope."})
    print(json.dumps(T.read(BATCH / "decision.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
