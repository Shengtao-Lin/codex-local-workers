"""Read-only replay of the frozen R3 CLI handoff boundary; never dispatch review."""

import json

import harness_r3_origin_fixed as F

B = F.B


def main():
    case = F.BATCH / "cases/repair-candidate-1"
    root = case / "isolated"
    packet = B.read(root / ".agent/packet.json")
    config = B.read(root / ".agent/config.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    before = {str(p): B.sha(p) for p in B.files(root)}
    full = B.read(archive / "handoff.json")
    actual = B.read(case / "coder.json")
    worker = F.R.load(root / ".local-agents/worker-runtime.py", "r3_boundary_worker")
    unit = F.R.load(root / ".local-agents/local-unit.py", "r3_boundary_unit")
    reproduced = worker.compact_handoff(full)
    assert reproduced == actual, "CLI result differs from compact projection"
    canonical_identity = unit.verify_handoff(root, full, config=config)
    try:
        unit.verify_handoff(root, reproduced, config=config)
    except unit.HandoffError as exc:
        error = str(exc)
    else:
        raise AssertionError("Expected exact compact protocol failure")
    assert error == "Unknown host execution protocol"
    # Counterfactual in memory only. Not a changed report, accepted run, or review dispatch.
    in_memory = {**reproduced, "execution_protocol": full["execution_protocol"]}
    restored_identity = unit.verify_handoff(root, in_memory, config=config)
    assert restored_identity == canonical_identity
    assert {str(p): B.sha(p) for p in B.files(root)} == before
    assert not (case / "reviewer.json").exists()
    record = {
        "no_model_calls": True,
        "no_archive_changes": True,
        "canonical_protocol": full["execution_protocol"],
        "canonical_worker_assessment_present": "worker_assessment" in full,
        "canonical_worker_assessment": full["worker_assessment"],
        "compact_protocol_present": "execution_protocol" in actual,
        "compact_worker_assessment_present": "worker_assessment" in actual,
        "cli_equals_compact_projection": True,
        "canonical_verifier_passed": canonical_identity,
        "compact_verifier_failure": error,
        "in_memory_protocol_only_restoration_verifier_passed": restored_identity,
        "reviewer_dispatched": False,
        "counterfactual_not_acceptance": True,
        "root_cause": "compact_handoff drops execution_protocol; CLI defaults to compact; local-unit correctly rejects missing protocol before Reviewer",
        "control_gap": "Existing host positive controls call verify_handoff with runtime.run full report, bypassing CLI compact serialization",
        "recommended_scope": "A separately authorized serializer-only repair plus actual installed CLI/subprocess positive and unknown-protocol negative controls. Preserve worker_assessment null explicitly; do not infer from status or weaken receiver.",
    }
    B.save(F.BATCH / "handoff-boundary-audit.json", record)
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
