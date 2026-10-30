"""Close fixed batch; keep raw caps, semantic verdicts and advice defects distinct."""

import argparse
from pathlib import Path

import harness_bounded_recovery as H
import harness_reviewer_stage_close as C


def close(used):
    C.close(
        H,
        {
            "sample-02-candidate": (
                "incorrect_alternative_fix",
                "Correct defect and first suggested key-presence repair, but alternative sentinel example compares against a newly created object() and cannot detect absence. Judgment correct; complete repair advice is not reliable, retained as report-quality failure rather than silently ignoring bad advice.",
            ),
            "sample-17-candidate": (
                "model_output_budget_exhausted",
                "First 4096-token response and sole within-budget required-REPORT recovery both hit length with no final action. No partial reasoning credit; exact source/facts retained.",
            ),
            "sample-20-candidate": (
                "model_output_budget_exhausted",
                "Repeated bad source also hits output limit on both allowed requests, no final action. This is quality/completion failure, not HTTP or context overflow.",
            ),
        },
        used,
        "fixed-observations",
        "Do not promote or rerun this candidate. One separately frozen conditional recovery using the already-tested low reasoning instruction may be evaluated within the same budgets; no temperature/strength sweep, oracle or model change. Preserve bad optional repair advice as independent quality data. No R4 fresh-chain admission until all report criteria pass.",
    )
    B = H.B
    accounting = []
    for row in B.read(H.BATCH / "registration.json")["cells"]:
        cell = Path(row["root"]).parent
        matches = list(Path(row["root"]).rglob("bounded-request-accounting.json"))
        assert len(matches) == 1
        facts = B.read(matches[0])
        assert facts["actual_requests"] <= 16 and facts["shared_error_budget_used"] <= 4
        for failure in Path(row["root"]).rglob("output-limit-failure-*.json"):
            assert B.read(failure)["partial_action_executed"] is False
        accounting.append(
            {
                "id": row["id"],
                **facts,
                "decision": B.read(cell / "reviewer.json")["decision"],
            }
        )
    B.save(
        H.BATCH / "recovery-audit.json",
        {
            "calls": accounting,
            "actual_requests": sum(r["actual_requests"] for r in accounting),
            "first_request_completed": 18,
            "first_request_capped": 2,
            "recovery_attempted": 2,
            "recovered_invocations": 0,
            "output_caps": 4,
            "judgment_correct_original": 16,
            "report_quality_correct_original": 15,
            "real_correct": 2,
            "real_total": 4,
            "note": "Original verdicts all correct, but sample02 includes a broken alternative fix. Registered report-quality gate remains strict. Recovery added two requests without rescuing either failed invocation.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
