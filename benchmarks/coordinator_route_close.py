"""Close the fixed routing A/B from immutable results; no model invocation."""

import coordinator_route_evidence as R


def close():
    batch, s = R.BATCH, R.S
    reg = s.read(batch / "registration.json")
    assert all(s.sha(p) == h for p, h in reg["pins"].items())
    rows = {}
    for cell in R.ORDER:
        result = s.read(batch / cell / "result.json")
        proposal = s.read(batch / cell / "proposal.json")
        assert not result["infrastructure_failure"]
        assert proposal["status"] == "proposal_valid"
        units = {u["contracts"][0]: u for u in proposal["proposal"]["units"]}
        assert set(units) == {"encode", "append"}
        catalog = s.read(R.SOURCE / "catalog.json")
        for key, unit in units.items():
            assert unit["contracts"] == [key] and unit["risk"] == "high"
            assert unit["modify"] == [catalog[key]["path"]] and not unit["create"]
        assert units["encode"]["dependencies"] == []
        assert units["append"]["dependencies"] == [units["encode"]["id"]]
        rows[cell] = {**result, "primary_proposal_review": "valid_scoped_decomposition"}
    assert all(rows[c]["both_local"] for c in ("B1", "B2"))
    assert not any(rows[c]["both_local"] for c in ("A1", "A2"))
    s.save(
        batch / "primary-proposal-review.json",
        {
            "authority": "primary",
            "reviewed": R.ORDER,
            "finding": "All four actual proposals read: exact two high-risk contracts/files; producer has no dependency, consumer depends on producer; no creates, permissions or risk lowered. Normalized plan carries full original contracts. A legally chooses Primary, B chooses local-coder. No implementation strategy supplied.",
            "dispatch": False,
            "inputs": {c: s.sha(batch / c / "proposal.json") for c in R.ORDER},
        },
    )
    s.save(
        batch / "metrics.json",
        {
            "registered": 4,
            "executed": 4,
            "not_run": 0,
            "rows": rows,
            "valid_decomposition": {"A": "2/2", "B": "2/2"},
            "qualified_local_routing": {"A": "0/2", "B": "2/2"},
            "requests": 4,
            "protocol_retries": 0,
            "coder_calls": 0,
            "reviewer_calls": 0,
            "accepted_implementations": 0,
            "local_seconds": sum(r["seconds"] for r in rows.values()),
            "Primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "cost_savings": "Not established",
        },
    )
    s.save(
        batch / "decision.json",
        {
            "status": "PASS_NARROW_ROUTING_EVIDENCE_DELIVERY",
            "gate": reg["gate"],
            "production_enabled": False,
            "supported": "On this fixed known detailed brief, supplying the already-verified per-contract route catalog changed local-owner routing 0/2 to 2/2 without changing decomposition validity, permissions, risks, budgets or instructions.",
            "not_proved": "General planning, novel task qualification, implementation correctness, repeat reliability beyond two proposals, or Primary cost savings.",
            "next": "One separately frozen full real-package snapshot chain with the same catalog delivery; no promotion until both independent units and integration accept.",
            "prior_HOLD": "project-identity-chain-20261022-1 unchanged, two downstream NOT_RUN",
        },
    )
    R.D.T.write(
        batch / "handoff.md",
        """# Coordinator route evidence: narrow PASS

Fixed order B1/A1/A2/B2 completed. All four decomposed contracts/paths/high risk/dependency correctly; A routed both units to Primary twice, B to local-coder twice. One request each, no protocol retry. B only received the exact existing Primary-verified qualification catalog in read-only context.

Primary read all proposals. This supports useful qualification-fact delivery on one already-detailed known brief, not broad planning or implementation success. No Coder, Reviewer or final implementation acceptance occurred. Primary still supplied contracts, classification, exact paths, tests and an explicit dependency edge. Active time/cloud tokens unknown; no savings claim.

The prior HOLD and two NOT_RUN units remain unchanged. A separate real-package snapshot chain will test whether this routing can complete through Coder, fresh Reviewer, exact accepted dependency transfer and independent complete-project checks. No production defaults or model settings changed.
""",
    )
    print("Routing A0/2 B2/2; decomposition both2/2; narrow gate closed")


if __name__ == "__main__":
    close()
