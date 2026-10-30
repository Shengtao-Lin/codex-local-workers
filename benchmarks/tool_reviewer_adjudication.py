"""Immutable Primary adjudication of actual review evidence, never keyword grading."""

import argparse
import json

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes
from role_usage_facts import summarize
from tool_awaitable_trial import TARGET

OUTCOMES = {
    "correct_detection",
    "correct_clean_pass",
    "false_positive",
    "false_pass",
    "invalid_report",
    "uncertain",
}
COHORTS = ("tool-reviewer-transfer-1", "tool-reviewer-falsification-1")


def review_identity(report, request):
    expected = {
        key: request[key] for key in ("task_id", "unit_id", "run_id", "review_id")
    }
    observed = report.get("identity")
    if observed is not None and observed != expected:
        raise ValueError("terminal report identity differs from trusted request")
    if observed is None and report.get("decision") != "failed":
        raise ValueError("successful semantic report lacks identity")
    return expected


def adjudicate(cohort, arm, outcome, rationale):
    if cohort not in COHORTS or outcome not in OUTCOMES or not rationale.strip():
        raise ValueError("explicit bounded Primary outcome/rationale required")
    base = WORK / cohort
    registration = read(base / "registration.json")
    if arm not in registration["arms_in_order"]:
        raise ValueError("unregistered arm")
    root = base / arm
    facts = read(base / (arm + ".json"))
    report_path = root / ".agent/reviewer.json"
    report = read(report_path)
    decision = report["decision"]
    required_decision = {
        "correct_detection": "rework",
        "correct_clean_pass": "pass_to_primary",
        "false_positive": "rework",
        "false_pass": "pass_to_primary",
        "invalid_report": "failed",
    }
    if outcome in required_decision and decision != required_decision[outcome]:
        raise ValueError("Primary outcome inconsistent with actual terminal decision")
    hidden = "-hidden-" in arm
    if (outcome in {"correct_detection", "false_pass"} and not hidden) or (
        outcome in {"correct_clean_pass", "false_positive"} and hidden
    ):
        raise ValueError("outcome inconsistent with registered hidden/clean artifact")
    if digest(root / TARGET) != facts["source_sha256"]:
        raise ValueError("reviewed artifact drift")
    provenance = read(KIT / "benchmarks/fixtures/tool-awaitable-v5/provenance.json")
    verify_hashes(
        root, {path: sha for path, sha in provenance["files"].items() if path != TARGET}
    )
    identity = review_identity(report, read(root / ".agent/request.json"))["review_id"]
    archive = root / ".agent/tasks" / identity / "reviews" / identity
    events = [
        json.loads(line)
        for line in (archive / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    result = {
        "arm": arm,
        "outcome": outcome,
        "rationale": rationale,
        "actual_decision": decision,
        "reviewer_report_sha256": digest(report_path),
        "source_sha256": facts["source_sha256"],
        "protected_unchanged": True,
        "oracle_exit": facts["oracle_exit"],
        "prepass_challenge_exposed": any(
            event["event"] == "prepass_challenge_issued" for event in events
        ),
        "finding_challenge_exposed": any(
            event["event"] == "finding_challenge_issued" for event in events
        ),
        "local_usage_including_failed_turns": summarize(events),
        "whole_invocation_seconds": read(root / ".agent/invocation.json")["seconds"],
        "coder_invoked": False,
        "explorer_invoked": False,
        "feature_accepted": False,
        "primary_semantic_adjudication": True,
    }
    provisional = archive / "provisional-report.json"
    result["provisional_report_available"] = provisional.exists()
    result["provisional_report_sha256"] = (
        digest(provisional) if provisional.exists() else None
    )
    result["original_challenged_semantic_claim_verified"] = False
    write(base / (arm + ".primary.json"), result)
    print(
        json.dumps(
            {
                "arm": arm,
                "outcome": outcome,
                "prepass_exposed": result["prepass_challenge_exposed"],
                "finding_exposed": result["finding_challenge_exposed"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--cohort", choices=COHORTS, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--outcome", choices=sorted(OUTCOMES), required=True)
    parser.add_argument("--rationale", required=True)
    args = parser.parse_args()
    adjudicate(args.cohort, args.arm, args.outcome, args.rationale)
