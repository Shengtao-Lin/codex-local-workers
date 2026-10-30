"""Immutable R3 closure after source-origin invalidation; no new model work."""
import argparse
import json

import harness_r3_prepare as P
import harness_r3_run as run

B = P.B


def close(used):
    audit = B.read(P.BATCH / "origin-audit.json")
    assert audit["status"] == "EXPERIMENT_INVALID"
    frozen = B.read(run.BATCH / "live-freeze-approved.json")
    run.assert_files(B.KIT, frozen["candidate_and_driver"])
    origins = {row["cell"]: row for row in audit["cells"]}
    rows, usages = [], []
    for name in P.ORDER:
        case = run.BATCH / "cases" / name
        path = case / "result.json"
        if path.exists():
            row = {**B.read(path), "execution": "EXECUTED_INVALID_START", "quality_evaluation": "INCONCLUSIVE", "source_origin": origins[name]}
            for response in sorted((case / "wire").glob("*-response.json")):
                body = json.loads(B.read(response)["raw"])
                usages.append({"case": name, "response_file": str(response), "usage": body.get("usage"), "finish_reasons": [choice.get("finish_reason") for choice in body.get("choices", [])]})
        else:
            row = {"case": name, "execution": "NOT_RUN", "reason": "Experiment invalidated; no replacement trials in this batch", "source_origin": origins[name]}
            B.save(case / "not-run.json", row)
        rows.append(row)
    sums = {key: sum((item.get("usage") or {}).get(key, 0) for item in usages) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    metrics = {"registered": 12, "executed": 2, "not_run": 10, "valid_capability_units": 0,
               "candidate_registered": 6, "candidate_executed_invalid_start": 1, "candidate_accepted": 0,
               "local_model_requests": len(usages), "local_response_usage": sums, "responses": usages,
               "reviewer_calls": 0, "primary_accepts": 0, "primary_active_seconds": None,
               "cloud_tokens": None, "cost_savings": "not established", "weekly_used_start": 0, "weekly_used_end": used, "weekly_stop": 30,
               "local_cell_seconds": sum(row.get("seconds", 0) for row in rows)}
    B.save(P.BATCH / "grid-results.json", rows)
    B.save(P.BATCH / "metrics.json", metrics)
    B.save(P.BATCH / "decision.json", {
        "stage": "R3", "qualification": "HOLD", "experiment_status": "EXPERIMENT_INVALID",
        "model_capability": "INCONCLUSIVE", "r4_admitted": False,
        "candidate": "host-proposal-v1", "candidate_hashes": frozen["candidate_and_driver"],
        "candidate_unchanged_after_live": True, "registered": 12, "executed": 2, "not_run": 10,
        "candidate_gate": "six of six independently reviewed and Primary accepted, unchanged",
        "prior_r2_qualification": "retained; no old decision overwritten",
        "offline": {"regression_passed": 809, "subtests_passed": 302, "new_protocol_controls": 27, "origin_controls_after_discovery": 3, "installation": "passed", "holdout_reference_mutation_sets": 3},
        "cause": audit["cause"], "responsibility": "Primary experiment preparation and insufficient origin preflight, not LM Studio or demonstrated model incapacity",
        "primary_intervention": "No live semantic hints or source repairs. Post-run origin audit and offline corrected input only.",
        "limitations": ["No valid R3 capability trial", "No live Reviewer handoff", "No presence trial", "No R4 model transfer", "No economic benefit claim"],
        "usage": {"start": 0, "end": used, "stop": 30},
        "stop_reason": "Invalid registered starting state; preserve exposed cells, stop remaining live rather than overwrite/retry",
        "next_action": "Keep candidate/model/contract/check budgets fixed; separately register a corrected batch with upstream pre-run source/test hashes AND expected baseline error predicate enforced before model calls. Preserve this invalid batch.",
        "commit_push": False, "brothers_readonly": True,
    })
    B.save(P.BATCH / "final-environment.json", {
        "weekly_used": used, "stop": 30, "git": B.command(["git", "status", "--short"]),
        "head": B.command(["git", "rev-parse", "HEAD"]), "diff_check": B.command(["git", "diff", "--check"]),
        "residency": B.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
        "siblings": {name: B.command(["git", "-C", str(B.KIT.parent / name), "status", "--short"]) for name in ("agent-runtime-kit", "agent-evaluation-harness")},
    })
    print(json.dumps({"decision": "EXPERIMENT_INVALID / capability INCONCLUSIVE", **{k: metrics[k] for k in ("executed", "not_run", "local_model_requests", "local_response_usage", "weekly_used_end")}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", required=True, type=int)
    close(parser.parse_args().used)
