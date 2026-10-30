"""Independent closed-batch receipts; retain failures and do not adopt ordering."""

from datetime import datetime
from pathlib import Path

import bounded_evidence_support as S
import failure_priority_trial as T


def close():
    registration = S.read(T.BATCH / "registration.json")
    assert all(S.sha(p) == sha for p, sha in registration["pins"].items())
    rows = S.read(T.BATCH / "cells.json")
    results = {}
    for cell in T.ORDER:
        row = rows[cell]
        root = Path(row["root"])
        identity = row["identity"]
        task = root / ".agent/tasks" / identity["task_id"]
        run = task / "runs" / identity["run_id"]
        result = S.read(T.BATCH / "live-results" / cell / "result.json")
        primary = S.read(run / "review.json")
        accepted = primary["decision"] == "accept"
        if accepted:
            assert (
                result["all_independent_pass"]
                and result["summary"]["reviewer_decision"] == "pass_to_primary"
            )
        assert not result["protected_drift"] and not result["assisted"]
        responses = [
            S.read(p)["stats"] for p in sorted(run.glob("proposal-response-*.json"))
        ]
        local_usage = {
            "coder": {
                key: sum(r["response_usage"][key] for r in responses)
                for key in ("prompt_tokens", "completion_tokens")
            }
        }
        review = task / "reviews" / ("auto-" + identity["run_id"])
        review_seconds = None
        reviewer_requests = 0
        if review.exists():
            responses = [
                S.read(p)["request_stats"]
                for p in sorted(review.glob("phase-response-*.json"))
            ]
            local_usage["reviewer"] = {
                key: sum(r["response_usage"][key] for r in responses)
                for key in ("prompt_tokens", "completion_tokens")
            }
            budget = S.read(review / "contract-first-budget.json")
            reviewer_requests = budget["actual_requests"]
            events = [
                __import__("json").loads(line)
                for line in (review / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            times = {e["event"]: datetime.fromisoformat(e["at"]) for e in events}
            review_seconds = (
                times["review_completed"] - times["review_prepared"]
            ).total_seconds()
        results[cell] = {
            "accepted": accepted,
            "Primary_decision": primary["decision"],
            "coder_status": result["coder_status"],
            "reviewer": result["summary"]["reviewer_decision"],
            "seconds": result["seconds"],
            "coder_loop_seconds": result["ledger"]["seconds"],
            "reviewer_prepared_to_completed_seconds": review_seconds,
            "load_seconds": "unknown",
            "coder_counters": result["ledger"]["actual"],
            "reviewer_requests": reviewer_requests,
            "local_usage": local_usage,
            "assisted": False,
            "protected_drift": [],
            "primary_record": str(run / "review.json"),
        }
    arms = {
        arm: {
            "registered": 2,
            "executed": 2,
            "accepted": sum(
                v["accepted"] for k, v in results.items() if k.startswith(arm)
            ),
        }
        for arm in ("A", "B")
    }
    assert arms["A"]["accepted"] == 1 and arms["B"]["accepted"] == 0
    S.save(
        T.BATCH / "metrics.json",
        {
            "cells": results,
            "arms": arms,
            "Primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "economic_saving": "not established",
        },
    )
    S.save(
        T.BATCH / "decision.json",
        {
            "status": "REJECT_FAILURE_PRIORITY_CANDIDATE",
            "arms": arms,
            "adopted": False,
            "reason": "Failure-first ordering had no observed gain: B0/2 vs A1/2; fixed B2/2/improvement gate not met. This small exposed-draft diagnostic does not estimate a general causal effect.",
            "original_batch": "prepared-slice-live-20261022-1 remains0/2; repair controls are separate and do not erase first attempts",
            "confirmed": [
                "Same correct reference is allowed by editor/validation/handoff offline for all four cells",
                "At least one unchanged-renderer fresh-context recovery produced exact type checks with no Primary hint, then fresh Reviewer and full independent acceptance",
                "Other three cells proposed unchanged broken source twice and stopped; no safety bypass, no false acceptance, no Reviewer invocation for failed checks",
                "Actual requests retain all facts and byte-length; reordering alone is not supported as an improvement",
            ],
            "interpretation": "Failure is unreliable semantic correction after known counterexamples, not inability to apply the permitted fix, missing repair-check credit, or observed context overflow. A1 disproves blanket impossibility; it does not prove reliable recovery or a general restart policy.",
            "confounds": [
                "One exposed task with two different failed drafts",
                "Fresh-call starting draft, initial-check state and available recovery credits differ from original attempts",
                "Sampling variation and different draft complexity; small sample, no universal model-capacity claim",
            ],
            "action": "Keep current production renderer/defaults. Do not add further prompt-order variants or retries on this task. Keep the deterministic installed preparation improvement only.",
            "general_production": "HOLD",
            "type_sensitive_message_id_family": "NOT_QUALIFIED",
            "weekly_used_observed": 42,
            "weekly_stop": None,
            "stop_reason": "All fixed cells complete; new bounded optimization rejected on evidence, no pending batch and no budget-stop claim",
            "preserved": "All failed drafts, requests, checks, per-run Primary decisions and old denominators retained; no commit/push or sibling source writes",
        },
    )
    S.save(
        T.BATCH / "handoff.json",
        {
            "current_user_authority": "Autonomous in-scope analysis/optimization; temporary no weekly stop; existing models/single residency/sibling-readonly/no commit-push/default preservation remain",
            "adopted_product_change": {
                "entry": ".local-agents/local-bounded-prepare.py",
                "controls": "preparation-entry-20261022-1:745 full regression,27 focused; overlapping counts",
                "effect": "Create-only assembly of approved capture inputs, exact packet copy and run-specific config hash. Preview executes nothing. No semantic planning, automatic qualification or acceptance.",
            },
            "new_live_results": {
                "prepared_slice": "0/2 on one new behavior; check gate rejected before Reviewer",
                "exposed_repair_control_A": "1/2 accepted",
                "exposed_repair_ordering_B": "0/2, rejected candidate",
                "do_not_pool": True,
            },
            "design_judgment": "Keep host-owned versioning/application/checking and fresh independent review. Stop treating setup errors, semantic failures and review reliability as one score. Simplifying setup helps product usability but does not establish reliable correction on type-sensitive priorities.",
            "next_direction": "Preserve named-family supervised use; unknown/type-sensitive compatibility work needs Primary classification. Any future recovery policy must be separately bounded and validated on different tasks, not repeated sampling of this exposed case. Coordinator qualification is unchanged and not exercised here.",
            "cost": "One-time preparation CLI and tests separate from recurring detailed contract/test/location/config preparation and final review. In-run Primary semantic hints/implementation takeover0; active time/cloud tokens/load split unknown. Weekly39->42 is shared-account observation, not exact task cost or saving.",
            "pending": [],
        },
    )
    print(arms)


if __name__ == "__main__":
    close()
