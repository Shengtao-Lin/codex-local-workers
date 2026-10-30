"""Navigation must not request another Reviewer after a completed current review."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local-agents"))
from bounded import primary_receipt as R


def inputs(decision="pass_to_primary"):
    return (
        {
            "status": "validation_passed_pending_review",
            "validation": {"status": "passed"},
            "next_action_required": "local_review",
        },
        {
            "reviewer_started": True,
            "reviewer_input_authenticated": True,
            "reviewer_exit": 0,
            "reviewer_decision": decision,
            "automatic_coder_rework": False,
        },
        {},
    )


@pytest.mark.parametrize(
    "decision,expected",
    [
        ("pass_to_primary", "primary_risk_routed_review"),
        ("rework", "primary_finding_disposition"),
        ("escalate", "primary_contract_or_scope_decision"),
    ],
)
def test_completed_review_never_requests_duplicate_dispatch(decision, expected):
    report, summary, reviewer = inputs(decision)
    before = copy.deepcopy((report, summary, reviewer))
    receipt = R.build(report, summary, reviewer, {})
    assert receipt["next_action_required"] == expected
    assert receipt["coder_next_action_required"] == "local_review"
    assert receipt["primary_acceptance"] == "not_recorded_by_this_entry"
    assert receipt["automatic_coder_rework"] is False
    assert (report, summary, reviewer) == before


@pytest.mark.parametrize(
    "fault",
    ["unauthenticated", "nonzero", "not_started", "bad_coder", "bad_validation"],
)
def test_contradictory_pass_points_to_evidence_reconciliation(fault):
    report, summary, reviewer = inputs()
    if fault == "unauthenticated":
        summary["reviewer_input_authenticated"] = False
    elif fault == "nonzero":
        summary["reviewer_exit"] = 2
    elif fault == "not_started":
        summary["reviewer_started"] = False
    elif fault == "bad_coder":
        report["status"] = "failed"
    else:
        report["validation"]["status"] = "failed"
    receipt = R.build(report, summary, reviewer, {})
    assert receipt["next_action_required"] == "primary_evidence_reconciliation"


def test_failed_reviewer_is_diagnosis_not_semantic_reroll():
    report, summary, reviewer = inputs("failed")
    summary.update(reviewer_input_authenticated=False, reviewer_exit=2)
    assert (
        R.build(report, summary, reviewer, {})["next_action_required"]
        == "primary_review_infrastructure_diagnosis"
    )


def test_offline_inspection_is_not_request_for_live_or_acceptance():
    report, summary, reviewer = inputs("NOT_RUN")
    summary["reviewer_started"] = False
    reviewer["mode"] = "offline-input-inspection"
    assert (
        R.build(report, summary, reviewer, {})["next_action_required"]
        == "offline_inspection_only"
    )


@pytest.mark.parametrize(
    "status", ["failed", "blocked", "interrupted", "policy_violation"]
)
def test_failed_coder_requires_primary_disposition_not_retry(status):
    report, summary, reviewer = inputs("NOT_RUN")
    report["status"] = status
    summary.update(reviewer_started=False, reviewer_input_authenticated=False)
    assert (
        R.build(report, summary, reviewer, {})["next_action_required"]
        == "primary_failure_disposition"
    )


def test_missing_or_undispatched_success_is_not_automatic_review_authority():
    assert (
        R.build({}, {}, None, {})["next_action_required"]
        == "primary_evidence_reconciliation"
    )
    report, summary, reviewer = inputs("NOT_RUN")
    summary.update(reviewer_started=False, reviewer_input_authenticated=False)
    assert (
        R.build(report, summary, reviewer, {})["next_action_required"]
        == "primary_evidence_reconciliation"
    )
