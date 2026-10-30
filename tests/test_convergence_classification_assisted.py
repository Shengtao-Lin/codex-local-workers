"""C4 collector/probe controls; no real model or worker execution."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import convergence_classification_assisted as trial


@pytest.mark.parametrize(
    "accepted,executed,used,expected",
    [
        (4, 4, 4, "PASS_LIMITED_ASSISTED"),
        (3, 4, 4, "HOLD_CAPABILITY_PRIMARY_OWNED"),
        (2, 2, 4, "HOLD_CAPABILITY_PRIMARY_OWNED"),
        (2, 2, 15, "INCOMPLETE_BUDGET"),
        (3, 4, 15, "HOLD_CAPABILITY_PRIMARY_OWNED"),
        (4, 3, 4, "HOLD_CAPABILITY_PRIMARY_OWNED"),
    ],
)
def test_fixed_denominator_and_budget(accepted, executed, used, expected):
    assert trial.stage_decision(accepted, executed, used) == expected


@pytest.mark.parametrize(
    "body,passed",
    [
        ("return True", True),
        ("return 1", False),
        ("return False", False),
        ("raw.clear(); return True", False),
        ("raise ValueError('actual failure')", False),
    ],
)
def test_independent_probe_requires_true_nonmutation_and_retains_errors(
    tmp_path, body, passed
):
    source = tmp_path / trial.SOURCE
    source.parent.mkdir(parents=True)
    source.write_text(
        "def is_internal_trace(raw):\n    " + body + "\n", encoding="utf-8"
    )
    report = trial.fallback_probe(tmp_path)
    assert report["passed"] is passed
    assert report["expected"] is True
    assert report["new_protected_tests_added"] is False
    if "raise" in body:
        assert (
            report["actual"] is None and report["error"] == "ValueError: actual failure"
        )
