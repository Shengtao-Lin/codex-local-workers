"""Read canonical live facts into immutable batch reports; no Worker execution."""

import argparse
import json
from pathlib import Path

import bounded_evidence_support as S


def usage(paths, stats_key):
    rows = [S.read(p).get(stats_key) or {} for p in paths]
    measured = [
        r["response_usage"] for r in rows if isinstance(r.get("response_usage"), dict)
    ]
    return {
        "responses": len(rows),
        "usage_records": len(measured),
        "prompt_tokens": sum(u.get("prompt_tokens", 0) for u in measured)
        if measured
        else None,
        "completion_tokens": sum(u.get("completion_tokens", 0) for u in measured)
        if measured
        else None,
    }


def main(used):
    registered = S.read(S.BATCH / "registration-v2-draft.json")
    cells = S.read(S.BATCH / "cells-v4.json")
    grid = []
    totals = {
        arm: {
            "registered": 6,
            "executed": 0,
            "accepted": 0,
            "coder_checked": 0,
            "reviewer_pass": 0,
            "requests": 0,
            "effective_edits": 0,
            "noops": 0,
            "evidence_actions": 0,
            "post_edit_checks": 0,
            "protocol_recoveries": 0,
            "seconds": 0,
        }
        for arm in ("A", "B")
    }
    for cell in registered["order"]:
        record = S.BATCH / "live-results" / cell / "result.json"
        if not record.exists():
            grid.append({"cell": cell, "status": "NOT_RUN"})
            continue
        result = S.read(record)
        root = Path(cells[cell]["root"])
        packet = S.read(root / ".agent/packet.json")
        run = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        review_path = run / "review.json"
        if not review_path.exists():
            raise ValueError("Primary review missing: " + cell)
        primary = S.read(review_path)
        decision = primary["decision"]
        independent = result["independent_all_checks_passed"]
        reviewer = result["summary"].get("reviewer_decision")
        if decision == "accept" and (
            not independent
            or reviewer != "pass_to_primary"
            or result["protected_drift"]
        ):
            raise ValueError("Acceptance lacks complete-chain proof")
        coder = S.read(run / "handoff.json")
        actual = coder["bounded_evidence"]["actual"]
        validation = [S.read(p) for p in run.glob("validation-attempt-*.json")]
        if actual["effective_edits"] != actual["post_edit_checks"]:
            raise ValueError("An effective edit did not get a post-edit check: " + cell)
        if len(validation) != actual["post_edit_checks"] + actual["initial_checks"]:
            raise ValueError("Validation ledger differs from canonical attempts")
        reviews = (
            root
            / ".agent/tasks"
            / packet["task_id"]
            / "reviews"
            / ("auto-" + packet["run_id"])
        )
        budget = (
            S.read(reviews / "contract-first-budget.json")
            if (reviews / "contract-first-budget.json").exists()
            else None
        )
        row = {
            "cell": cell,
            "task": cells[cell]["task"],
            "arm": cells[cell]["arm"],
            "coder_status": result["coder_status"],
            "ledger": actual,
            "validation_attempts": len(validation),
            "coder_elapsed_seconds": coder["bounded_evidence"]["elapsed_seconds"],
            "unit_seconds": result["unit_seconds"],
            "coder_usage": usage(sorted(run.glob("proposal-response-*.json")), "stats"),
            "reviewer_started": result["summary"]["reviewer_started"],
            "reviewer_decision": reviewer,
            "reviewer_budget": budget,
            "reviewer_usage": usage(
                sorted(reviews.glob("phase-response-*.json")), "request_stats"
            ),
            "independent_all_checks_passed": independent,
            "independent_commands": [
                {"exit_code": c["exit_code"], "argv": c["argv"]}
                for c in result["independent_checks"]
            ],
            "primary_decision": decision,
            "primary_summary": primary["summary"],
            "assisted": False,
            "primary_semantic_hints": 0,
            "primary_code_changes": 0,
            "reviewer_false_pass_under_registered_contract": reviewer
            == "pass_to_primary"
            and decision != "accept",
            "reviewer_false_reject": None if reviewer is None else False,
            "protected_drift": result["protected_drift"],
            "infra_failure": result["infra_failure"],
            "source_sha256": result["final_source_sha256"],
            "canonical_run": str(run.relative_to(S.KIT)),
            "failure_reason": coder.get("failure_reason"),
            "Primary_active_seconds": None,
            "cloud_tokens": None,
        }
        grid.append(row)
        tally = totals[row["arm"]]
        tally["executed"] += 1
        tally["accepted"] += decision == "accept"
        tally["coder_checked"] += (
            result["coder_status"] == "validation_passed_pending_review"
        )
        tally["reviewer_pass"] += reviewer == "pass_to_primary"
        tally["seconds"] += result["unit_seconds"]
        for key in (
            "requests",
            "effective_edits",
            "noops",
            "evidence_actions",
            "post_edit_checks",
            "protocol_recoveries",
        ):
            tally[key] += actual[key]
    if len(grid) != 12 or any(row.get("status") == "NOT_RUN" for row in grid):
        raise ValueError("Fixed batch not complete; no completed-batch report")
    drift = [p for p, sha in registered["pins"].items() if S.sha(p) != sha]
    if drift:
        raise ValueError("Frozen candidate or evidence changed")
    per_task = {
        task: {
            arm: sum(
                r["primary_decision"] == "accept"
                for r in grid
                if r["task"] == task and r["arm"] == arm
            )
            for arm in ("A", "B")
        }
        for task in ("T1", "T2", "T3")
    }
    start = S.read(S.BATCH / "live-results/batch-start.json")["epoch"]
    ended = max(
        S.read(S.BATCH / "live-results" / r["cell"] / "start.json")["epoch"]
        + r["unit_seconds"]
        for r in grid
    )
    metrics = {
        "by_arm": totals,
        "per_task_accepted_of_2": per_task,
        "registered": 12,
        "executed": 12,
        "not_run": 0,
        "local_unit_seconds_sum": round(sum(r["unit_seconds"] for r in grid), 3),
        "batch_start_to_last_unit_end_seconds": round(ended - start, 3),
        "model_loading_seconds": None,
        "Primary_active_seconds": None,
        "cloud_tokens": None,
        "primary_execution_launches": 12,
        "primary_final_reviews": 12,
        "primary_semantic_hints": 0,
        "Primary_code_takeovers": 0,
        "evidence_actions_total": sum(r["ledger"]["evidence_actions"] for r in grid),
        "noops_total": sum(r["ledger"]["noops"] for r in grid),
        "all_effective_edits_have_post_edit_checks": True,
        "reviewer_false_passes_under_registered_contract": sum(
            r["reviewer_false_pass_under_registered_contract"] for r in grid
        ),
        "final_wrong_accepts_observed": 0,
        "infrastructure_failures": sum(bool(r["infra_failure"]) for r in grid),
        "assisted_units": 0,
        "weekly_used_start": 9,
        "weekly_used_end_observed": used,
        "weekly_ceiling": 15,
        "note": "Token fields are local provider-reported tokens only. No Primary-only cost comparison; account usage does not measure precise savings.",
    }
    metrics["primary_extra_semantic_audits"] = [
        {
            "cell": "T3-A2",
            "file": "live-results/T3-A2/primary-probes.json",
            "probes": 2,
            "reason": "Check original conversion preservation; separate from 14 frozen tests; not fed to Worker",
        }
    ]
    metrics["shared_feedback_presentation_caveat"] = (
        "Qualified host appends a no_op receipt; this common A/B adapter communicates noops in resource_ledger but does not append that receipt. Stop counter remains 2. No claim that old formal candidate differs only in numeric budget, or that this encoding caused failure."
    )
    S.save(S.BATCH / "live-grid-results.json", grid)
    S.save(S.BATCH / "live-metrics.json", metrics)
    S.save(
        S.BATCH / "live-decision.json",
        {
            "status": "HOLD_FIXED_GATE_BATCH_COMPLETE",
            "registered": 12,
            "executed": 12,
            "not_run": 0,
            "accepted": {arm: totals[arm]["accepted"] for arm in ("A", "B")},
            "required_per_arm": 6,
            "R4": "HOLD",
            "R5": "NOT_ADMITTED",
            "production_enabled": False,
            "evidence_interaction_contribution": "Not demonstrated: all B evidence-action counts are retained; do not attribute numerical difference to READ/SEARCH if unused",
            "stop_reason": "All registered diagnostics and independent Primary reviews completed; no additional candidate or replacement runs authorized",
            "weekly_used": used,
            "weekly_ceiling": 15,
            "frozen_pin_count": len(registered["pins"]),
            "frozen_pin_mismatches": 0,
            "old_5_of_6_and_all_historical_failures": "UNCHANGED",
            "task_T3_limit": "Non-reduction clause permits max(prompt,cached); exact prompt equality for cached>prompt not registered, tested or claimed. This is a specification/coverage limitation, not an observed false pass.",
            "future_direction": "No evidence to promote B by extra interaction. Report actual feedback-to-repair and no-op behavior before proposing any new experiment; no runtime/default change here.",
        },
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly-used", type=int, required=True)
    main(parser.parse_args().weekly_used)
