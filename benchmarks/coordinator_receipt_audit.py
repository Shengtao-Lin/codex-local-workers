"""Read-only paired quality/provenance/cost facts; no Primary feature acceptance."""

import json
from pathlib import Path

import coordinator_receipt_pilot as pilot
from capability_fit import write
from inherited_context_recovery import digest, read


def main():
    contract = pilot.configure()
    manifest = pilot.matrix.verify()
    registration = read(pilot.BASE / "registration.json")
    if len(manifest["cells"]) != 4 or {c["id"] for c in manifest["cells"]} != set(
        registration["order"]
    ):
        raise ValueError("paired cell set is incomplete or duplicated")
    if (
        digest(Path(pilot.__file__)) != registration["driver_sha256"]
        or digest(pilot.SOURCE / "corpus.json") != registration["source_corpus_sha256"]
    ):
        raise ValueError("registered inputs drift")
    rows, timings, tokens = [], {}, []
    configs = {}
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        expected, refs, units = dict(cell["hashes"]), {}, []
        config = read(root / ".agent/config.json")
        if config["coordinator_enabled"] != (cell["arm"] == "coordinator"):
            raise ValueError("Coordinator flag differs from arm")
        config.pop("coordinator_enabled")
        configs[cell["id"]] = config
        seconds = read(root / ".agent/explorer-invocation.json")["seconds"]
        for unit in cell["units"]:
            packet = read(root / f".agent/{unit}-bound.json")
            archive = (
                root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
            )
            refs[unit] = {k: packet[k] for k in ("task_id", "run_id")}
            coder = read(root / f".agent/{unit}-coder.json")
            reviewer = read(root / f".agent/{unit}-reviewer.json")
            primary = read(archive / "review.json")
            actual_packet = read(archive / "packet.json")
            for key in (
                "required_behavior",
                "acceptance_criteria",
                "acceptance_scenarios",
                "required_order",
                "forbidden_orderings",
                "validation_profile",
                "focused_tests",
            ):
                if actual_packet[key] != packet[key]:
                    raise ValueError(
                        "Primary hard contract changed: " + unit + "/" + key
                    )
            contract.validate_unit_packet(
                read(root / ".agent/feature-plan.json"), actual_packet
            )
            for change in read(archive / "handoff.json")["changed_files"]:
                expected[change["path"]] = change["final_sha256"]
            units.append(
                {
                    "unit_id": unit,
                    "run_id": packet["run_id"],
                    "coder": coder["status"],
                    "reviewer": reviewer["decision"],
                    "primary": primary["decision"],
                    "validation_passed": coder["validation_summary"]["status"]
                    == "passed"
                    and coder["validation_summary"]["executed"] > 0
                    and coder["validation_summary"]["inputs_unchanged"] is True
                    and all(
                        c["status"] == "passed"
                        for c in coder["validation_summary"]["configured_checks"]
                    ),
                    "actual_contract_matches_primary": True,
                }
            )
            path = (
                root
                / f".agent/{unit}-{'coordinator-invocation' if cell['arm'] == 'coordinator' else 'unit-invocation'}.json"
            )
            seconds += read(path)["seconds"]
            if cell["arm"] == "coordinator":
                proposal = (
                    root
                    / ".agent/coordinator"
                    / packet["feature_id"]
                    / "proposals"
                    / packet["run_id"]
                )
                for mode in ("decision", "proposal"):
                    model_result = read(proposal / f"{mode}.json")
                    tokens.extend(
                        r["response_usage"]
                        for r in model_result["model_requests"]
                        if r.get("response_usage")
                    )
        pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
        plan = read(root / ".agent/feature-plan.json")
        accepted = contract.accepted_units_from_archives(plan, root, refs)
        contract.verify_integration_archive(plan, root, refs)
        explorer = read(root / ".agent/explorer-primary-adjudication.json")
        final = (
            read(root / ".agent/coordinator-finish-result.json")
            if cell["arm"] == "coordinator"
            else None
        )
        if final:
            seconds += final["seconds"]
            tokens.extend(
                r["response_usage"]
                for r in read(root / ".agent/coordinator-finish-model.json")[
                    "model_requests"
                ]
                if r.get("response_usage")
            )
        quality = (
            accepted == set(cell["units"])
            and explorer["success"]
            and all(u["validation_passed"] for u in units)
            and (final is None or final["expected_feature_ready"])
        )
        rows.append(
            {
                "id": cell["id"],
                "units": units,
                "explorer_accepted": explorer["success"],
                "accepted_units": sorted(accepted),
                "current_files_match": True,
                "integration_verified": True,
                "terminal_recommendation_correct": final["expected_feature_ready"]
                if final
                else None,
                "quality_passed": quality,
            }
        )
        timings[cell["id"]] = seconds
    if any(config != next(iter(configs.values())) for config in configs.values()):
        raise ValueError("E/C/R configuration differs between paired arms")
    facts = {
        "cells": rows,
        "all_quality_checks_passed": all(r["quality_passed"] for r in rows),
        "configuration_equal_except_coordinator_enabled": True,
        "local_invocation_seconds": timings,
        "local_coordinator_provider_usage": {
            key: sum(u[key] for u in tokens)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
        "coordinator_provider_requests_with_usage": len(tokens),
        "cloud_tokens": None,
        "primary_active_seconds": None,
        "cost_savings_established": False,
        "model_load_seconds_separately": None,
        "timing_interpretation": "Sum of outer E plus C/R/coordinator invocations and terminal probe; excludes Primary work/preparation/integration gaps, includes model switching/checks.",
        "primary_feature_acceptance_not_inferred": True,
        "audit_driver_sha256": digest(Path(__file__)),
    }
    write(pilot.BASE / "paired-facts-1.json", facts)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()
