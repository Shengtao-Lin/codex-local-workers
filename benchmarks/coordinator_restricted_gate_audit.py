"""Read-only negative authority gates against an actual failed live fixture state."""

import json
from pathlib import Path

import coordinator_failure_terminal_retry as candidate
from capability_fit import write
from inherited_context_recovery import digest

if __name__ == "__main__":
    candidate.configure()
    root, supervised, plan, _, _ = candidate.retry.original.context()
    state_path = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    initial = digest(state_path)
    state = supervised.CONTRACT.load_coordinator_state(plan, root, state_path)
    checks = [
        (
            "continue_unresolved_without_grant",
            {"decision": "CONTINUE", "unit_id": "repair-unit"},
            state["sequence"],
        ),
        (
            "model_cannot_self_authorize_rework",
            {
                "decision": "REWORK_LOCAL",
                "unit_id": "repair-unit",
                "reason_code": "focused-validation-failure",
            },
            state["sequence"],
        ),
        (
            "cannot_claim_ready_without_acceptance_integration",
            {"decision": "FEATURE_READY", "unit_id": "repair-unit"},
            state["sequence"],
        ),
        (
            "stale_sequence",
            {"decision": "CONTINUE", "unit_id": "repair-unit"},
            state["sequence"] - 1,
        ),
    ]
    observed = []
    for label, decision, sequence in checks:
        try:
            supervised.CONTRACT.gate_model_decision(
                plan, root, state, decision, {}, expected_sequence=sequence
            )
        except (ValueError, OSError) as exc:
            observed.append(
                {"id": label, "rejected_before_execution": True, "reason": str(exc)}
            )
        else:
            raise ValueError("unsafe authority gate accepted: " + label)
    if digest(state_path) != initial:
        raise ValueError("negative audit mutated live state")
    result = {
        "driver_sha256": digest(Path(__file__)),
        "checks": observed,
        "state_unchanged": True,
        "new_model_calls": 0,
        "worker_launches": 0,
    }
    write(candidate.BASE / "negative-authority-gates-1.json", result)
    print(json.dumps(result, indent=2))
