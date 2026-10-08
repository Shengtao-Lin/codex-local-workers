"""Regression checks for explicit policy, without changing old acceptance."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "benchmarks"))
import coordinator_wrap_policy as policy


def test_policy_adds_semantics_without_weakening_tests(monkeypatch):
    prior = {
        "files": {"src/product/target.py": "bug", "tests/test_target.py": "protected"},
        "units": [
            {
                "contract": "original",
                "acceptance_scenarios": [
                    {"observables": {}},
                    {"observables": {"cols": 1}},
                ],
            }
        ],
    }
    before = copy.deepcopy(prior)
    monkeypatch.setattr(policy.original, "case", lambda: prior)
    actual = policy.case()
    assert prior == before
    assert actual["files"] == prior["files"]
    assert actual["units"][0]["contract"] == "original " + policy.POLICY
    boundary = actual["units"][0]["acceptance_scenarios"][1]["observables"]
    assert boundary["cols"] == 1
    assert boundary["split_policy_expected"] == [" ", " a", "bc"]


def test_policy_labels_supplemental_boundary_and_no_zero_progress():
    assert "offset in 1..cols" in policy.POLICY
    assert "emit exactly cols characters" in policy.POLICY
    assert "not an upstream requirement" in policy.POLICY
    assert "Protected assertions are unchanged" in policy.POLICY


def test_new_cohort_does_not_reuse_old_workspace():
    assert policy.BASE != policy.original.BASE
    assert policy.SNAPSHOT != policy.original.SNAPSHOT
