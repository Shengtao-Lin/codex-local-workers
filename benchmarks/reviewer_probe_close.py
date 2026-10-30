"""Adjudicate diagnostic probes; wire facts override broad raw failure labels."""

import argparse
from pathlib import Path

import harness_r4_dto_audit as A
import reviewer_semantic_probe as P


def close(batch, used):
    B = P.B
    P.C.audit()
    for path, sha in B.read(batch / "live-freeze.json")["pins"].items():
        assert B.sha(Path(path)) == sha
    judgments = B.read(batch / "primary-adjudications.json")
    rows, requests = [], []
    for row in B.read(batch / "registration.json")["cells"]:
        cell = batch / "cells" / row["id"]
        assert B.sha(cell / "messages.json") == row["messages_sha256"]
        result = B.read(cell / "result.json")
        wire = A.calls(cell)
        assert len(wire) == 1
        requests.extend(wire)
        failure = result["request_stats"].get("rejection_reason")
        rows.append(
            {
                "id": row["id"],
                "strength": row.get("strength"),
                "implementation": row["implementation"],
                "expected": row["expected"],
                "primary": judgments[row["id"]],
                "raw_result_sha256": B.sha(cell / "result.json"),
                "failure_class": "model_output_budget_exhausted"
                if failure == "output_token_limit"
                else "transport_or_service"
                if result["infra_failure"]
                else "protocol"
                if result["error"]
                else None,
                "seconds": result["seconds"],
                "raw_infra_flag_is_overbroad": failure == "output_token_limit"
                and result["infra_failure"],
            }
        )
    correct = sum(r["primary"]["correct"] for r in rows)
    registered = B.read(batch / "registration.json")["registered"]
    assert registered == len(rows)
    strengths = sorted({r["strength"] for r in rows if r["strength"]})
    groups = [
        {
            "strength": strength,
            "correct": sum(
                r["primary"]["correct"] for r in rows if r["strength"] == strength
            ),
            "total": sum(r["strength"] == strength for r in rows),
        }
        for strength in strengths
    ]
    eligible = [g["strength"] for g in groups if g["correct"] == g["total"] == 4]
    qualified = bool(eligible) if strengths else correct == registered
    B.save(batch / "grid-results.json", rows)
    B.save(
        batch / "decision.json",
        {
            "qualification": "PASS" if qualified else "HOLD",
            "registered": registered,
            "executed": len(rows),
            "correct": correct,
            "strength_groups": groups,
            "selected_for_formal_diagnostic": "medium"
            if "medium" in eligible
            else "high"
            if "high" in eligible
            else None,
            "criterion": B.read(batch / "registration.json")["criterion"],
            "r4_passed": False,
            "new_coder_or_holdout_credit": False,
            "production_promoted": False,
            "weekly_used": used,
            "usage_ceiling": 45,
            "first_failures_and_old_gates_unchanged": True,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    B.save(
        batch / "metrics.json",
        {
            "chat_completions": len(requests),
            "seconds": sum(r["seconds"] for r in rows),
            "prompt_tokens": sum(r["usage"]["prompt_tokens"] for r in requests),
            "completion_tokens": sum(r["usage"]["completion_tokens"] for r in requests),
            "maximum_prompt_tokens": max(r["usage"]["prompt_tokens"] for r in requests),
        },
    )
    print(
        {
            "correct": correct,
            "registered": registered,
            "groups": groups,
            "r4_passed": False,
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--used", type=int, required=True)
    args = p.parse_args()
    close(args.batch, args.used)
