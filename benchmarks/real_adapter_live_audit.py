"""Audit one accepted trial; separate contract pass from exact error fidelity."""

import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import real_adapter_live as live
from capability_fit import KIT, write
from inherited_context_recovery import digest, read


def error_observation(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_datetime"
    )
    namespace = {"UTC": UTC, "datetime": datetime, "Any": Any}
    # Primary inspected this pure helper; execute only its extracted AST, not
    # the full candidate module. This is trusted local validation, not isolation.
    exec(  # noqa: S102
        compile(ast.Module(body=[helper], type_ignores=[]), str(path), "exec"),
        namespace,
    )
    try:
        namespace["_datetime"]("bad", datetime(2000, 1, 1, tzinfo=UTC))
    except ValueError as error:
        return {
            "type": type(error).__name__,
            "message": str(error),
            "cause_type": type(error.__cause__).__name__ if error.__cause__ else None,
            "cause_message": str(error.__cause__) if error.__cause__ else None,
        }
    raise ValueError("invalid timestamp was not rejected")


def requests(path):
    stats = []
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "model_request":
            stats.append(event["facts"])
        elif event["event"] == "model_turn" and event["facts"].get("model_request"):
            stats.append(event["facts"]["model_request"])
    values = [s.get("reported_context_utilization") for s in stats]
    return {
        "requests": len(stats),
        "max_reported_context_utilization": max(
            (v for v in values if v is not None), default=None
        ),
    }


def main():
    contract = live.configure()
    cell = live.pilot.matrix.verify()["cells"][0]
    root = live.ROOT
    plan = read(root / ".agent/feature-plan.json")
    _, refs, accepted = live.evidence.provenance(contract, cell, root, plan, True)
    contract.verify_integration_archive(plan, root, refs)
    packet = read(root / ".agent/normalize-unit-bound.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    actual, coder, primary = (
        read(archive / name) for name in ("packet.json", "handoff.json", "review.json")
    )
    reviewer_root = (
        root
        / ".agent/tasks"
        / packet["task_id"]
        / "reviews"
        / primary["local_review_id"]
    )
    reviewer = read(reviewer_root / "handoff.json")
    for key in (
        "required_behavior",
        "acceptance_criteria",
        "acceptance_scenarios",
        "dependencies",
        "focused_tests",
        "validation_profile",
        "owned_contract_ids",
        "required_order",
        "forbidden_orderings",
        "scope",
        "contract_check_required",
    ):
        if actual[key] != packet[key]:
            raise ValueError("hard contract drift: " + key)
    if any(
        actual["risk"][k] != packet["risk"][k]
        for k in ("feature", "unit", "integration")
    ):
        raise ValueError("risk drift")
    if (
        coder["status"] != "ready_for_review"
        or primary["decision"] != "accept"
        or reviewer["decision"] != "pass_to_primary"
    ):
        raise ValueError("canonical role gate failed")
    explorer_path = root / ".agent/flow-explorer.json"
    explorer = read(explorer_path)
    adjudication = read(root / ".agent/flow-explorer-primary.json")
    if (
        not adjudication["success"]
        or digest(explorer_path) != adjudication["report_sha256"]
    ):
        raise ValueError("localization adjudication drift")
    for ref in explorer["source_refs"]:
        source = root / ref["path"]
        if digest(source) != ref["source_hash"]:
            source = archive / "preimages" / ref["path"]
        lines = source.read_text(encoding="utf-8").splitlines()
        if digest(source) != ref["source_hash"] or ref["quote"] != "\n".join(
            lines[ref["start_line"] - 1 : ref["end_line"]]
        ):
            raise ValueError("original Explorer citation mismatch")
    frozen = read(live.SNAPSHOT / "freeze.json")["files"]
    if not all(digest(KIT / p) == sha for p, sha in frozen.items()):
        raise ValueError("product changed during trial")
    source_provenance = read(live.FROZEN / "provenance.json")
    if not all(
        digest(Path(source_provenance["source_root"]) / p) == sha
        for p, sha in source_provenance["copied_original_files"].items()
    ):
        raise ValueError("sibling files changed since extraction")
    integration = read(root / ".agent/feature-integration.json")
    independent = read(root / ".agent/normalize-unit-independent-1.json")
    if not integration["passed"] or not independent["passed"]:
        raise ValueError("independent checks failed")
    validation_attempts = []
    for path in sorted(archive.glob("validation-attempt-*.json")):
        attempt = read(path)
        validation_attempts.append(
            {
                "attempt": attempt["attempt"],
                "edit_revision": attempt["edit_revision"],
                "status": attempt["validation"]["status"],
                "junit": attempt["validation"]["focused_tests"].get("junit", {}),
            }
        )
    original_error = error_observation(live.FROZEN / live.COMMON)
    candidate_error = error_observation(root / live.COMMON)
    proposal = read(root / ".agent/normalize-unit-proposal.json")
    elapsed = read(root / ".agent/normalize-unit-invocation.json")["seconds"]
    explorer_elapsed = read(root / ".agent/explorer-invocation.json")["seconds"]
    facts = {
        "feature_id": packet["feature_id"],
        "accepted_units": sorted(accepted),
        "coder_status": coder["status"],
        "reviewer_decision": reviewer["decision"],
        "review_id": primary["local_review_id"],
        "canonical_hard_contract_and_risk_preserved": True,
        "fresh_explorer": {
            "status": explorer["status"],
            "cached": explorer["cache"]["hit"],
            "protocol_errors": explorer["budget_usage"]["protocol_errors"],
            "source_refs_verified": len(explorer["source_refs"]),
        },
        "coordinator": {"status": proposal["status"], "turns": proposal["model_turns"]},
        "validation_attempts": validation_attempts,
        "independent_tests": independent["junit"],
        "integration": integration,
        "model_request_context": {
            "coder": requests(archive / "events.jsonl"),
            "reviewer": requests(reviewer_root / "events.jsonl"),
        },
        "timing": {
            "proposal_coder_reviewer_seconds": elapsed,
            "explorer_seconds": explorer_elapsed,
            "total_local_invocation_seconds": elapsed + explorer_elapsed,
            "exact_loading_inference_split_seconds": None,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "note": "Includes loading/switching, excludes Primary/preparation/independent/kit checks. Kit regression overlapped calls; not causal performance/cost evidence.",
        },
        "error_fidelity": {
            "original": original_error,
            "candidate": candidate_error,
            "exact_match": original_error == candidate_error,
            "classification": "Original registration fixed ValueError type/rejection, not original message/cause. Passing explicit contract is not full exception semantic equivalence or a Reviewer false-negative credit.",
        },
        "runtime_files_unchanged": len(frozen),
        "sibling_original_files_unchanged": len(
            source_provenance["copied_original_files"]
        ),
        "cost_savings_established": False,
        "production_deployment": False,
        "primary_feature_accepted": False,
    }
    write(live.BASE / "facts-1.json", facts)
    print(
        json.dumps(
            {
                "facts": str(live.BASE / "facts-1.json"),
                "local_seconds": elapsed + explorer_elapsed,
                "error_fidelity": facts["error_fidelity"],
                "attempts": [
                    {k: a[k] for k in ("attempt", "edit_revision", "status")}
                    for a in validation_attempts
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
