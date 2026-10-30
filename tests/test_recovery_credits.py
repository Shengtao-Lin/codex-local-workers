"""Reduced experimental recovery credits cannot replenish the original budget."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_support as S
import consolidated_harness as H
from test_consolidated_harness import prepare, run


@pytest.mark.parametrize(
    "credits",
    [
        {"requests": 13},
        {"seconds": 901},
        {"requests": True},
        {"edits": -1},
        {"requests": 0},
        {"post_edit_checks": 2},
        {"shell": 1},
        [],
    ],
)
def test_invalid_or_enlarged_credits_rejected(credits):
    with pytest.raises(ValueError):
        H.recovery_budget({"experimental_recovery_credits": credits})


def test_original_budget_unchanged_without_opt_in():
    assert H.recovery_budget({}) == H.BUDGET
    assert (
        H.recovery_budget(
            {
                "experimental_recovery_credits": {
                    "requests": 10,
                    "format_preparations": 10,
                }
            }
        )["requests"]
        == 10
    )
    assert H.BUDGET["requests"] == 12


def test_reduced_request_credit_stops_actual_entry(tmp_path):
    root = prepare(tmp_path, "T1", "recovery-credit")
    path = root / ".agent/config.json"
    config = S.read(path)
    config["experimental_recovery_credits"] = {"requests": 1}
    path.write_text(json.dumps(config), encoding="utf-8")
    before = S.sha(root / "src/product/code.py")
    process, report = run(
        root,
        "coder",
        [
            {"_model_error": "output_token_limit"},
            {"blocked_reason": "must not be consumed"},
        ],
    )
    assert process["exit_code"] == 2
    assert report["failure_reason"] == "Request budget exhausted"
    assert report["consolidated_harness"]["actual"]["requests"] == 1
    assert report["consolidated_harness"]["budget"]["requests"] == 1
    assert before == S.sha(root / "src/product/code.py")
