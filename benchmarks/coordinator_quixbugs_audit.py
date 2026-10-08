"""Primary-facing immutable review windows and six-cell benchmark fact audit."""

import argparse
import json
import time
from pathlib import Path

import coordinator_quixbugs_wrap as wrap
from capability_fit import KIT, write
from inherited_context_recovery import digest, read


def require(condition, message):
    if not condition:
        raise ValueError(message)


def context(identity):
    contract = wrap.configure()
    cell = next(c for c in wrap.pilot.matrix.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    packet = read(root / ".agent/normalize-unit-bound.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    return contract, cell, root, packet, archive


def inspect(identity):
    _, _, root, _, archive = context(identity)
    write(
        root / ".agent/primary-review-window-start.json",
        {
            "monotonic": time.monotonic(),
            "scope": "Primary observed review window; includes independent check/tool/model latency, not exact active CPU/cloud tokens or task preparation",
        },
    )
    coder = read(archive / "handoff.json")
    require(coder["status"] == "ready_for_review", "Coder not ready")
    reviewer = read(root / ".agent/normalize-unit-reviewer.json")
    print((archive / "cumulative.diff").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "identity": identity,
                "reviewer": reviewer["decision"],
                "findings": reviewer["findings"],
                "read_paths": reviewer["runtime_facts"]["read_paths"],
                "configured_checks": reviewer["verified_check_ids"],
                "coder_repair_count": coder["repair_count"],
            }
        )
    )


def review_window(identity):
    _, _, root, _, archive = context(identity)
    require(
        read(archive / "review.json")["decision"] == "accept",
        "actual Primary acceptance missing",
    )
    started = read(root / ".agent/primary-review-window-start.json")
    write(
        root / ".agent/primary-review-window.json",
        {
            "observed_window_seconds": time.monotonic() - started["monotonic"],
            "measurement_scope": started["scope"],
            "primary_implementation_edits": 0,
            "primary_rework_packets": 0,
        },
    )


def audit(weekly_used):
    wrap.configure()
    provenance = read(wrap.BASE / "upstream-provenance.json")
    for path, sha in provenance["files"].items():
        require(digest(wrap.BASE / "upstream" / path) == sha, "upstream drift")
    rows, run_ids = [], set()
    for cell in wrap.pilot.matrix.verify()["cells"]:
        contract, _, root, bound, archive = context(cell["id"])
        run_ids.add(bound["run_id"])
        plan = read(root / ".agent/feature-plan.json")
        _, refs, accepted = wrap.evidence.provenance(contract, cell, root, plan, True)
        contract.verify_integration_archive(plan, root, refs)
        actual, coder, primary = (
            read(archive / name)
            for name in ("packet.json", "handoff.json", "review.json")
        )
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
            "acceptance_criteria",
            "acceptance_scenarios",
            "dependencies",
            "validation_profile",
            "owned_contract_ids",
            "required_order",
            "forbidden_orderings",
            "contract_check_required",
        ):
            require(actual[key] == bound[key], "hard contract drift")
        require(
            all(
                actual["risk"][key] == bound["risk"][key]
                for key in ("unit", "feature", "integration")
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
            "Coder not qualified",
        )
        require(
            primary["decision"] == "accept"
            and reviewer["decision"] == "pass_to_primary"
            and reviewer["runtime_facts"]["inputs_unchanged"],
            "independent Reviewer/Primary missing",
        )
        require(
            [c["path"] for c in coder["changed_files"]] == ["src/product/target.py"],
            "unattributed changes",
        )
        require(
            read(root / ".agent/normalize-unit-independent-1.json")["passed"],
            "independent checks missing",
        )
        require(
            read(root / ".agent/feature-integration.json")["junit"]
            == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0},
            "integration failed",
        )
        require(
            digest(root / "tests/official-wrap.json")
            == provenance["files"]["json_testcases/wrap.json"],
            "official cases changed",
        )
        explorer = read(root / ".agent/flow-explorer.json")
        primary_e = read(root / ".agent/flow-explorer-primary.json")
        require(
            explorer["status"] == "success"
            and not explorer["cache"]["hit"]
            and primary_e["success"]
            and digest(root / ".agent/flow-explorer.json")
            == primary_e["report_sha256"],
            "Explorer not independently accepted",
        )
        for ref in explorer["source_refs"]:
            source = root / ref["path"]
            if digest(source) != ref["source_hash"]:
                source = archive / "preimages" / ref["path"]
            lines = source.read_text(encoding="utf-8").splitlines()
            require(
                digest(source) == ref["source_hash"]
                and ref["quote"]
                == "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]]),
                "Explorer original quote drift",
            )
        turns, tokens = 0, 0
        if cell["arm"] == "coordinator":
            proposal = read(root / ".agent/normalize-unit-proposal.json")
            context_data = read(root / ".agent/normalize-unit-proposal-input.json")
            require(
                proposal["status"] == "protocol_valid"
                and set(context_data)
                == {"identity", "feature_goal", "source_refs", "question"}
                and all(
                    ref in explorer["source_refs"]
                    for ref in context_data["source_refs"]
                ),
                "proposal scope/provenance error",
            )
            turns = proposal["model_turns"]
            tokens = sum(
                request["response_usage"]["total_tokens"]
                for request in proposal["model_requests"]
            )
        rows.append(
            {
                "identity": cell["id"],
                "round": cell["round"],
                "arm": cell["arm"],
                "fresh_explorer": True,
                "coder": "ready_for_review",
                "reviewer": reviewer["decision"],
                "primary": primary["decision"],
                "accepted_units": sorted(accepted),
                "tests": 7,
                "official_vectors": 5,
                "supplemental_generated_samples": 80,
                "proposal_turns": turns,
                "proposal_local_provider_tokens": tokens,
                "local_invocation_seconds": read(
                    root / ".agent/normalize-unit-invocation.json"
                )["seconds"],
                "primary_review_window": read(
                    root / ".agent/primary-review-window.json"
                ),
                "validation_attempts": len(
                    coder["evidence_refs"]["validation_attempts"]
                ),
                "repair_count": coder["repair_count"],
            }
        )
    frozen = read(wrap.SNAPSHOT / "freeze.json")["files"]
    require(
        len(run_ids) == 6
        and all(digest(KIT / path) == sha for path, sha in frozen.items()),
        "identities/runtime drift",
    )
    facts = {
        "rows": rows,
        "commit": wrap.COMMIT,
        "fresh_explorer_passes": 6,
        "coder_passes": 6,
        "reviewer_passes": 6,
        "primary_accepts": 6,
        "runtime_files_verified": len(frozen),
        "weekly_used_start": 7,
        "weekly_used_end": weekly_used,
        "weekly_used_ceiling": 15,
        "official_reference_supplemental_failure_retained": "preflight-1.json mutant-1",
        "cloud_tokens": None,
        "primary_total_active_seconds": None,
        "cost_saving_established": False,
        "whole_repository_or_autonomous_coordinator_release": False,
        "elapsed_scope": "proposal when present, role residency loading, Coder and Reviewer; Explorer/preparation/Primary/checks excluded",
        "driver_sha256": digest(Path(__file__)),
    }
    write(wrap.BASE / "benchmark-facts-1.json", facts)
    print(json.dumps(facts, indent=2))


