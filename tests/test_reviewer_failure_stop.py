import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from normal_task_trial import reviewer_failed


def test_failed_reviewer_stops_even_when_coder_passed_and_summary_exists():
    summary = {
        "reviewer_started": True,
        "coder_status": "validation_passed_pending_review",
    }
    assert reviewer_failed(
        summary,
        {"decision": "failed", "infra_failure": {"reason_code": "output_token_limit"}},
    )
    assert reviewer_failed(summary, {})


def test_semantic_rework_escalate_and_diagnostic_not_run_are_not_infrastructure():
    for decision in ("pass_to_primary", "rework", "escalate"):
        assert not reviewer_failed({"reviewer_started": True}, {"decision": decision})
    assert not reviewer_failed({"reviewer_started": False}, {})
