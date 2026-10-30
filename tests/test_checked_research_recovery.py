import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_support as S
import checked_research_recovery as C


def parent():
    return {
        "status": "failed",
        "failure_reason": "Two unchanged prepared proposals",
        "consolidated_harness": {
            "budget": dict(C.H.BUDGET),
            "seconds": 14,
            "actual": {
                "requests": 4,
                "model_requests": 4,
                "scripted_requests": 0,
                "edits": 2,
                "post_edit_checks": 2,
                "initial_checks": 1,
                "format_preparations": 4,
                "protocol_recoveries": 0,
                "noops": 2,
            },
        },
    }


def test_remaining_credits_deduct_every_parent_use():
    actual = parent()
    before = copy.deepcopy(actual)
    assert C.remaining(actual) == {
        "requests": 8,
        "edits": 1,
        "post_edit_checks": 1,
        "format_preparations": 8,
        "protocol_recoveries": 2,
        "seconds": 886,
    }
    assert actual == before


@pytest.mark.parametrize(
    "change",
    [
        "infra",
        "unsafe",
        "success",
        "protocol",
        "unchecked",
        "exhausted",
        "expanded",
        "scripted",
        "negative",
        "bool",
        "time",
    ],
)
def test_ineligible_parent_fails_closed(change):
    value = parent()
    facts, counts = (
        value["consolidated_harness"],
        value["consolidated_harness"]["actual"],
    )
    if change == "infra":
        value["infra_failure"] = {"reason": "busy"}
    elif change in ("unsafe", "success"):
        value["status"] = (
            "policy_violation"
            if change == "unsafe"
            else "validation_passed_pending_review"
        )
    elif change == "protocol":
        value["failure_reason"] = "Protocol recovery budget exhausted"
    elif change == "unchecked":
        counts["post_edit_checks"] = 1
    elif change == "exhausted":
        counts["edits"] = counts["post_edit_checks"] = 3
    elif change == "expanded":
        facts["budget"]["requests"] = 13
    elif change == "scripted":
        counts["scripted_requests"] = 1
    elif change == "negative":
        counts["format_preparations"] = -1
    elif change == "bool":
        counts["format_preparations"] = True
    elif change == "time":
        facts["seconds"] = 900
    with pytest.raises(ValueError):
        C.remaining(value)


@pytest.mark.parametrize(
    "change", [None, "missing", "stale", "outside", "failed", "no_findings"]
)
def test_local_advice_requires_exact_fresh_approved_sources(tmp_path, change):
    (tmp_path / "source.py").write_text("value = 1", encoding="utf-8")
    (tmp_path / "tests.py").write_text("assert True", encoding="utf-8")
    required = ["source.py", "tests.py"]
    report = {
        "status": "success",
        "findings": ["Untrusted local research."],
        "observed_hashes": {p: S.sha(tmp_path / p) for p in required},
    }
    if change == "missing":
        report["observed_hashes"].pop("tests.py")
    elif change == "stale":
        report["observed_hashes"]["source.py"] = "stale"
    elif change == "outside":
        report["observed_hashes"]["../private.py"] = "outside"
    elif change == "failed":
        report["status"] = "failed"
    elif change == "no_findings":
        report["findings"] = []
    if change is not None:
        with pytest.raises(ValueError):
            C.feedback(report, tmp_path, required)
    else:
        notes = C.feedback(report, tmp_path, required)
        assert notes == [
            {
                "source": "local_explorer_untrusted",
                "text": "Untrusted local research.",
                "verify_in_review": False,
            }
        ]
