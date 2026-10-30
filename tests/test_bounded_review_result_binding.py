"""A convenience Reviewer report must never stand in for this run's completion."""

import copy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / ".local-agents"))
sys.path.insert(0, str(KIT / "benchmarks"))
import bounded_evidence_support as S
from bounded import capture_fixture_support as F

ENTRY = F.load(KIT / ".local-agents/local-bounded-unit.py", "receipt_binding_entry")


def setup_review(tmp_path, *, decision="pass_to_primary", fault=None, compact=False):
    identity = {"task_id": "task", "unit_id": "unit", "run_id": "run"}
    review_identity = {**identity, "review_id": "auto-run"}
    canonical = {"decision": decision, "identity": review_identity, "findings": []}
    report = copy.deepcopy(canonical)
    completed = {"decision": decision}
    if fault == "stale_identity":
        report["identity"]["run_id"] = "older"
    elif fault == "different_payload":
        report["findings"] = [{"id": "altered"}]
    elif fault == "incomplete":
        completed["decision"] = "failed"
    args = SimpleNamespace(
        review_report=tmp_path / "last-review.json",
        compact_output=compact,
    )
    if fault != "missing_report":
        S.save(args.review_report, [] if fault == "nonobject" else report)
    review_root = tmp_path / ".agent/tasks/task/reviews/auto-run"
    if fault != "missing_canonical":
        S.save(review_root / "handoff.json", canonical)
        S.save(review_root / "completed.json", completed)
    worker = SimpleNamespace(RUN_STATE=SimpleNamespace(write_json_once=S.save))
    gate = SimpleNamespace(verify_handoff=lambda *_args, **_kwargs: identity)
    return args, worker, gate


@pytest.mark.parametrize(
    "fault",
    [
        "nonzero_exit",
        "stale_identity",
        "different_payload",
        "incomplete",
        "missing_canonical",
        "missing_report",
        "nonobject",
    ],
)
def test_failed_or_unbound_review_never_reports_pass(tmp_path, fault):
    args, worker, gate = setup_review(tmp_path, fault=fault)
    with (
        patch.object(ENTRY.F, "load", return_value=gate),
        patch.object(
            ENTRY.subprocess,
            "run",
            return_value=SimpleNamespace(
                returncode=1 if fault == "nonzero_exit" else 0
            ),
        ),
    ):
        result = ENTRY.review(
            tmp_path, args, worker, {"execution_protocol": "p"}, {}, False
        )
    assert result["reviewer_decision"] == "failed"
    assert result["reviewer_input_authenticated"] is False
    assert result.get("reviewer_result_error")


@pytest.mark.parametrize("decision", ["pass_to_primary", "rework", "escalate"])
@pytest.mark.parametrize("compact", [False, True])
def test_valid_canonical_recommendation_is_preserved(tmp_path, decision, compact):
    args, worker, gate = setup_review(tmp_path, decision=decision, compact=compact)

    def process(_command, **kwargs):
        if compact:
            kwargs["stdout"].write("retained Reviewer output\n")
            kwargs["stderr"].write("retained diagnostics\n")
        else:
            assert "stdout" not in kwargs and "stderr" not in kwargs
        return SimpleNamespace(returncode=0)

    with (
        patch.object(ENTRY.F, "load", return_value=gate),
        patch.object(
            ENTRY.subprocess,
            "run",
            side_effect=process,
        ),
    ):
        result = ENTRY.review(
            tmp_path, args, worker, {"execution_protocol": "p"}, {}, False
        )
    assert result["reviewer_decision"] == decision
    assert result["reviewer_input_authenticated"] is True
    if compact:
        archive = tmp_path / ".agent/tasks/task/runs/run"
        assert (
            archive / "reviewer-process.stdout.log"
        ).read_text() == "retained Reviewer output\n"
        assert (
            archive / "reviewer-process.stderr.log"
        ).read_text() == "retained diagnostics\n"


def test_offline_missing_inspection_is_not_authentication(tmp_path):
    args, worker, gate = setup_review(tmp_path, fault="missing_report")
    with (
        patch.object(ENTRY.F, "load", return_value=gate),
        patch.object(
            ENTRY.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0),
        ),
    ):
        result = ENTRY.review(
            tmp_path, args, worker, {"execution_protocol": "p"}, {}, True
        )
    assert result["reviewer_decision"] == "NOT_RUN"
    assert not result["reviewer_input_authenticated"]
