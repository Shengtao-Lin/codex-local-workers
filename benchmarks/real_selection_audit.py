"""Record observed held-out results, without granting a new release."""

import json

import real_selection_trial as trial
from capability_fit import write
from inherited_context_recovery import digest, read


def main():
    trial.configure()
    cell = trial.pilot.matrix.verify()["cells"][0]
    packet = read(trial.ROOT / ".agent/normalize-unit-bound.json")
    archive = (
        trial.ROOT / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    )
    handoff = read(archive / "handoff.json")
    actual = read(archive / "packet.json")
    for field in ("required_behavior", "acceptance_scenarios", "focused_tests"):
        if actual[field] != packet[field]:
            raise ValueError("Coordinator changed hard field: " + field)
    for level in ("feature", "unit", "integration"):
        if actual["risk"][level] != packet["risk"][level]:
            raise ValueError("risk level changed: " + level)
    expected = dict(cell["hashes"])
    for change in handoff["changed_files"]:
        if change["path"] != trial.COMMON:
            raise ValueError("unexpected changed path")
        expected[change["path"]] = change["final_sha256"]
    trial.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(trial.ROOT, expected)
    provenance = read(trial.FROZEN / "provenance.json")
    for root in (trial.FROZEN, trial.SIBLING):
        trial.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(
            root, provenance["original_files"]
        )
    snapshot = trial.live.SNAPSHOT
    trial.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(
        trial.KIT, read(snapshot / "freeze.json")["files"]
    )
    explorer = read(trial.ROOT / ".agent/flow-explorer.json")
    for ref in explorer["source_refs"]:
        path = trial.ROOT / ref["path"]
        if ref["path"] == trial.COMMON:
            path = archive / "preimages" / ref["path"]
        lines = path.read_text(encoding="utf-8").splitlines()
        quote = "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]])
        if digest(path) != ref["source_hash"] or quote != ref["quote"]:
            raise ValueError("Explorer citation drift")
    events = [
        json.loads(line)
        for line in (archive / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    requests = [e["facts"] for e in events if e["event"] == "model_request"]
    reviewer_path = trial.ROOT / ".agent/normalize-unit-reviewer.json"
    reviewer = read(reviewer_path) if reviewer_path.exists() else None
    integration_path = trial.ROOT / ".agent/feature-integration.json"
    integration = read(integration_path) if integration_path.exists() else None
    primary = read(archive / "review.json")
    facts = {
        "task_family": "Real deterministic dataset selection, distinct from timestamp normalization",
        "reference_preflight": read(trial.BASE / "preflight-1.json"),
        "explorer_success": explorer["status"] == "success",
        "explorer_cache_hit": explorer["cache"]["hit"],
        "explorer_citations_verified": len(explorer["source_refs"]),
        "coordinator_status": read(trial.ROOT / ".agent/normalize-unit-proposal.json")[
            "status"
        ],
        "coordinator_hard_contract_unchanged": True,
        "risk_levels_unchanged": True,
        "risk_reason_normalization": {
            "bound": packet["risk"]["reasons"],
            "canonical": actual["risk"]["reasons"],
        },
        "coder_status": handoff["status"],
        "coder_requests": len(requests),
        "coder_max_reported_context_utilization": max(
            (r.get("reported_context_utilization", 0) for r in requests), default=0
        ),
        "validation_attempts": [
            {
                "path": str(p),
                "sha256": digest(p),
                "attempt": read(p)["attempt"],
                "edit_revision": read(p)["edit_revision"],
                "status": read(p)["validation"]["status"],
            }
            for p in sorted(archive.glob("validation-attempt-*.json"))
        ],
        "reviewer": reviewer,
        "reviewer_not_run_reason": None
        if reviewer
        else "Coder did not pass validation gate",
        "primary_unit_decision": primary["decision"],
        "integration": integration,
        "coordinator_coder_reviewer_seconds": read(
            trial.ROOT / ".agent/normalize-unit-invocation.json"
        )["seconds"],
        "runtime_and_original_source_unchanged": True,
        "unattended_release": False,
        "primary_feature_accepted": False,
        "limitations": [
            "Single injected repair, not a discovered production bug",
            "No independent architecture/decomposition or broad new feature qualification",
            "No cloud savings measurement; pytest9 vs <9; no Pyright",
        ],
    }
    write(trial.BASE / "facts-1.json", facts)
    print(
        json.dumps(
            {
                "coder": facts["coder_status"],
                "primary": primary["decision"],
                "integration": integration["passed"] if integration else None,
            }
        )
    )


if __name__ == "__main__":
    main()
