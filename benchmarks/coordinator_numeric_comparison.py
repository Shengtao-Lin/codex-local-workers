"""Audit the paired numeric chains without inferring Primary feature acceptance."""

import json
from pathlib import Path

import coordinator_numeric_split as split
from capability_fit import KIT, write
from inherited_context_recovery import digest, read


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    contract = split.configure()
    manifest = split.candidate.numeric.pilot.matrix.verify()
    rows = []
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        explorers = []
        for mode, (required, _) in split.QUESTIONS.items():
            path = root / f".agent/{mode}-explorer.json"
            report = read(path)
            primary = read(root / f".agent/{mode}-explorer-primary.json")
            require(
                report["status"] == "success"
                and not report.get("cache", {}).get("hit")
                and not report["uncertainties"]
                and primary["success"]
                and digest(path) == primary["report_sha256"],
                "Explorer report/adjudication mismatch",
            )
            paths = set()
            for ref in report["source_refs"]:
                source = root / ref["path"]
                if digest(source) != ref["source_hash"]:
                    matches = [
                        p
                        for p in (root / ".agent/tasks").glob(
                            "*/runs/*/preimages/" + ref["path"]
                        )
                        if digest(p) == ref["source_hash"]
                    ]
                    require(bool(matches), "original cited source missing")
                    source = matches[0]
                lines = source.read_text(encoding="utf-8").splitlines()
                start, end = ref["start_line"], ref["end_line"]
                require(
                    1 <= start <= end <= len(lines)
                    and ref["quote"] == "\n".join(lines[start - 1 : end]),
                    "invalid original source citation",
                )
                paths.add(ref["path"])
            require(set(required) <= paths, "required citation missing")
            explorers.append(
                {"mode": mode, "fresh_pass": True, "refs": len(report["source_refs"])}
            )
        plan = read(root / ".agent/feature-plan.json")
        _, refs, accepted = split.candidate.numeric.evidence.provenance(
            contract, cell, root, plan, True
        )
        contract.verify_integration_archive(plan, root, refs)
        units = []
        for uid in cell["units"]:
            bound = read(root / f".agent/{uid}-bound.json")
            archive = (
                root / ".agent/tasks" / bound["task_id"] / "runs" / bound["run_id"]
            )
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
                require(
                    actual[key] == bound[key], "hard contract drift: " + uid + "/" + key
                )
            require(
                all(
                    actual["risk"][k] == bound["risk"][k]
                    for k in ("feature", "unit", "integration")
                ),
                "risk drift",
            )
            independent = read(root / f".agent/{uid}-independent-1.json")
            validation = coder["validation"]
            require(
                coder["status"] == "ready_for_review"
                and primary["decision"] == "accept"
                and reviewer["decision"] == "pass_to_primary"
                and reviewer["runtime_facts"]["inputs_unchanged"]
                and independent["passed"]
                and independent["inputs_unchanged"]
                and validation["status"] == "passed"
                and validation["focused_tests"]["junit"]["executed"] > 0
                and validation["focused_tests"]["inputs_unchanged"]
                and all(
                    c["status"] == "passed" for c in validation["configured_checks"]
                ),
                "unit qualification failed: " + uid,
            )
            proposal_turns, proposal_tokens = 0, 0
            if cell["arm"] == "coordinator":
                proposal = read(root / f".agent/{uid}-proposal.json")
                context = read(root / f".agent/{uid}-proposal-input.json")
                mode = "parse" if uid == "normalize-unit" else "flow"
                original_refs = read(root / f".agent/{mode}-explorer.json")[
                    "source_refs"
                ]
                require(
                    proposal["status"] == "protocol_valid"
                    and set(context)
                    == {"identity", "feature_goal", "source_refs", "question"}
                    and context["source_refs"]
                    and all(r in original_refs for r in context["source_refs"]),
                    "proposal evidence/authority drift",
                )
                proposal_turns = proposal["model_turns"]
                proposal_tokens = sum(
                    r["response_usage"]["total_tokens"]
                    for r in proposal["model_requests"]
                )
            units.append(
                {
                    "id": uid,
                    "coder": "ready_for_review",
                    "reviewer": "pass_to_primary",
                    "primary": "accept",
                    "proposal_turns": proposal_turns,
                    "proposal_provider_tokens": proposal_tokens,
                    "local_invocation_seconds": read(
                        root / f".agent/{uid}-invocation.json"
                    )["seconds"],
                }
            )
        integration = read(root / ".agent/feature-integration.json")
        require(
            integration["checks"]["all_checks_pass"]
            and integration["junit"]
            == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0},
            "feature integration failed",
        )
        rows.append(
            {
                "identity": cell["id"],
                "explorers": explorers,
                "units": units,
                "accepted_units": sorted(accepted),
                "integration_tests": 7,
                "canonical_provenance_verified": True,
                "local_invocation_seconds": sum(
                    u["local_invocation_seconds"] for u in units
                ),
            }
        )
    frozen = read(split.SNAPSHOT / "freeze.json")["files"]
    require(all(digest(KIT / p) == h for p, h in frozen.items()), "production drift")
    facts = {
        "rows": rows,
        "fresh_focused_explorer_passes": 4,
        "coder_passes": 6,
        "reviewer_passes": 6,
        "primary_unit_accepts": 6,
        "six_file_single_call_qualified": False,
        "production_files_verified": len(frozen),
        "cost_savings_established": False,
        "elapsed_scope": "Sequential proposal when applicable, role loading, Coder and Reviewer; excludes Explorer, Primary active time and independent/integration checks. Single paired observation, not a causal comparison.",
        "primary_cloud_tokens_and_active_minutes": "not measured",
        "primary_feature_acceptance_not_inferred": True,
        "historical_failed_numeric_cohorts": [1, 2, 3],
        "driver_sha256": digest(Path(__file__)),
    }
    write(split.BASE / "comparison-facts-1.json", facts)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()
