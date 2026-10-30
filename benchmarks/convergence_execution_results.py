"""Explicit Primary decisions and independent final checks; never model dispatch."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import convergence_execution as core
import convergence_execution_fixture as fixture
from convergence_coder import save
from convergence_protocol_audit import preservation
from system_convergence import read_object, ref, sha256


def accepted_refs(root):
    return {
        p.stem: read_object(p) for p in (root / ".agent/accepted-refs").glob("*.json")
    }


def accept(identity, unit_id, note):
    """Called separately by Primary after inspecting actual diff and evidence."""
    fixture.bind()
    core.verify_frozen()
    _, cell = core.entry(identity)
    root = Path(cell["root"])
    suffix = (
        "-rework"
        if (root / (".agent/" + unit_id + "-rework-packet.json")).exists()
        else ""
    )
    packet = read_object(root / (".agent/" + unit_id + suffix + "-packet.json"))
    coder = read_object(root / (".agent/" + unit_id + suffix + "-coder.json"))
    reviewer = read_object(root / (".agent/" + unit_id + suffix + "-reviewer.json"))
    if (
        coder["status"] != "ready_for_review"
        or reviewer.get("decision") != "pass_to_primary"
    ):
        raise ValueError("not eligible for normal acceptance")
    api = core.module()
    gate = api.load("d2_handoff_current", "local-unit.py")
    gate.verify_handoff(root, coder)
    assert (
        core.command(
            root,
            [
                core.RUNTIME / "record-review.py",
                "--task-id",
                packet["task_id"],
                "--run-id",
                packet["run_id"],
                "--decision",
                "accept",
                "--summary",
                note,
                "--repo",
                root,
            ],
            root / (".agent/" + unit_id + "-primary-record-invocation.json"),
        )
        == 0
    )
    run_ref = {"task_id": packet["task_id"], "run_id": packet["run_id"]}
    refs = {**accepted_refs(root), unit_id: run_ref}
    plan = read_object(root / ".agent/approval.json")["approved_plan"]
    assert unit_id in api.CONTRACT.accepted_units_from_archives(plan, root, refs)
    save(root / (".agent/accepted-refs/" + unit_id + ".json"), run_ref)
    print(
        identity, unit_id, "Primary ACCEPT with canonical matching Reviewer", flush=True
    )


def integration(identity, arm="B"):
    fixture.bind()
    core.verify_frozen()
    feature, cell = core.entry(identity, arm)
    root = Path(cell["root"])
    brief = read_object(root / ".agent/brief.json")
    api = core.module()
    if arm == "B":
        plan = read_object(root / ".agent/approval.json")["approved_plan"]
        refs = accepted_refs(root)
        if (
            len(api.CONTRACT.accepted_units_from_archives(plan, root, refs))
            != feature["expected_units"]
        ):
            raise ValueError("not all units independently accepted")
    protected = {
        p: h for p, h in cell["inputs"].items() if p not in brief["authority"]["modify"]
    }
    api.assert_sources_current({"source_hashes": protected}, root)
    assert (
        core.command(
            root,
            [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml",
                root / ".agent/integration.xml",
            ],
            root / ".agent/integration.json",
        )
        == 0
    )
    assert (
        core.command(
            root,
            ["-m", "ruff", "check", "src", "tests"],
            root / ".agent/ruff-check.json",
        )
        == 0
    )
    assert (
        core.command(
            root,
            ["-m", "ruff", "format", "--check", "src", "tests"],
            root / ".agent/ruff-format.json",
        )
        == 0
    )
    api.assert_sources_current({"source_hashes": protected}, root)


def audit():
    fixture.bind()
    registration = core.verify_frozen()
    results = []
    for feature in read_object(core.BASE / "preparation.json")["features"]:
        arms = []
        for cell in feature["arms"]:
            root = Path(cell["root"])
            decision = read_object(root / ".agent/primary-decision.json")
            for path in ("integration.json", "ruff-check.json", "ruff-format.json"):
                assert read_object(root / ".agent" / path)["exit"] == 0
            junit = list(ET.parse(root / ".agent/integration.xml").iter("testcase"))
            assert junit and all(
                c.find("failure") is None
                and c.find("error") is None
                and c.find("skipped") is None
                for c in junit
            )
            brief = read_object(root / ".agent/brief.json")
            assert all(
                sha256(root / p) == h
                for p, h in cell["inputs"].items()
                if p not in brief["authority"]["modify"]
            )
            assert decision["decision"] == "accept"
            item = {
                "arm": cell["arm"],
                "tests": len(junit),
                "primary": ref(root, ".agent/primary-decision.json"),
                "cloud_tokens": None,
                "primary_active_seconds": None,
            }
            if cell["arm"] == "B":
                plan = read_object(root / ".agent/approval.json")["approved_plan"]
                refs = accepted_refs(root)
                assert (
                    len(
                        core.module().CONTRACT.accepted_units_from_archives(
                            plan, root, refs
                        )
                    )
                    == feature["expected_units"]
                )
                item["accepted_units"] = refs
                item["initial_and_final_results"] = [
                    read_object(root / (".agent/" + u + "-invocation.json"))["exit"]
                    for u in refs
                ]
                item["proposal_attempts"] = len(
                    read_object(root / ".agent/proposal-result.json")["attempts"]
                )
            arms.append(item)
        results.append(
            {
                "id": feature["id"],
                "registered_order": feature["order"],
                "origin": feature["origin"],
                "arms": arms,
            }
        )
    save(
        core.BASE / "stage-decision-1.json",
        {
            "stage": "D2",
            "candidate": registration["candidate"],
            "decision": "LIMITED_SUPERVISED_EXECUTION_QUALITY_PASS",
            "registered_feature_chains": 6,
            "completed_feature_chains": 6,
            "pairs": results,
            "same_primary_context_learning_confound": True,
            "fixed_denominator_and_original_failures_preserved": True,
            "primary_business_implementation_in_B": False,
            "external_rework_packets": sum(
                (Path(a["root"]) / ".agent/external-rework-1.json").exists()
                for f in read_object(core.BASE / "preparation.json")["features"]
                for a in f["arms"]
            ),
            "cost_qualification": "UNMEASURED",
            "no_usage_saving_claim": True,
            "weekly_used_start": 3,
            "weekly_used_ceiling": 15,
            "preservation": preservation(),
            "production_promoted": False,
            "next": "I1 fresh independent dependency chain smoke and applicable release-gate mapping",
        },
    )


def hold_audit():
    """Keep failed cells in the original denominator; never invoke a worker."""
    import json
    from collections import Counter
    from datetime import datetime

    fixture.bind()
    registration = core.verify_frozen()
    features = read_object(core.BASE / "preparation.json")["features"]
    rows, calls, reviews = [], [], []
    counts = Counter()
    for feature in features:
        arm_rows = []
        for cell in feature["arms"]:
            root = Path(cell["root"])
            brief = read_object(root / ".agent/brief.json")
            protected = {
                p: h
                for p, h in cell["inputs"].items()
                if p not in brief["authority"]["modify"]
            }
            core.module().assert_sources_current({"source_hashes": protected}, root)
            decision = read_object(root / ".agent/primary-decision.json")
            counts[cell["arm"] + "-" + decision["decision"]] += 1
            arm_rows.append(
                {
                    "arm": cell["arm"],
                    "decision": decision["decision"],
                    "record": ref(root, ".agent/primary-decision.json"),
                }
            )
            if cell["arm"] == "A":
                assert all(
                    read_object(root / ".agent" / p)["exit"] == 0
                    for p in ("integration.json", "ruff-check.json", "ruff-format.json")
                )
                continue
            plan = read_object(root / ".agent/approval.json")["approved_plan"]
            accepted = core.module().CONTRACT.accepted_units_from_archives(
                plan, root, accepted_refs(root)
            )
            if decision["decision"] == "accept":
                assert len(accepted) == feature["expected_units"]
            for archive in (
                root / ".agent/tasks" / brief["task_id"] / "runs"
            ).iterdir():
                handoff = read_object(archive / "handoff.json")
                events = [
                    json.loads(line)
                    for line in (archive / "events.jsonl").read_text().splitlines()
                ]
                model = [e["facts"] for e in events if e["event"] == "model_request"]
                raw_validation = json.loads((archive / "validation.json").read_text())
                validation = raw_validation if isinstance(raw_validation, dict) else {}
                stats = (validation.get("focused_tests") or {}).get("junit") or {}
                calls.append(
                    {
                        "feature": feature["id"],
                        "identity": handoff["identity"],
                        "status": handoff["status"],
                        "failure_reason": handoff.get("failure_reason"),
                        "executed_tests": stats.get("executed"),
                        "current_validation_available": isinstance(
                            raw_validation, dict
                        ),
                        "protocol_errors": sum(
                            e["event"] == "tool_error" for e in events
                        ),
                        "model_turns": len(model),
                        "local_tokens": sum(
                            m.get("response_usage", {}).get("total_tokens", 0)
                            for m in model
                        ),
                        "reported_utilization_max": max(
                            (m.get("reported_context_utilization", 0) for m in model),
                            default=None,
                        ),
                        "event_window_seconds": (
                            datetime.fromisoformat(events[-1]["at"])
                            - datetime.fromisoformat(events[0]["at"])
                        ).total_seconds(),
                        "archive": ref(
                            root, archive.relative_to(root).as_posix() + "/handoff.json"
                        ),
                    }
                )
            for review_root in (
                root / ".agent/tasks" / brief["task_id"] / "reviews"
            ).glob("*"):
                report = read_object(review_root / "handoff.json")
                reviews.append(
                    {
                        "identity": report["identity"],
                        "decision": report["decision"],
                        "report": ref(
                            root,
                            review_root.relative_to(root).as_posix() + "/handoff.json",
                        ),
                    }
                )
        rows.append(
            {
                "id": feature["id"],
                "origin": feature["origin"],
                "registered_order": feature["order"],
                "arms": arm_rows,
            }
        )
    assert (
        counts["A-accept"] == 3 and counts["B-accept"] == 2 and counts["B-replan"] == 1
    )
    assert len(calls) == 7 and len(reviews) == 3
    save(
        core.BASE / "stage-decision-1.json",
        {
            "stage": "D2",
            "candidate": registration["candidate"],
            "decision": "HOLD_CAPABILITY",
            "registered_feature_chains": 6,
            "completed_feature_attempts": 6,
            "A_accepts": 3,
            "B_accepts": 2,
            "B_failed": 1,
            "pairs": rows,
            "coder_calls": calls,
            "reviewer_calls": reviews,
            "coder_initial_successful_units": 1,
            "coder_initial_units": 4,
            "coder_final_accepted_units": 3,
            "coordinator_proposals": 3,
            "valid_initial_proposals": 3,
            "primary_semantic_graph_rewrites": 0,
            "explorer_calls": 1,
            "explorer_independent_complete_truthful": 1,
            "external_rework_packets": 3,
            "per_feature_external_rework_used": {f["id"]: 1 for f in features},
            "primary_business_implementation_in_B": False,
            "primary_takeover": False,
            "actual_failed_contract": "classification-shapes",
            "failure": "Two protected AttributeError failures remain after permitted inherited recovery, and original service-name fallback is also broken",
            "runtime_overrestriction_not_supported": "Failing semantic recovery traces have required_paths=[]; narrow SAFE_REPLACE edits were permitted and executed, followed by current validation. No evidence of HTTP400/context overflow in these runs.",
            "context_causal_conclusion": "Only absence of observed overflow; utilization is not proof that attention/context played no part",
            "cost_qualification": "UNMEASURED",
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "same_primary_learning_confound": True,
            "same_fixed_tests_and_standards": True,
            "initial_fixture_fault_and_false_primary_acceptance_correction_preserved": ref(
                fixture.OLD, "stage-decision-1.json"
            ),
            "weekly_used_start": 3,
            "weekly_used_latest": 3,
            "weekly_used_ceiling": 15,
            "preservation": preservation(),
            "I1": "NOT_RUN_DEPENDENCY_D2_HOLD",
            "new_live_stage_authorization_needed": "Fixed D2 batch and the one allowed external rework per feature are exhausted; cannot add a retry or substitute a task to pass this registration",
            "production_promoted": False,
            "commit_push": False,
        },
    )
    old_gates = read_object(
        core.KIT
        / "benchmarks/work/system-convergence/followup-20261011-2/release-gates-1.json"
    )
    updates = {
        "v12-explorer-independent-completion": (
            "PASS_LIMITED",
            "Typed single-question/scoped evidence protocol six/six plus actual D2 caller/test question, known-symbol guided and within budget; broad investigation not promoted",
        ),
        "reviewer-original-sixteen-semantic": (
            "PASS_LIMITED",
            "Same original sixteen controls all correct and valid for typed-assessment/evidence-ID candidate; nine protocol corrections preserved, not general reliability proof",
        ),
        "coordinator-approved-supervised-execution": (
            "HOLD_CAPABILITY",
            "D2 fixed 3 pairs: A3/3, B2/3. Seven Coder calls, three fresh Reviewer/Primary accepts, one Explorer; novel real-copy repair failed twice. No I1 smoke",
        ),
        "complete-runtime-http-example-install-validation": (
            "PASS_RUNTIME_WITH_HOST_SKIP_I1_INCOMPLETE",
            "Combined exact runtime hashes 1096 passes, one symlink skip,192 subtests; old first environment failures preserved, installation/HTTP suites executed. Example/I1 smoke not yet claimed for this stage",
        ),
        "paired-primary-cost-and-token-savings": (
            "UNMEASURED",
            "A/B actual quality data present including failed task, but cloud tokens and Primary active time unknown; no savings or release claim",
        ),
    }
    gates = []
    for gate in old_gates["gates"]:
        item = dict(gate)
        if item["id"] in updates:
            item["status"], item["evidence"] = updates[item["id"]]
        gates.append(item)
    save(
        core.BASE / "release-gates-1.json",
        {
            **old_gates,
            "version": "typed-roles-d2-20261011-2",
            "implementation_gate": "HOLD_D2_AND_I1",
            "release_gate": "HOLD",
            "gates": gates,
            "prior_gates": ref(
                core.KIT,
                "benchmarks/work/system-convergence/followup-20261011-2/release-gates-1.json",
            ),
            "global_coordinator_enabled": False,
            "legacy_production_qualification_not_overwritten": True,
        },
    )
    save(
        core.BASE / "next-stage-proposal-1.json",
        {
            "proposed_stage": "C3 Coder action-argument transport qualification",
            "status": "NOT_AUTHORIZED_OR_STARTED",
            "reason": "Three of four initial units failed; two were protocol completion failures, one real semantic repair failure. Coordinator decomposition was correct, so do not redesign it or add broad hints",
            "single_axis": "Evaluate existing coder_typed_action_arguments=true as a frozen transport-mode candidate against unchanged baseline, before any new implementation. Do not reimplement existing typed schema/native tools",
            "historical_checks": "coder-tagged-preflight-1 three exact echoes, negative probe fixes missing/null line but not multiline replacement; native preflight truncated. Compatibility echo is not semantic qualification or guaranteed grammar enforcement",
            "hard_constraints": "Current models/context/residency/budgets/scope/validation/Reviewer16/protected contracts unchanged; argument shape is not permission or automatic semantic acknowledgement",
            "sequence": [
                "Read prior tagged/native trials and countertests, freeze baseline and one mode candidate",
                "Offline required fields, multiline/unknown action, missing contract_check, current validation and stale-evidence negative controls",
                "One bounded paired live protocol qualification on existing normal and repair units with all failures included",
                "Independently decide whether any semantic transfer hypothesis is still justified; schema success cannot erase classification failure",
                "Only with explicit new-stage approval register a new fixed execution batch; old D2 remains HOLD",
            ],
            "classification_route": "Unqualified under this original protected contract, Primary-owned pending a separately qualified assisted mode",
            "economic_gate": "UNMEASURED; no permission to claim savings",
            "no_case_substitution_or_relaxed_standard": True,
        },
    )
    print(
        "D2 HOLD: A 3/3, B 2/3; Coder 7 calls / 3 accepted units, Reviewer 3, Explorer 1; I1 blocked"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("accept", "integration", "audit", "hold-audit")
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("unit", nargs="?")
    parser.add_argument("--note")
    parser.add_argument("--arm", default="B")
    args = parser.parse_args()
    if args.action == "accept":
        accept(args.identity, args.unit, args.note)
    elif args.action == "integration":
        integration(args.identity, args.arm)
    elif args.action == "hold-audit":
        hold_audit()
    else:
        audit()
