"""Close the fixed preparation integration batch without rewriting outcomes."""

import ast

import bounded_evidence_support as S
import prepared_slice_trial as T


def close():
    registration = S.read(T.BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in registration["pins"].items())
    assert S.sha(T.ORIGIN) == registration["origin"]["sha256"]
    rows = S.read(T.BATCH / "cells.json")
    metrics = {}
    for cell, row in rows.items():
        root = T.Path(row["root"])
        run = (
            root
            / ".agent/tasks"
            / row["identity"]["task_id"]
            / "runs"
            / row["identity"]["run_id"]
        )
        result = S.read(T.BATCH / "live-results" / cell / "result.json")
        review = S.read(run / "review.json")
        assert review["decision"] == "replan" and not result["all_independent_pass"]
        responses = [S.read(p) for p in sorted(run.glob("proposal-response-*.json"))]
        counters = result["ledger"]["actual"]
        usage = [r["stats"]["response_usage"] for r in responses]
        proposal1 = __import__("json").loads(responses[0]["raw"])["content"]
        proposal2 = __import__("json").loads(responses[1]["raw"])["content"]
        metrics[cell] = {
            "status": "REJECTED_CODER_SEMANTIC_FAILURE",
            "reviewer": "NOT_RUN",
            "final_accept": False,
            "seconds": result["seconds"],
            "ledger": counters,
            "first_two_proposals_same_ast": ast.dump(ast.parse(proposal1))
            == ast.dump(ast.parse(proposal2)),
            "prompt_tokens": sum(u["prompt_tokens"] for u in usage),
            "output_tokens": sum(u["completion_tokens"] for u in usage),
            "max_reported_context_utilization": max(
                r["stats"]["reported_context_utilization"] for r in responses
            ),
            "protected_drift": result["protected_drift"],
            "Primary_review": str(run / "review.json"),
            "semantic_assistance_during_run": False,
        }
    S.save(T.BATCH / "metrics.json", metrics)
    S.save(
        T.BATCH / "decision.json",
        {
            "status": "HOLD_REAL_SLICE_COMPLETION",
            "registered": 2,
            "executed": 2,
            "accepted": 0,
            "not_run": 0,
            "unit_interpretation": "One new requested behavior, two independently initialized repeats; not two tasks. Does not replace prior known-task successes or failures.",
            "preparation": "2/2 preview/apply/preflight and one complete offline scripted chain passed; no preparation/transport/schema/scope failures in live",
            "coder": "Both repeats failed semantic checks, with two applied edits and two no-ops each; one second edit only changes comments, the other repairs E712 but retains semantic defects.",
            "reviewer": "0 dispatched; no false pass and no review capability credit",
            "confirmed": "Both drafts equate numeric zero without strict type distinction; second also prioritizes message_id=0 before a truthy id. Concrete public failures reached later requests. Allowed correct reference passes the identical editor/check/handoff path offline.",
            "supported": "For this exposed type-sensitive priority task, checking/repair opportunity exists but failed evidence is not reliably converted into code correction; not an edit-application or context-capacity failure.",
            "unknown": [
                "Whether fact ordering improves recovery",
                "General model ability outside this task",
                "Primary cloud savings",
            ],
            "Primary": "Detailed contract/tests/target/config prepared before execution; inspected actual source and failures afterwards; no in-run guidance or production implementation takeover",
            "general_production": "HOLD",
            "old_qualification": "Unchanged named families only; this exact type-sensitive behavior is not qualified by similarity",
            "weekly_used_observed": 40,
            "weekly_stop": None,
            "commit_push": False,
            "next": "One bounded experiment may compare only existing-fact ordering on the frozen failed drafts, without adding hints, facts, retries or changing production defaults; retain this0/2 denominator.",
        },
    )
    print(metrics)


if __name__ == "__main__":
    close()
