"""Verify fresh E/C/R archives, explicit policy and Primary acceptance."""

import argparse
import json
from pathlib import Path

import coordinator_wrap_policy as cohort
from capability_fit import write
from inherited_context_recovery import digest, read


def context(identity):
    contract = cohort.configure()
    cell = next(c for c in cohort.pilot.matrix.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    packet = read(root / ".agent/normalize-unit-bound.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    return contract, cell, root, packet, archive


def inspect(identity):
    _, _, root, _, archive = context(identity)
    print((archive / "cumulative.diff").read_text(encoding="utf-8"))
    coder = read(archive / "handoff.json")
    reviewer = read(root / ".agent/normalize-unit-reviewer.json")
    print(
        json.dumps(
            {
                "coder": coder["status"],
                "validation": coder["validation_summary"],
                "reviewer": reviewer["decision"],
                "findings": reviewer["findings"],
                "runtime_facts": reviewer["runtime_facts"],
                "checks": reviewer["verified_check_ids"],
            }
        )
    )


def audit(weekly_used):
    rows, runs = [], set()
    for cell in cohort.pilot.matrix.verify()["cells"]:
        contract, _, root, bound, archive = context(cell["id"])
        plan = read(root / ".agent/feature-plan.json")
        expected, refs, _ = cohort.original.evidence.provenance(
            contract, cell, root, plan, True
        )
        contract.verify_integration_archive(plan, root, refs)
        packet, coder, primary = (
            read(archive / name)
            for name in ("packet.json", "handoff.json", "review.json")
        )
        contract.validate_unit_packet(plan, packet)
        for key in (
            "scope",
            "required_behavior",
            "acceptance_scenarios",
            "acceptance_criteria",
            "focused_tests",
            "validation_profile",
            "owned_contract_ids",
            "required_order",
            "forbidden_orderings",
        ):
            if packet[key] != bound[key]:
                raise ValueError("hard contract differs: " + key)
        if packet["run_id"] in runs or not (archive / "completed.json").exists():
            raise ValueError("run reuse or incomplete run")
        runs.add(packet["run_id"])
        explorer = read(root / ".agent/flow-explorer.json")
        adjudication = read(root / ".agent/flow-explorer-primary.json")
        if (
            explorer["status"] != "success"
            or explorer["cache"]["hit"]
            or not adjudication["success"]
            or adjudication["report_sha256"]
            != digest(root / ".agent/flow-explorer.json")
        ):
            raise ValueError("missing independently accepted fresh Explorer")
        for ref in explorer["source_refs"]:
            source = root / ref["path"]
            if digest(source) != ref["source_hash"]:
                source = archive / "preimages" / ref["path"]
            lines = source.read_text(encoding="utf-8").splitlines()
            if digest(source) != ref["source_hash"] or ref["quote"] != "\n".join(
                lines[ref["start_line"] - 1 : ref["end_line"]]
            ):
                raise ValueError("Explorer source citation drift")
        reviewer = read(root / ".agent/normalize-unit-reviewer.json")
        independent = read(root / ".agent/normalize-unit-independent-1.json")
        integration = read(root / ".agent/feature-integration.json")
        if (
            coder["status"] != "ready_for_review"
            or reviewer["decision"] != "pass_to_primary"
            or primary["decision"] != "accept"
            or not primary["local_review_id"]
            or not independent["passed"]
            or not integration["checks"]["all_checks_pass"]
        ):
            raise ValueError("incomplete accepted role chain")
        for observed in (independent["junit"], integration["junit"]):
            if observed != {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}:
                raise ValueError("seven real passing tests required")
        proposal = None
        if cell["arm"] == "coordinator":
            proposal = read(root / ".agent/normalize-unit-proposal.json")
            proposal_input = read(root / ".agent/normalize-unit-proposal-input.json")
            if (
                proposal["status"] != "protocol_valid"
                or set(proposal_input)
                != {"identity", "feature_goal", "source_refs", "question"}
                or not all(
                    r in explorer["source_refs"] for r in proposal_input["source_refs"]
                )
            ):
                raise ValueError("bounded proposal provenance invalid")
        events = [
            json.loads(line)
            for line in (archive / "events.jsonl").read_text().splitlines()
        ]
        requests = [e["facts"] for e in events if e["event"] == "model_request"]
        cohort.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
        rows.append(
            {
                "id": cell["id"],
                "arm": cell["arm"],
                "run_id": packet["run_id"],
                "explorer": "fresh_success_primary_verified",
                "coder": coder["status"],
                "reviewer": reviewer["decision"],
                "primary": primary["decision"],
                "integration": integration["junit"],
                "proposal_turns": proposal["model_turns"] if proposal else 0,
                "local_invocation_seconds": read(
                    root / ".agent/normalize-unit-invocation.json"
                )["seconds"],
                "coder_model_requests": len(requests),
                "validation_attempts": len(
                    coder["evidence_refs"]["validation_attempts"]
                ),
                "max_reported_context_utilization": max(
                    (r.get("reported_context_utilization") or 0 for r in requests),
                    default=0,
                ),
                "protected_inputs_verified": True,
            }
        )
    if len(rows) != 6:
        raise ValueError("all six registered cells required")
    write(
        cohort.BASE / "qualification-facts-1.json",
        {
            "rows": rows,
            "successful_chains": len(rows),
            "weekly_used_observed": weekly_used,
            "weekly_used_ceiling": 18,
            "classification": "Explicit-policy pure helper task transfer, not general unseen repository qualification",
            "coordinator_global_enabled": False,
            "cost_savings_claim": False,
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "old_failed_cohorts_retained": True,
            "reference_code_given_to_workers": False,
            "coordinator_and_control_have_same_explicit_policy": True,
            "comparison_to_previous_cohort_is_confounded": "Policy examples, current node-ID prefetch runtime and fresh stochastic calls differ; no single-factor causal claim.",
            "primary_release_decision": "separate_required",
        },
    )
    print(json.dumps(rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("inspect", "audit"))
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--weekly-used", type=float)
    args = parser.parse_args()
    cohort.configure()
    if args.action == "inspect":
        inspect(args.identity)
    else:
        audit(args.weekly_used)
