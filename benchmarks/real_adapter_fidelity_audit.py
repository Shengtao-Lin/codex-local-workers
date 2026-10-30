"""Aggregate immutable evidence without writing Primary acceptance."""

import json

import real_adapter_fidelity as trial
from capability_fit import WORK, write
from inherited_context_recovery import digest, read


def main():
    records = []
    for number in (1, 2, 3):
        contract = trial.configure(number)
        trial.live.pilot.matrix.verify()
        _, cell, root, plan = trial.live.evidence.context(trial.live.IDENTITY)
        packet = read(root / ".agent/normalize-unit-bound.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        handoff = read(archive / "handoff.json")
        succeeded = handoff["status"] == "ready_for_review"
        if succeeded:
            expected, refs, _ = trial.live.evidence.provenance(
                contract, cell, root, plan, True
            )
            contract.verify_integration_archive(plan, root, refs)
        else:
            expected = dict(cell["hashes"])
            for change in handoff["changed_files"]:
                if change["path"] != trial.live.COMMON:
                    raise ValueError("failed run escaped scope")
                expected[change["path"]] = change["final_sha256"]
        trial.live.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
        review = (
            read(root / ".agent/normalize-unit-reviewer.json") if succeeded else None
        )
        explorer = read(root / ".agent/flow-explorer.json")
        accepted = read(root / ".agent/flow-explorer-primary.json")
        if digest(root / ".agent/flow-explorer.json") != accepted["report_sha256"]:
            raise ValueError("Explorer report drift")
        for ref in explorer["source_refs"]:
            path = root / ref["path"]
            if ref["path"] == trial.live.COMMON:
                path = archive / "preimages" / ref["path"]
            lines = path.read_text(encoding="utf-8").splitlines()
            actual = "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]])
            if digest(path) != ref["source_hash"] or actual != ref["quote"]:
                raise ValueError("Explorer evidence mismatch")
        integration = (
            read(root / ".agent/feature-integration.json") if succeeded else None
        )
        primary = read(archive / "review.json")
        proposal = read(root / ".agent/normalize-unit-proposal.json")
        events = [
            json.loads(line)
            for line in (archive / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        requests = [
            event["facts"] for event in events if event["event"] == "model_request"
        ]
        record = {
            "round": number,
            "root": str(root),
            "explorer_success": explorer["status"] == "success" and accepted["success"],
            "explorer_cache_hit": explorer["cache"]["hit"],
            "explorer_protocol_errors": explorer.get("protocol_errors"),
            "coordinator_status": proposal["status"],
            "coder_status": handoff["status"],
            "coder_model_requests": len(requests),
            "coder_max_reported_context_utilization": max(
                (r.get("reported_context_utilization", 0) for r in requests), default=0
            ),
            "reviewer_decision": review["decision"] if review else None,
            "reviewer_read_paths": review["runtime_facts"]["read_paths"]
            if review
            else [],
            "reviewer_protocol_errors": review["runtime_facts"]["protocol_error_count"]
            if review
            else None,
            "reviewer_not_run_reason": None
            if review
            else "Coder validation gate failed",
            "primary_unit_decision": primary["decision"],
            "integration": integration["junit"] if integration else None,
            "integration_passed": integration["passed"] if integration else False,
            "validation_attempts": [
                read(p) for p in sorted(archive.glob("validation-attempt-*.json"))
            ],
            "coordinator_coder_reviewer_seconds": read(
                root / ".agent/normalize-unit-invocation.json"
            )["seconds"],
        }
        record["registered_chain_passed"] = (
            record["explorer_success"]
            and not record["explorer_cache_hit"]
            and record["coordinator_status"] == "protocol_valid"
            and record["coder_status"] == "ready_for_review"
            and record["reviewer_decision"] == "pass_to_primary"
            and record["primary_unit_decision"] == "accept"
            and record["integration_passed"]
        )
        records.append(record)
    snapshot = trial.live.SNAPSHOT
    trial.live.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(
        snapshot, read(snapshot / "freeze.json")["files"]
    )
    trial.live.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(
        trial.KIT, read(snapshot / "freeze.json")["files"]
    )
    originals = read(trial.live.FROZEN / "provenance.json")["copied_original_files"]
    sibling = trial.KIT.parent / "agent-evaluation-harness"
    trial.live.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(sibling, originals)
    facts = {
        "records": records,
        "registered_chain_passes": sum(r["registered_chain_passed"] for r in records),
        "runtime_and_sibling_inputs_unchanged": True,
        "new_protected_test_hash": digest(trial.SUPPORT),
        "limitations": [
            "One private-helper repair family; repetitions are not three independent tasks",
            "No SQL/async/concurrency/new-feature generalization",
            "pytest9 vs original <9; no pytest-asyncio or Pyright",
            "Reviewer test-read coverage recorded, not assumed complete",
            "Cloud token savings and Primary active time not measured",
        ],
        "primary_feature_accepted": False,
    }
    target = WORK / "real-adapter-fidelity-controls-1/facts-1.json"
    write(target, facts)
    print(
        json.dumps({"facts": str(target), "passes": facts["registered_chain_passes"]})
    )


if __name__ == "__main__":
    main()
