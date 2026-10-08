"""Live completion recommendation from verified archives, never feature acceptance."""

import json
from pathlib import Path

import coordinator_failure_terminal_retry as candidate
from capability_fit import write
from inherited_context_recovery import digest, read

if __name__ == "__main__":
    candidate.configure()
    root, supervised, plan, initial, config = candidate.retry.original.context()
    actual = read(
        root
        / ".agent/coordinator"
        / plan["feature_id"]
        / "proposals/authorized-recovery/packet.json"
    )
    refs = {"repair-unit": {k: actual[k] for k in ("task_id", "run_id")}}
    supervised.CONTRACT.verify_integration_archive(plan, root, refs)
    identity = {
        "unit_id": "repair-unit",
        "run_id": initial["run_id"].replace("-a1", "-completion-a3"),
        "attempt": 3,
        "packet_revision": 3,
    }
    state_path = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    state = supervised.CONTRACT.load_coordinator_state(plan, root, state_path)
    before = digest(state_path)
    client = supervised.MODEL.WORKER.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        structured_output=False,
        timeout=config["coordinator_request_timeout_seconds"],
        max_tokens=config["coordinator_max_tokens"],
        context_length=config["coordinator_context_length"],
    )
    code, result = supervised.run_step(
        root=root,
        plan=plan,
        context={
            "identity": identity,
            "question": "Recommend next step using verified runtime facts; this is not permission to accept or replay work.",
        },
        request={},
        explorer={},
        run_refs=refs,
        config=config,
        config_path=root / ".agent/config.json",
        authorized=True,
        expected_sequence=state["sequence"],
        client=client,
        proposal_id="completion-recommendation",
    )
    coder_archive = (
        root / ".agent/tasks" / initial["task_id"] / "runs" / identity["run_id"]
    )
    if (
        code != 0
        or result["status"] != "primary_final_review_required"
        or result["feature_accepted"]
        or coder_archive.exists()
        or digest(state_path) != before
    ):
        raise ValueError(
            "completion must request Primary final review without dispatch, acceptance or state mutation"
        )
    facts = {
        "driver_sha256": digest(Path(__file__)),
        "result": result,
        "coder_not_replayed": True,
        "state_unchanged": True,
        "feature_not_auto_accepted": True,
    }
    write(candidate.BASE / "completion-facts-1.json", facts)
    print(json.dumps(facts, indent=2))
