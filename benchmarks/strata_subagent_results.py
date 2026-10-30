"""Create-only experiment scoring; never writes production task acceptance."""

import argparse
from pathlib import Path

import strata_subagent_trial as T


def close(used):
    registration = T.S.read(T.BATCH / "registration.json")
    cells = T.S.read(T.BATCH / "cells.json")
    rows = []
    for cell in registration["order"]:
        root = T.BATCH / "cells" / cell / "isolated"
        result = T.S.read(T.BATCH / "live-results" / cell / "result.json")
        arm = registration["arms"][cell]
        identity = T.BATCH.name + "-" + cell
        review_path = (
            root / ".agent/tasks" / identity / "runs" / identity / "review.json"
            if arm == "A"
            else T.BATCH / "live-results" / cell / "primary-review.json"
        )
        review = T.S.read(review_path)
        if review["decision"] == "accept":
            assert result["all_independent_pass"] and not result["protected_drift"]
            if arm == "B":
                assert result["summary"].get("host_handoff_verified") is True
                assert result["summary"]["production_acceptance"] is False
                assert not (root / ".agent/reviewer-report.json").exists()
                assert review["production_acceptance"] is False
                assert (
                    review["source_sha256"]
                    == result["final_source_sha256"]
                    == T.S.sha(root / cells[cell]["target"])
                )
                assert review["coder_report_sha256"] == T.S.sha(
                    root / ".agent/unit-report.json"
                )
                assert review["independent_result_sha256"] == T.S.sha(
                    T.BATCH / "live-results" / cell / "result.json"
                )
        usage = {k: 0 for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
        for path in (root / ".agent/strata-wire").glob("*.response.json"):
            for key in usage:
                usage[key] += T.S.read(path).get("usage", {}).get(key, 0)
        rows.append(
            {
                "cell": cell,
                "arm": arm,
                "Primary": review["decision"],
                "Primary_evidence": str(review_path),
                "coder": result["coder_status"],
                "ledger": result["ledger"],
                "summary": result["summary"],
                "independent_checks_pass": result["all_independent_pass"],
                "protected_drift": result["protected_drift"],
                "seconds": result["seconds"],
                "local_usage": usage,
                "final_source_sha256": result["final_source_sha256"],
            }
        )
    accepted = {
        arm: sum(r["Primary"] == "accept" for r in rows if r["arm"] == arm)
        for arm in ("A", "B")
    }
    evidence_actions = sum(
        r["ledger"]["actual"].get("evidence_actions", 0)
        for r in rows
        if r["arm"] == "B"
    )
    T.S.save(
        T.BATCH / "metrics.json",
        {
            "rows": rows,
            "registered": 4,
            "executed": 4,
            "accepted_by_arm": accepted,
            "B_evidence_actions": evidence_actions,
            "Primary_active_seconds": None,
            "cloud_tokens": None,
            "cold_load_seconds": None,
            "weekly_used_observed": used,
            "weekly_stop": 40,
            "script_sha256": T.S.sha(Path(__file__)),
        },
    )
    T.S.save(
        T.BATCH / "decision.json",
        {
            "status": "PASS_DIRECT_PRIMARY_FEASIBILITY"
            if accepted["B"] == 2
            else "HOLD_DIRECT_PRIMARY",
            "accepted_by_arm": accepted,
            "registered": 4,
            "executed": 4,
            "not_run": 0,
            "B_evidence_actions": evidence_actions,
            "evidence_interaction_exercised": evidence_actions > 0,
            "production_acceptance": False,
            "Reviewer_general_qualification": False,
            "limits": "Two exposed test-assisted tasks, one execution per arm; combined evidence/routing difference, no causal performance or economic savings claim. Production defaults and old grades unchanged. Direct Primary route not general release.",
            "weekly_used_observed": used,
            "weekly_stop": 40,
        },
    )
    print({"accepted_by_arm": accepted, "B_evidence_actions": evidence_actions})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly-used", type=int, required=True)
    close(parser.parse_args().weekly_used)
