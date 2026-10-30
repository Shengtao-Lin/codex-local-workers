"""Primary-only closure of one frozen snapshot smoke; no model or code changes."""

import argparse
from pathlib import Path

import bounded_dependency_smoke as D
import bounded_evidence_support as S


def close(used, reason):
    assert 0 <= used <= 100 and reason.strip()
    reg = S.read(D.BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    plan = S.read(D.BATCH / "approved-plan.json")
    catalog = S.read(D.BATCH / "catalog.json")
    receipts, rows, inputs = {}, [], {}
    for topic in D.SPECS:
        data = S.read(D.BATCH / "units" / topic / "binding.json")
        root, packet = Path(data["root"]), data["packet"]
        current = D.BRIDGE.verify_accepted_unit(
            plan,
            root,
            packet["unit_id"],
            {k: packet[k] for k in ("task_id", "run_id")},
            data["config"],
            catalog,
            bridge_profile="bounded-v1",
        )
        assert current == S.read(root.parent / "acceptance.json")
        result = S.read(root.parent / "result.json")
        assert result["all_checks_pass"] and not result["protected_drift"]
        assert all(S.sha(root / p) == h for p, h in data["protected"].items())
        report = S.read(root / ".agent/unit-report.json")
        reviewer = S.read(root / ".agent/reviewer-report.json")
        rows.append(
            {
                "topic": topic,
                "unit_id": packet["unit_id"],
                "accepted": True,
                "seconds": result["seconds"],
                "coder_ledger": report["consolidated_harness"]["actual"],
                "reviewer_decision": reviewer["decision"],
                "reviewer_requests": reviewer["reviewer_model_calls"],
                "reviewer_output_failures": reviewer.get("output_limit_failures"),
                "reviewer_errors": reviewer.get("shared_error_budget_used"),
            }
        )
        receipts[topic], inputs[topic] = current, data
    producer, consumer = inputs["encode"], inputs["append"]
    uid = producer["packet"]["unit_id"]
    transfer = D.BRIDGE.dependency_readiness(
        plan,
        consumer["root"],
        consumer["packet"],
        consumer["config"],
        catalog,
        {uid: {k: producer["packet"][k] for k in ("task_id", "run_id")}},
        {uid: producer["config"]},
        bridge_profile="bounded-v1",
        dependency_roots={uid: producer["root"]},
        transfer_paths={
            uid: {
                "source": D.SPECS["encode"]["path"],
                "destination": D.SPECS["encode"]["path"],
            }
        },
        evidence_root=D.BATCH,
    )
    assert transfer == S.read(D.BATCH / "units/append/dependency-gate.json")
    root = Path(consumer["root"])
    integration = S.read(root.parent / "result.json")["independent_checks"]
    assert (
        "tests" in integration[0]["argv"]
        and str(D.BATCH / "private") in integration[0]["argv"]
    )
    hashes = {
        str(p.relative_to(root)): S.sha(p)
        for folder in ("src", "tests", "acceptance")
        for p in (root / folder).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    S.save(
        D.BATCH / "integration.json",
        {
            "authority": "primary",
            "decision": "accept_snapshot_smoke",
            "reason": reason,
            "primary_plan_sha256": D.BRIDGE.CONTRACT.authority_fingerprint(plan),
            "checks": integration,
            "current_files": hashes,
            "unit_receipts": receipts,
            "dependency_transfer": transfer,
            "automatic_acceptance": False,
        },
    )
    proposal = S.read(D.BATCH / "proposal.json")
    S.save(
        D.BATCH / "metrics.json",
        {
            "registered": {"chains": 1, "units": 2},
            "accepted": {"chains": 1, "units": 2},
            "rows": rows,
            "coordinator_requests": len(proposal["attempts"]),
            "local_unit_seconds": sum(r["seconds"] for r in rows),
            "Primary_runtime_semantic_hints": 0,
            "Primary_implementation_edits": 0,
            "Primary_preparation": reg["Primary_cost"],
            "Primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "weekly_used": used,
            "weekly_stop": 50,
            "cost_savings": "Not established",
        },
    )
    S.save(
        D.BATCH / "decision.json",
        {
            "status": "PASS_ONE_SUPERVISED_SNAPSHOT_DEPENDENCY_SMOKE",
            "gate": reg["gate"],
            "accepted_units": 2,
            "accepted_chains": 1,
            "scope": reg["scope"],
            "exposure": reg["exposure"],
            "production_enabled": False,
            "same_worktree_dependency_execution": "NOT_TESTED",
            "old_R4_D2_C4": "Unchanged",
            "stop_reason": "Registered smoke complete; no unregistered extra repeats",
        },
    )
    S.save(
        D.BATCH / "handoff.json",
        {
            "proved": "One fresh Coordinator decomposition, two independently accepted bounded units, exact read-only producer transfer and current full integration pass using explicit protocol bridge",
            "not_proved": "General release, repeat reliability, new-task transfer, same-worktree automatic scheduling, Reviewer unknown-boundary detection or cloud cost savings",
            "Primary_work": "Prepared complete contracts/tests/classification/paths and full reviews; approved decomposition and both units, no runtime semantic hint or implementation rescue",
            "histories": "Three zero-model preparation failures retained separately; no failed live result replaced",
            "defaults": "Unchanged; per-unit coordinator_enabled remains false, explicit Primary bridge performs no dispatch or acceptance itself",
        },
    )
    print(
        "One snapshot dependency chain independently accepted; no production enablement"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    close(args.weekly_used, args.reason)
