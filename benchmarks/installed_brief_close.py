"""Primary-only immutable approval/closure for the conditional brief probe."""

import argparse
from pathlib import Path

import bounded_evidence_support as S
import installed_brief_trial as I


def approve(cell, reason):
    row = S.read(I.BATCH / "live-results" / cell / "result.json")
    inputs = S.read(I.BATCH / "inputs" / (cell.split("-")[0] + ".json"))
    root, brief = Path(inputs["root"]), inputs["brief"]
    assert row["status"] == "proposal_valid" and row["family_eligible"]
    assert I.eligibility(brief, row["untrusted_plan"]) and not row["dispatch_allowed"]
    record = I.C.approve(
        brief,
        row["proposal"],
        root,
        root / ".agent" / (cell + "-approval.json"),
        primary_review_note=reason,
    )
    assert (
        I.C.approved_plan(
            brief, row["proposal"], root, root / ".agent" / (cell + "-approval.json")
        )
        == record["approved_plan"]
    )
    S.save(
        I.BATCH / "primary" / (cell + ".json"),
        {
            "decision": "approve_decomposition_only",
            "reason": reason,
            "approval_sha256": I.C.digest(record),
            "dispatch": False,
        },
    )


def close(used):
    reg = S.read(I.BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    rows = []
    for cell in I.ORDER:
        result = I.BATCH / "live-results" / cell / "result.json"
        row = S.read(result) if result.exists() else {"status": "NOT_RUN"}
        rows.append(
            {
                "cell": cell,
                "status": row["status"],
                "Primary_approved": (I.BATCH / "primary" / (cell + ".json")).exists(),
                "requests": row.get("model_requests", 0),
                "seconds": row.get("seconds", 0),
                "protocol_corrections": max(0, len(row.get("attempts", [])) - 1),
            }
        )
    accepted = sum(r["Primary_approved"] for r in rows)
    S.save(
        I.BATCH / "metrics.json",
        {
            "registered": 4,
            "executed": sum(r["status"] != "NOT_RUN" for r in rows),
            "approved": accepted,
            "rows": rows,
            "weekly_used": used,
            "weekly_stop": 50,
            "cloud_tokens": "unknown",
            "Primary_active_seconds": "unknown",
            "worker_dispatches": 0,
        },
    )
    S.save(
        I.BATCH / "decision.json",
        {
            "status": "PASS_BOUNDED_DECOMPOSITION_ONLY"
            if accepted == 4
            else "HOLD_BOUNDED_DECOMPOSITION",
            "gate": reg["gate"],
            "approved": accepted,
            "production_enabled": False,
            "dependency_chain_execution": "NOT_RUN",
            "old_R4_D2_C4": "Unchanged",
        },
    )
    S.save(
        I.BATCH / "handoff.json",
        {
            "proved": "See actual proposals and Primary approvals; only supplied-source already-qualified task families",
            "not_proved": reg["not_proven"],
            "Primary_preparation": reg["Primary_work"],
            "cost_savings": "Not measured; no Primary-only comparison",
            "next": "A plan-generation PASS is not end-to-end dispatch or dependency-chain qualification",
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("approve", "close"))
    p.add_argument("--cell", choices=I.ORDER)
    p.add_argument("--reason")
    p.add_argument("--weekly-used", type=int)
    args = p.parse_args()
    if args.mode == "approve":
        assert args.cell and args.reason
        approve(args.cell, args.reason)
    else:
        assert args.weekly_used is not None
        close(args.weekly_used)
