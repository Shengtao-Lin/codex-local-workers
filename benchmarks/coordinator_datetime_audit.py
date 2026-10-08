"""Verify real-helper transfer facts; acceptance stays an explicit Primary act."""

import argparse
import json
from pathlib import Path

import coordinator_datetime_transfer_checked as checked
from capability_fit import KIT, write
from inherited_context_recovery import digest, read


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main(weekly_used):
    contract = checked.configure()
    checked.verify()
    transfer = checked.transfer
    provenance = read(checked.BASE / "source-provenance.json")
    require(
        digest(transfer.SOURCE) == provenance["source_sha256"], "real source changed"
    )
    rows = []
    for cell in transfer.pilot.matrix.verify()["cells"]:
        root = Path(cell["root"])
        explorer = read(root / ".agent/flow-explorer.json")
        primary_e = read(root / ".agent/flow-explorer-primary.json")
        require(
            explorer["status"] == "success"
            and not explorer["cache"]["hit"]
            and primary_e["success"]
            and digest(root / ".agent/flow-explorer.json")
            == primary_e["report_sha256"],
            "fresh Explorer not accepted",
        )
        plan = read(root / ".agent/feature-plan.json")
        _, refs, accepted = transfer.evidence.provenance(
            contract, cell, root, plan, True
        )
        contract.verify_integration_archive(plan, root, refs)
        bound = read(root / ".agent/normalize-unit-bound.json")
        archive = root / ".agent/tasks" / bound["task_id"] / "runs" / bound["run_id"]
        actual = read(archive / "packet.json")
        coder = read(archive / "handoff.json")
        primary = read(archive / "review.json")
        reviewer = read(
            root
            / ".agent/tasks"
            / bound["task_id"]
            / "reviews"
            / primary["local_review_id"]
            / "handoff.json"
        )
        for key in (
            "scope",
            "focused_tests",
            "required_behavior",
            "acceptance_scenarios",
            "acceptance_criteria",
            "dependencies",
            "validation_profile",
            "owned_contract_ids",
            "required_order",
            "forbidden_orderings",
            "contract_check_required",
        ):
            require(actual[key] == bound[key], "hard contract drift: " + key)
        require(
            all(
                actual["risk"][k] == bound["risk"][k]
                for k in ("unit", "feature", "integration")
            ),
            "risk drift",
        )
        validation = coder["validation"]
        require(
            coder["status"] == "ready_for_review"
            and validation["status"] == "passed"
            and validation["focused_tests"]["junit"]["executed"] == 7
            and validation["focused_tests"]["inputs_unchanged"]
            and all(c["status"] == "passed" for c in validation["configured_checks"]),
            "Coder gate missing",
        )
        require(
            reviewer["decision"] == "pass_to_primary"
            and reviewer["runtime_facts"]["inputs_unchanged"]
            and primary["decision"] == "accept",
            "independent review missing",
        )
        require(
            read(root / ".agent/normalize-unit-independent-1.json")["passed"],
            "independent validation missing",
        )
        require(
            read(root / ".agent/feature-integration.json")["junit"]
            == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0},
            "integration count mismatch",
        )
        # Explorer hashes refer to pre-edit source. Check its exact archived version.
        for ref in explorer["source_refs"]:
            source = root / ref["path"]
            if digest(source) != ref["source_hash"]:
                source = archive / "preimages" / ref["path"]
            require(
                digest(source) == ref["source_hash"], "Explorer original source lost"
            )
            lines = source.read_text(encoding="utf-8").splitlines()
            require(
                ref["quote"]
                == "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]]),
                "Explorer quote mismatch",
            )
        proposal_turns = 0
        if cell["arm"] == "coordinator":
            proposal = read(root / ".agent/normalize-unit-proposal.json")
            context = read(root / ".agent/normalize-unit-proposal-input.json")
            require(
                proposal["status"] == "protocol_valid"
                and set(context)
                == {"identity", "feature_goal", "source_refs", "question"}
                and all(
                    ref in explorer["source_refs"] for ref in context["source_refs"]
                ),
                "proposal authority mismatch",
            )
            proposal_turns = proposal["model_turns"]
        rows.append(
            {
                "identity": cell["id"],
                "root": str(root),
                "explorer": "fresh accepted",
                "coder": coder["status"],
                "reviewer": reviewer["decision"],
                "primary": primary["decision"],
                "accepted_units": sorted(accepted),
                "integration_tests": 7,
                "proposal_turns": proposal_turns,
                "local_invocation_seconds": read(
                    root / ".agent/normalize-unit-invocation.json"
                )["seconds"],
                "validation_attempts": len(
                    coder["evidence_refs"]["validation_attempts"]
                ),
                "changed_paths": [item["path"] for item in coder["changed_files"]],
            }
        )
    frozen = read(transfer.SNAPSHOT / "freeze.json")["files"]
    require(
        all(digest(KIT / p) == sha for p, sha in frozen.items()),
        "production runtime drift",
    )
    facts = {
        "rows": rows,
        "production_files_verified": len(frozen),
        "real_source_unchanged": True,
        "weekly_used_start": 6,
        "weekly_used_end": weekly_used,
        "weekly_ceiling": 15,
        "scope": "one isolated private real helper; synthetic defects and synthetic caller",
        "whole_project_qualified": False,
        "cloud_saving_established": False,
        "cloud_tokens": None,
        "primary_active_seconds": None,
        "elapsed_scope": "invocation includes role loads/Coder/Reviewer and Coordinator proposal when applicable; Explorer/preparation/Primary/checks excluded",
        "preparation_diagnostic_retained": "coordinator-datetime-transfer-1",
        "identity_note": "Task strings retained across preparation cohorts; records scoped to distinct frozen workspace roots; no Coder invocation occurred in cohort 1",
        "driver_sha256": digest(Path(__file__)),
        "primary_feature_acceptance_inferred": False,
    }
    write(checked.BASE / "transfer-facts-1.json", facts)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--weekly-used", required=True, type=int)
    args = parser.parse_args()
    main(args.weekly_used)
