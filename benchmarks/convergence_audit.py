"""Read-only evidence audit; emits facts, never accepts a worker or a feature."""

import json
from pathlib import Path

from convergence_screen import BASE, KIT, SNAPSHOT
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes


def audit():
    manifest = read(BASE / "manifest.json")
    policy = read(BASE / "convergence-policy.json")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    for path, sha in policy["files"].items():
        if digest(Path(path)) != sha:
            raise ValueError("policy drift")
    if digest(KIT / ".local-agents/config.json") != policy["global_config_sha256"]:
        raise ValueError("global config drift")
    units, explorers, integrations = [], [], []
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        expected = dict(cell["hashes"])
        for unit in cell["units"]:
            packet = read(root / f".agent/{unit}-bound.json")
            archive = (
                root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
            )
            coder = read(root / f".agent/{unit}-coder.json")
            review = read(root / f".agent/{unit}-reviewer.json")
            primary = read(archive / "review.json")
            handoff = read(archive / "handoff.json")
            completed = read(archive / "completed.json")
            for change in handoff["changed_files"]:
                expected[change["path"]] = change["final_sha256"]
            validation = coder["validation_summary"]
            units.append(
                {
                    "id": cell["id"] + "/" + unit,
                    "coder": coder["status"],
                    "reviewer": review["decision"],
                    "primary": primary["decision"],
                    "accepted": completed["status"] == "ready_for_review"
                    and coder["status"] == "ready_for_review"
                    and review["decision"] == "pass_to_primary"
                    and primary["decision"] == "accept"
                    and validation["status"] == "passed"
                    and validation["executed"] > 0
                    and validation["inputs_unchanged"] is True,
                    "reviewer_protocol_errors": review["runtime_facts"][
                        "protocol_error_count"
                    ],
                    "reviewer_executed_checks": len(
                        review["runtime_facts"]["approved_execution"]
                    ),
                    "primary_summary": primary["summary"],
                }
            )
        verify_hashes(root, expected)
        if cell["explorer_required"]:
            report = read(root / ".agent/explorer.json")
            adjudication = read(root / ".agent/explorer-primary-adjudication.json")
            explorers.append(
                {
                    "id": cell["id"],
                    "runtime_status": report["status"],
                    "task_complete": adjudication["success"],
                    "failure": adjudication.get("failure_signature"),
                    "cache_hit": report.get("cache", {}).get("hit", False),
                }
            )
        if len(cell["units"]) > 1:
            result = read(root / ".agent/feature-integration.json")
            integrations.append(
                {
                    "id": cell["id"],
                    "passed": result["checks"]["all_checks_pass"]
                    and result["inputs_unchanged"],
                }
            )
    return {
        "scope": "six previously known narrow task families, two fresh repetitions",
        "units": units,
        "explorers": explorers,
        "integrations": integrations,
        "accepted_units": sum(item["accepted"] for item in units),
        "explorer_runtime_success": sum(
            item["runtime_status"] == "success" for item in explorers
        ),
        "explorer_task_complete": sum(item["task_complete"] for item in explorers),
        "protected_and_final_source_hashes_match": True,
        "global_config_unchanged": True,
        "blind_reviewer_controls_executed": False,
        "coordinator_release": False,
        "cloud_savings_established": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
