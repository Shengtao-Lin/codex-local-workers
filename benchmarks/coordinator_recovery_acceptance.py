"""Verify recovered live unit and run independent full protected integration."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import coordinator_failure_terminal_retry as candidate
import layer_isolation as checks
from capability_fit import write
from inherited_context_recovery import digest, read


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


if __name__ == "__main__":
    candidate.configure()
    root, supervised, plan, initial, _ = candidate.retry.original.context()
    registration = read(candidate.BASE / "registration.json")
    proposal = (
        root
        / ".agent/coordinator"
        / plan["feature_id"]
        / "proposals/authorized-recovery"
    )
    actual = read(proposal / "packet.json")
    archive = root / ".agent/tasks" / initial["task_id"] / "runs" / actual["run_id"]
    coder = read(archive / "handoff.json")
    primary = read(archive / "review.json")
    reviewer = read(
        root
        / ".agent/tasks"
        / initial["task_id"]
        / "reviews"
        / primary["local_review_id"]
        / "handoff.json"
    )
    for field in (
        "scope",
        "required_behavior",
        "acceptance_criteria",
        "acceptance_scenarios",
        "required_order",
        "forbidden_orderings",
        "focused_tests",
        "validation_profile",
        "dependencies",
        "owned_contract_ids",
    ):
        require(actual[field] == initial[field], "hard contract drift: " + field)
    require(
        all(
            actual["risk"][key] == initial["risk"][key]
            for key in ("feature", "unit", "integration")
        ),
        "risk drift",
    )
    require(
        actual["run_id"] == initial["run_id"].replace("-a1", "-a2")
        and actual["attempt"] == actual["packet_revision"] == 2,
        "recovery identity drift",
    )
    require(
        read(proposal / "decision.json")["output"]["decision"] == "REWORK_LOCAL",
        "not authorized live rework decision",
    )
    require(
        read(proposal / "proposal.json")["status"] == "protocol_valid",
        "invalid live proposal",
    )
    observation = (
        root
        / ".agent/coordinator"
        / plan["feature_id"]
        / "proposals/unapproved-failure-observation"
    )
    require(
        read(observation / "decision.json")["output"]["decision"] == "ESCALATE_PRIMARY"
        and not (observation / "packet.json").exists()
        and not (observation / "proposal.json").exists(),
        "unapproved failure launched proposal",
    )
    parent = archive.parent / initial["run_id"]
    injected = read(root / ".agent/verified-injected-failure.json")
    require(
        digest(parent / "completed.json") == injected["completed_sha256"]
        and digest(parent / "handoff.json") == injected["handoff_sha256"]
        and injected["actual_junit"]["executed"] == 7
        and injected["actual_junit"]["failures"] == 2,
        "injected parent evidence drift",
    )
    validation = coder["validation"]
    require(
        coder["status"] == "ready_for_review"
        and primary["decision"] == "accept"
        and reviewer["decision"] == "pass_to_primary"
        and reviewer["runtime_facts"]["inputs_unchanged"]
        and validation["status"] == "passed"
        and validation["focused_tests"]["inputs_unchanged"]
        and validation["focused_tests"]["junit"]["executed"] == 7
        and all(c["status"] == "passed" for c in validation["configured_checks"]),
        "recovered unit not accepted/validated/reviewed",
    )
    require(
        [c["path"] for c in coder["changed_files"]] == ["src/product/labels.py"],
        "unexpected recovered changes",
    )
    change = coder["changed_files"][0]
    require(
        change["initial_sha256"]
        == read(parent / "handoff.json")["changed_files"][0]["final_sha256"],
        "failed draft continuity missing",
    )
    expected = dict(registration["files"])
    expected[change["path"]] = change["final_sha256"]
    require(
        all(digest(root / path) == sha for path, sha in expected.items()),
        "protected source/test or recovered source drift",
    )
    junit = root / ".agent/recovery-integration-1.xml"
    require(not junit.exists(), "integration observation must be new")
    results = [
        checks.command(
            root,
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--basetemp={root / 'recovery-integration-temp-1'}",
                f"--junitxml={junit}",
            ],
        ),
        checks.command(root, [sys.executable, "-m", "ruff", "check", "src", "tests"]),
        checks.command(
            root, [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"]
        ),
    ]
    counts = {
        k: sum(int(s.get(k, 0)) for s in ET.parse(junit).getroot().iter("testsuite"))
        for k in ("tests", "failures", "errors", "skipped")
    }
    require(
        counts == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}
        and all(c["exit"] == 0 for c in results),
        "independent recovery integration failed",
    )
    require(
        all(digest(root / path) == sha for path, sha in expected.items()),
        "integration inputs changed",
    )
    refs = {"repair-unit": {k: actual[k] for k in ("task_id", "run_id")}}
    evidence = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "plan_revision": plan["plan_revision"],
        "primary_plan_sha256": supervised.CONTRACT.authority_fingerprint(plan),
        "integration_risk": plan["integration_risk"],
        "status": "passed",
        "checks": [
            {"id": f"integration-{i}", "status": "passed", "exit_code": c["exit"]}
            for i, c in enumerate(results)
        ],
        "files": [{"path": p, "sha256": sha} for p, sha in expected.items()],
        "junit_sha256": digest(junit),
        "primary_feature_accepted": False,
    }
    write(
        root / ".agent/integration" / plan["feature_id"] / "validation.json", evidence
    )
    supervised.CONTRACT.verify_integration_archive(plan, root, refs)
    facts = {
        "driver_sha256": digest(Path(__file__)),
        "initial_failure_local_llm_credit": False,
        "live_unapproved_escalation": True,
        "live_authorized_rework_decision": True,
        "live_proposal": True,
        "live_coder_ready": True,
        "fresh_reviewer_pass": True,
        "primary_unit_accepted": True,
        "junit": counts,
        "checks": results,
        "protected_inputs_unchanged": True,
        "canonical_integration_verified": True,
        "primary_feature_acceptance_not_inferred": True,
    }
    write(candidate.BASE / "recovery-facts-1.json", facts)
    print(json.dumps(facts, indent=2))
