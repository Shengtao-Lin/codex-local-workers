"""Offline evidence of the Coordinator/archive protocol boundary; no Worker call."""

import copy

import bounded_evidence_support as S
import capture_fixture_support as F
import installed_brief_trial as I

DEST = I.BATCH / "integration-boundary"


def audit():
    helper = F.load(
        I.ENTRY / "tests/test_coordinator_contract.py", "boundary_existing_fixture"
    )
    plan, packet = helper.packet_pair.__wrapped__()
    unit = plan["units"][0]["unit_id"]
    task, run, review = packet["task_id"], packet["run_id"], "boundary-review"
    identity = {
        "task_id": task,
        "unit_id": unit,
        "run_id": run,
        "feature_id": plan["feature_id"],
        "plan_revision": plan["plan_revision"],
    }
    facts = []
    for status in ("ready_for_review", "validation_passed_pending_review"):
        root = DEST / "synthetic-controls" / status
        archive = root / ".agent/tasks" / task / "runs" / run
        reviewer = root / ".agent/tasks" / task / "reviews" / review
        records = {
            archive / "packet.json": copy.deepcopy(packet),
            archive / "review.json": {
                "task_id": task,
                "unit_id": unit,
                "run_id": run,
                "decision": "accept",
                "worker_status": status,
                "local_review_id": review,
            },
            archive / "handoff.json": {"identity": identity, "status": status},
            archive / "completed.json": {"status": status},
            reviewer / "handoff.json": {
                "identity": {**identity, "review_id": review},
                "decision": "pass_to_primary",
            },
            reviewer / "completed.json": {"decision": "pass_to_primary"},
        }
        for path, record in records.items():
            S.save(path, record)
        try:
            accepted = helper.CONTRACT.accepted_units_from_archives(
                plan, root, {unit: {"task_id": task, "run_id": run}}
            )
            assert status == "ready_for_review" and accepted == {unit}
            facts.append({"status": status, "accepted": True})
        except ValueError as exc:
            assert (
                status == "validation_passed_pending_review"
                and "accepted Coder evidence" in str(exc)
            )
            facts.append({"status": status, "accepted": False, "error": str(exc)})
    actual = S.read(
        I.R.BATCH
        / "cells/binding-2/isolated/.agent/tasks/installed-real-transfer-20261021-1-binding-2/runs/installed-real-transfer-20261021-1-binding-2/review.json"
    )
    S.save(
        DEST / "result.json",
        {
            "offline_only": True,
            "synthetic_archive_controls_not_live_results": facts,
            "actual_accepted_real_slice": {
                k: actual.get(k)
                for k in (
                    "decision",
                    "worker_status",
                    "task_id",
                    "run_id",
                    "local_review_id",
                )
            },
            "confirmed": "Existing Coordinator verifier rejects new host-proposal status even with otherwise matching Primary/Reviewer metadata; current bounded constructor also explicitly rejects coordinator_enabled. These are intentional fail-closed boundaries, not model failures.",
            "not_claimed": "Synthetic metadata controls do not authenticate a real bounded archive, grant execution eligibility, or prove integration. No current status or canonical record was rewritten.",
            "next_design_boundary": "An explicit protocol-aware bridge must verify the full host manifest/current input/check/Reviewer/Primary evidence and plan binding without relabeling status or weakening existing archive gates. Current dry-run approval alone is insufficient.",
            "runtime_changes": False,
            "worker_calls": 0,
            "source_pins": {
                str(p): S.sha(p)
                for p in (
                    I.ENTRY / "coordinator-contract.py",
                    I.ENTRY / "bounded/consolidated_harness.py",
                )
            },
        },
    )
    print(
        "Legacy accepted; new status rejected as expected; integration remains unqualified"
    )


if __name__ == "__main__":
    audit()
