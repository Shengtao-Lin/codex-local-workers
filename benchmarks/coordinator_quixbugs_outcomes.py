"""Outcome audit with explicit JSON equality across Windows newline normalization."""

import argparse
import json
import time
from pathlib import Path

import coordinator_quixbugs_audit as prior
import coordinator_quixbugs_wrap as wrap
from capability_fit import KIT, write
from inherited_context_recovery import digest, read


def vectors(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main(weekly_used):
    wrap.configure()
    provenance = read(wrap.BASE / "upstream-provenance.json")
    for path, sha in provenance["files"].items():
        prior.require(
            digest(wrap.BASE / "upstream" / path) == sha, "raw upstream drift"
        )
    source_vectors = wrap.BASE / "upstream/json_testcases/wrap.json"
    official = vectors(source_vectors)
    prior.require(len(official) == 5, "five pinned official vectors required")
    rows, run_ids = [], set()
    for cell in wrap.pilot.matrix.verify()["cells"]:
        contract, _, root, bound, archive = prior.context(cell["id"])
        run_ids.add(bound["run_id"])
        prior.require((archive / "completed.json").exists(), "incomplete worker")
        coder, actual, primary = (
            read(archive / name)
            for name in ("handoff.json", "packet.json", "review.json")
        )
        contract.validate_unit_packet(read(root / ".agent/feature-plan.json"), actual)
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
            prior.require(actual[key] == bound[key], "hard contract changed")
        expected = dict(cell["hashes"])
        for change in coder["changed_files"]:
            prior.require(change["path"] == "src/product/target.py", "unexpected edit")
            expected[change["path"]] = change["final_sha256"]
        wrap.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
        # Original downloaded bytes remain immutable. Fixture creation on
        # Windows normalized LF -> CRLF; parsed JSON and baseline raw hash must
        # both match, rather than falsely claiming fixture/upstream raw equality.
        prior.require(
            vectors(root / "tests/official-wrap.json") == official,
            "official JSON records changed",
        )
        explorer = read(root / ".agent/flow-explorer.json")
        primary_e = read(root / ".agent/flow-explorer-primary.json")
        prior.require(
            explorer["status"] == "success"
            and not explorer["cache"]["hit"]
            and primary_e["success"]
            and digest(root / ".agent/flow-explorer.json")
            == primary_e["report_sha256"],
            "Explorer not accepted independently",
        )
        for ref in explorer["source_refs"]:
            source = root / ref["path"]
            if digest(source) != ref["source_hash"]:
                source = archive / "preimages" / ref["path"]
            lines = source.read_text(encoding="utf-8").splitlines()
            prior.require(
                digest(source) == ref["source_hash"]
                and ref["quote"]
                == "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]]),
                "original citation changed",
            )
        checks_path = root / ".agent/outcome-independent-1.json"
        if not checks_path.exists():
            checks = wrap.pilot.matrix.SCOPE.FA.LAYER.check(
                root, "outcome-independent-1"
            )
            wrap.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
            write(checks_path, checks)
        checks = read(checks_path)
        last = read(root / coder["evidence_refs"]["validation_attempts"][-1])
        focused = last["validation"]["focused_tests"]
        passed_ids = focused["diagnostic"].get("passed_test_ids", [])
        prior.require(
            checks["tests_executed"] == 7 and checks["static_pass"],
            "independent test/static evidence missing",
        )
        reviewer_path = root / ".agent/normalize-unit-reviewer.json"
        reviewer = read(reviewer_path) if reviewer_path.exists() else None
        if coder["status"] == "failed":
            prior.require(
                not checks["semantic_pass"]
                and reviewer is None
                and primary["decision"] == "takeover",
                "failed-unit incorrectly accepted",
            )
        else:
            prior.require(
                coder["status"] == "ready_for_review"
                and checks["all_checks_pass"]
                and reviewer is not None
                and primary["decision"] == "accept",
                "successful-unit review missing",
            )
        proposal = (
            read(root / ".agent/normalize-unit-proposal.json")
            if cell["arm"] == "coordinator"
            else None
        )
        if proposal:
            context = read(root / ".agent/normalize-unit-proposal-input.json")
            prior.require(
                proposal["status"] == "protocol_valid"
                and set(context)
                == {"identity", "feature_goal", "source_refs", "question"}
                and all(
                    ref in explorer["source_refs"] for ref in context["source_refs"]
                ),
                "proposal provenance changed",
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
                "last_junit": focused["junit"],
                "last_official_group_passed": any(
                    name.endswith("::test_official_cases") for name in passed_ids
                )
                or focused["status"] == "passed",
                "independent_semantic_pass": checks["semantic_pass"],
                "independent_static_pass": checks["static_pass"],
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
                "primary_decision": primary["decision"],
                "validation_attempts": len(
                    coder["evidence_refs"]["validation_attempts"]
                ),
                "official_fixture_raw_sha256": digest(
                    root / "tests/official-wrap.json"
                ),
                "official_fixture_json_unchanged": True,
            }
        )
    frozen = read(wrap.SNAPSHOT / "freeze.json")["files"]
    prior.require(
        len(run_ids) == 6
        and all(digest(KIT / path) == sha for path, sha in frozen.items()),
        "identity/runtime drift",
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
        "official_data_representation_note": "Downloaded upstream raw bytes pinned; fixture text normalized LF to CRLF on Windows; five parsed records unchanged and original frozen fixture raw hashes still match. Registration's byte-for-byte fixture wording was inaccurate, not source drift.",
        "general_release": False,
        "auditor_seconds": time.monotonic() - STARTED,
        "driver_sha256": digest(Path(__file__)),
    }
    write(wrap.BASE / "benchmark-outcomes-1.json", facts)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    STARTED = time.monotonic()
    main(args.weekly_used)
