"""Paired packet-preparation facts, never Primary semantic acceptance."""

import json
from pathlib import Path

import coordinator_label_evidence as evidence
import coordinator_label_pilot as pilot
from capability_fit import KIT, write
from inherited_context_recovery import digest, read


def main():
    contract = pilot.configure()
    manifest = pilot.matrix.verify()
    registration = read(pilot.BASE / "registration.json")
    if len(manifest["cells"]) != 4 or {c["id"] for c in manifest["cells"]} != set(
        registration["order"]
    ):
        raise ValueError("incomplete paired registration")
    rows, configs, timings, usage = [], [], {}, []
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        plan = read(root / ".agent/feature-plan.json")
        _, refs, accepted = evidence.provenance(contract, cell, root, plan, True)
        contract.verify_integration_archive(plan, root, refs)
        config = read(root / ".agent/config.json")
        if config.pop("coordinator_enabled") != (cell["arm"] == "coordinator"):
            raise ValueError("arm config mismatch")
        configs.append(config)
        explorer = read(root / ".agent/explorer.json")
        adjudication = read(root / ".agent/explorer-primary-adjudication.json")
        seconds = read(root / ".agent/explorer-invocation.json")["seconds"]
        units = []
        for unit in cell["units"]:
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
                    raise ValueError(
                        "Primary hard contract changed: " + unit + "/" + key
                    )
            if any(
                actual["risk"][k] != packet["risk"][k]
                for k in ("feature", "unit", "integration")
            ):
                raise ValueError("Primary risk level changed")
            coder = read(root / f".agent/{unit}-coder.json")
            reviewer = read(root / f".agent/{unit}-reviewer.json")
            primary = read(archive / "review.json")
            invocation = read(root / f".agent/{unit}-invocation.json")
            independent = read(root / f".agent/{unit}-independent-1.json")
            validation = coder["validation_summary"]
            good = (
                invocation["exit"] == 0
                and coder["status"] == "ready_for_review"
                and reviewer["decision"] == "pass_to_primary"
                and primary["decision"] == "accept"
                and independent["passed"]
                and validation["status"] == "passed"
                and validation["executed"] > 0
                and validation["inputs_unchanged"] is True
                and all(
                    c["status"] == "passed" for c in validation["configured_checks"]
                )
            )
            proposal_turns = None
            if cell["arm"] == "coordinator":
                context = read(root / f".agent/{unit}-proposal-input.json")
                if set(context) != {
                    "identity",
                    "feature_goal",
                    "source_refs",
                    "question",
                }:
                    raise ValueError("full packet or unregistered context supplied")
                proposal = read(root / f".agent/{unit}-proposal.json")
                if proposal["status"] != "protocol_valid":
                    raise ValueError("invalid proposal")
                if actual != contract.materialize_bounded_packet(
                    plan, proposal["output"]
                ):
                    raise ValueError(
                        "archived packet differs from trusted materialization"
                    )
                proposal_turns = proposal["model_turns"]
                usage.extend(
                    r["response_usage"]
                    for r in proposal["model_requests"]
                    if r.get("response_usage")
                )
            units.append(
                {
                    "unit_id": unit,
                    "coder": coder["status"],
                    "reviewer": reviewer["decision"],
                    "primary": primary["decision"],
                    "independent_checks_passed": independent["passed"],
                    "hard_contract_unchanged": True,
                    "proposal_turns": proposal_turns,
                    "passed": good,
                }
            )
            seconds += invocation["seconds"]
        integration = read(root / ".agent/feature-integration.json")
        quality = (
            accepted == set(cell["units"])
            and adjudication["success"]
            and not explorer.get("cache", {}).get("hit")
            and all(u["passed"] for u in units)
            and integration["checks"]["all_checks_pass"]
            and integration["junit"]
            == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}
        )
        rows.append(
            {
                "id": cell["id"],
                "units": units,
                "fresh_explorer_accepted": adjudication["success"]
                and not explorer.get("cache", {}).get("hit"),
                "integration_verified": True,
                "quality_passed": quality,
            }
        )
        timings[cell["id"]] = seconds
    if any(c != configs[0] for c in configs):
        raise ValueError("E/C/R configurations differ")
    frozen = read(pilot.SNAPSHOT / "freeze.json")["files"]
    drift = [p for p, sha in frozen.items() if digest(KIT / p) != sha]
    if drift:
        raise ValueError("production drift: " + repr(drift))
    facts = {
        "cells": rows,
        "all_quality_checks_passed": all(r["quality_passed"] for r in rows),
        "configuration_equal_except_coordinator_enabled": True,
        "production_files_unchanged": len(frozen),
        "local_invocation_seconds": timings,
        "coordinator_provider_usage": {
            k: sum(u[k] for u in usage)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
        "coordinator_requests_with_usage": len(usage),
        "primary_unit_reviews_per_arm": 6,
        "cloud_tokens": None,
        "primary_active_seconds": None,
        "model_load_seconds_separately": None,
        "cost_savings_established": False,
        "primary_feature_acceptance_not_inferred": True,
        "interpretation": "New composition of qualified families; proposal-only Coordinator from Primary hard plan and actual source refs, no full packet or reference implementation. Timings include switching/checks but exclude preparation, Primary work and integration gaps.",
        "audit_driver_sha256": digest(Path(__file__)),
    }
    write(pilot.BASE / "paired-facts-1.json", facts)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()