def outcomes(weekly_used):
    """Retain failures as failures; no missing Reviewer becomes a pass."""
    wrap.configure()
    rows = []
    provenance = read(wrap.BASE / "upstream-provenance.json")
    for path, sha in provenance["files"].items():
        require(digest(wrap.BASE / "upstream" / path) == sha, "upstream drift")
    for cell in wrap.pilot.matrix.verify()["cells"]:
        _, _, root, _bound, archive = context(cell["id"])
        require((archive / "completed.json").is_file(), "unfinished worker record")
        coder = read(archive / "handoff.json")
        expected = dict(cell["hashes"])
        for change in coder["changed_files"]:
            require(change["path"] == "src/product/target.py", "unexpected worker path")
            expected[change["path"]] = change["final_sha256"]
        wrap.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
        require(
            digest(root / "tests/official-wrap.json")
            == provenance["files"]["json_testcases/wrap.json"],
            "official vectors drift",
        )
        explorer = read(root / ".agent/flow-explorer.json")
        primary_e = read(root / ".agent/flow-explorer-primary.json")
        require(
            explorer["status"] == "success"
            and not explorer["cache"]["hit"]
            and primary_e["success"]
            and digest(root / ".agent/flow-explorer.json")
            == primary_e["report_sha256"],
            "Explorer must qualify independently",
        )
        for ref in explorer["source_refs"]:
            source = root / ref["path"]
            if digest(source) != ref["source_hash"]:
                source = archive / "preimages" / ref["path"]
            lines = source.read_text(encoding="utf-8").splitlines()
            require(
                digest(source) == ref["source_hash"]
                and ref["quote"]
                == "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]]),
                "Explorer citation drift",
            )
        validation_rows = []
        for relative in coder["evidence_refs"]["validation_attempts"]:
            snapshot = read(root / relative)
            focused = snapshot["validation"]["focused_tests"]
            junit = focused.get("junit", {})
            passed_ids = focused.get("diagnostic", {}).get("passed_test_ids", [])
            validation_rows.append(
                {
                    "attempt": snapshot["attempt"],
                    "edit_revision": snapshot["edit_revision"],
                    "status": snapshot["validation"]["status"],
                    "junit": junit,
                    "failed_ids": focused.get("diagnostic", {}).get(
                        "failed_test_ids", []
                    ),
                    "official_group_passed": any(
                        name.endswith("::test_official_cases") for name in passed_ids
                    )
                    or focused["status"] == "passed",
                }
            )
        independent = root / ".agent/outcome-independent-1.json"
        if not independent.exists():
            # This observes failed source without altering or rehabilitating its
            # canonical Coder validation, and also catches post-run divergence.
            checks = wrap.pilot.matrix.SCOPE.FA.LAYER.check(
                root, "outcome-independent-1"
            )
            wrap.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
            write(independent, checks)
        observed = read(independent)
        require(observed["tests_executed"] == 7, "missing independent test evidence")
        reviewer_path = root / ".agent/normalize-unit-reviewer.json"
        reviewer = read(reviewer_path) if reviewer_path.exists() else None
        if coder["status"] == "failed":
            require(
                not observed["semantic_pass"] and reviewer is None,
                "failed-unit gate violated",
            )
        else:
            require(
                coder["status"] == "ready_for_review"
                and observed["all_checks_pass"]
                and reviewer is not None,
                "success missing gates",
            )
        proposal = (
            read(root / ".agent/normalize-unit-proposal.json")
            if cell["arm"] == "coordinator"
            else None
        )
        if proposal:
            require(
                proposal["status"] == "protocol_valid",
                "invalid proposal is not Coder quality",
            )
        events = [
            json.loads(line)
            for line in (archive / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        requests = [
            event["facts"] for event in events if event["event"] == "model_request"
        ]
        rows.append(
            {
                "identity": cell["id"],
                "arm": cell["arm"],
                "round": cell["round"],
                "fresh_explorer": True,
                "explorer_seconds": read(root / ".agent/explorer-invocation.json")[
                    "seconds"
                ],
                "coder_status": coder["status"],
                "failure_signature": coder["failure_signature"],
                "validation_attempts": validation_rows,
                "last_official_group_passed": validation_rows[-1][
                    "official_group_passed"
                ],
                "independent_semantic_pass": observed["semantic_pass"],
                "independent_static_pass": observed["static_pass"],
                "reviewer_status": reviewer["decision"]
                if reviewer
                else "not_started_validation_gate",
                "proposal_turns": proposal["model_turns"] if proposal else 0,
                "local_invocation_seconds": read(
                    root / ".agent/normalize-unit-invocation.json"
                )["seconds"],
                "coder_model_requests": len(requests),
                "max_reported_context_utilization": max(
                    (
                        request.get("reported_context_utilization", 0) or 0
                        for request in requests
                    ),
                    default=0,
                ),
                "primary_decision": read(archive / "review.json")["decision"]
                if (archive / "review.json").exists()
                else "pending",
            }
        )
    frozen = read(wrap.SNAPSHOT / "freeze.json")["files"]
    require(
        all(digest(KIT / path) == sha for path, sha in frozen.items()),
        "production drift",
    )
    facts = {
        "rows": rows,
        "commit": wrap.COMMIT,
        "fresh_explorer_passes": sum(row["fresh_explorer"] for row in rows),
        "coder_passes": sum(row["coder_status"] == "ready_for_review" for row in rows),
        "reviewer_started": sum(
            row["reviewer_status"] != "not_started_validation_gate" for row in rows
        ),
        "extended_acceptance_passes": sum(
            row["independent_semantic_pass"] for row in rows
        ),
        "official_vector_groups_passed": sum(
            row["last_official_group_passed"] for row in rows
        ),
        "weekly_used_start": 7,
        "weekly_used_end": weekly_used,
        "weekly_used_ceiling": 15,
        "runtime_files_verified": len(frozen),
        "cloud_tokens": None,
        "primary_total_active_seconds": None,
        "cost_saving_established": False,
        "benchmark_leaderboard_score_claim": False,
        "known_upstream_reference_gap": "preflight-1.json mutant-1: official corrected wrap fails progress boundary and generated invariants",
        "general_release": False,
        "driver_sha256": digest(Path(__file__)),
    }
    write(wrap.BASE / "benchmark-outcomes-1.json", facts)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action", choices=("inspect", "review-window", "audit", "outcomes")
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--weekly-used", type=int)
    args = parser.parse_args()
    if args.action == "inspect":
        inspect(args.identity)
    elif args.action == "review-window":
        review_window(args.identity)
    elif args.action == "outcomes":
        outcomes(args.weekly_used)
    else:
        audit(args.weekly_used)
