"""Partial stage audit after Explorer failure; no inferred Primary acceptance."""

import json
from pathlib import Path

import coordinator_label_evidence as evidence
import coordinator_label_pilot as pilot
from capability_fit import KIT, write
from inherited_context_recovery import digest, read


def main():
    contract = pilot.configure()
    manifest = pilot.matrix.verify()
    rows, usages, configs = [], [], []
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        plan = read(root / ".agent/feature-plan.json")
        _, refs, accepted = evidence.provenance(contract, cell, root, plan)
        config = read(root / ".agent/config.json")
        if config.pop("coordinator_enabled") != (cell["arm"] == "coordinator"):
            raise ValueError("arm configuration mismatch")
        configs.append(config)
        ep = root / ".agent/explorer.json"
        explorer = read(ep) if ep.exists() else None
        seconds = (
            read(root / ".agent/explorer-invocation.json")["seconds"]
            if ep.exists()
            else None
        )
        units = []
        for unit in cell["units"]:
            invoked = root / f".agent/{unit}-invocation.json"
            if not invoked.exists():
                units.append(
                    {
                        "unit_id": unit,
                        "status": "not_executed",
                        "qualification_credit": False,
                    }
                )
                continue
            packet = read(root / f".agent/{unit}-bound.json")
            archive = (
                root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
            )
            actual = read(archive / "packet.json")
            contract.validate_unit_packet(plan, actual)
            for key in (
                "required_behavior",
                "acceptance_criteria",
                "acceptance_scenarios",
                "required_order",
                "forbidden_orderings",
                "validation_profile",
                "focused_tests",
                "dependencies",
                "owned_contract_ids",
            ):
                if actual[key] != packet[key]:
                    raise ValueError("hard contract changed: " + key)
            if any(
                actual["risk"][k] != packet["risk"][k]
                for k in ("feature", "unit", "integration")
            ):
                raise ValueError("risk level changed")
            coder = read(root / f".agent/{unit}-coder.json")
            reviewer = read(root / f".agent/{unit}-reviewer.json")
            independent = read(root / f".agent/{unit}-independent-1.json")
            invocation = read(invoked)
            validation = coder["validation_summary"]
            if not (
                invocation["exit"] == 0
                and unit in accepted
                and coder["status"] == "ready_for_review"
                and reviewer["decision"] == "pass_to_primary"
                and validation["status"] == "passed"
                and validation["executed"] > 0
                and validation["inputs_unchanged"]
                and all(
                    c["status"] == "passed" for c in validation["configured_checks"]
                )
                and independent["passed"]
            ):
                raise ValueError("executed unit was not independently accepted")
            proposal_turns = None
            if cell["arm"] == "coordinator":
                proposal = read(root / f".agent/{unit}-proposal.json")
                context = read(root / f".agent/{unit}-proposal-input.json")
                if (
                    set(context)
                    != {"identity", "feature_goal", "source_refs", "question"}
                    or proposal["status"] != "protocol_valid"
                    or actual
                    != contract.materialize_bounded_packet(plan, proposal["output"])
                ):
                    raise ValueError("proposal provenance or context invalid")
                proposal_turns = proposal["model_turns"]
                usages.extend(
                    r["response_usage"]
                    for r in proposal["model_requests"]
                    if r.get("response_usage")
                )
            units.append(
                {
                    "unit_id": unit,
                    "status": "primary_accepted",
                    "fresh_reviewer": reviewer["decision"],
                    "independent_checks_passed": True,
                    "hard_contract_and_risk_levels_unchanged": True,
                    "proposal_turns": proposal_turns,
                }
            )
            seconds += invocation["seconds"]
        integrated = bool(accepted == set(cell["units"]))
        if integrated:
            contract.verify_integration_archive(plan, root, refs)
            integration = read(root / ".agent/feature-integration.json")
            adjudication = read(root / ".agent/explorer-primary-adjudication.json")
            if not (
                integration["checks"]["all_checks_pass"]
                and integration["junit"]
                == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}
                and adjudication["success"]
                and not explorer["cache"]["hit"]
            ):
                raise ValueError("integration or Explorer adjudication invalid")
        rows.append(
            {
                "id": cell["id"],
                "explorer": explorer["status"] if explorer else "not_executed",
                "explorer_failure": explorer.get("failure_reason")
                if explorer
                else None,
                "units": units,
                "accepted_units": sorted(accepted),
                "integration_verified": integrated,
                "current_hashes_verified": True,
                "local_invocation_seconds": seconds,
            }
        )
    if any(c != configs[0] for c in configs):
        raise ValueError("paired role configuration drift")
    frozen = read(pilot.SNAPSHOT / "freeze.json")["files"]
    if any(digest(KIT / p) != sha for p, sha in frozen.items()):
        raise ValueError("production changed")
    facts = {
        "stage_status": "HOLD_NEW_COMPOSITION_EXPLORER_EOF_FEEDBACK",
        "cells": rows,
        "executed_coder_units": sum(len(r["accepted_units"]) for r in rows),
        "executed_explorers": sum(r["explorer"] != "not_executed" for r in rows),
        "accepted_explorers": sum(r["explorer"] == "success" for r in rows),
        "completed_integrations": sum(r["integration_verified"] for r in rows),
        "coordinator_provider_requests": len(usages),
        "coordinator_provider_usage": {
            k: sum(u[k] for u in usages)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
        "production_files_unchanged": len(frozen),
        "configuration_equal_except_coordinator_enabled": True,
        "full_registered_gate_passed": False,
        "cloud_tokens": None,
        "primary_active_seconds": None,
        "model_load_seconds_separately": None,
        "primary_feature_acceptance_not_inferred": True,
        "driver_sha256": digest(Path(__file__)),
    }
    write(pilot.BASE / "stage-facts-1.json", facts)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()
