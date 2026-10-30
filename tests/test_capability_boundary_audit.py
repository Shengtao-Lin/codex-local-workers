"""Offline labels and the existing scope gate; no model, writes or dispatch."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
import capability_boundary_audit as audit

spec = importlib.util.spec_from_file_location(
    "boundary_existing_limited", ROOT / ".local-agents/coordinator-limited.py"
)
limited = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limited)


@pytest.mark.parametrize(
    "counts,same,expected",
    [
        ((2, 2, 2), False, "HISTORICAL_ONLY"),
        ((2, 2, 2), True, "EXACT_REPEAT_EVIDENCE"),
        ((1, 2, 2), True, "UNQUALIFIED_WITHIN_RECORDED_SCOPE"),
        ((0, 2, 2), True, "UNQUALIFIED_WITHIN_RECORDED_SCOPE"),
        ((0, 0, 2), True, "NOT_EVALUATED"),
        ((1, 1, 2), True, "UNQUALIFIED_WITHIN_RECORDED_SCOPE"),
    ],
)
def test_labels_do_not_generalize(counts, same, expected):
    assert audit.disposition(*counts, same_candidate=same) == expected


def test_real_evidence_has_no_automatic_grants():
    report = audit.audit()
    assert len(report["rows"]) == 8
    assert report["current_local_dispatch_grants"] == 0
    assert sum(r["status"] == "HISTORICAL_ONLY" for r in report["rows"]) == 2
    assert all(
        r["current_dispatch"] == "PRIMARY_DECISION_REQUIRED" for r in report["rows"]
    )


@pytest.mark.parametrize("mutation", [None, "owner", "scope", "create", "evidence"])
def test_reuses_existing_route_guard(mutation):
    # Synthetic authority control, NOT an actual task qualification or new grant.
    plan = {
        "contracts": [{"id": "known"}],
        "units": [
            {
                "owner": "primary",
                "owned_contract_ids": ["known"],
                "scope_authority": {"modify": ["src/unit.py"], "create": []},
            }
        ],
    }
    catalog = {
        "known": {
            "owner": "primary",
            "route": "primary_owned",
            "modify": ["src/unit.py"],
            "evidence": "Primary review required",
        }
    }
    unit = plan["units"][0]
    if mutation == "owner":
        unit["owner"] = "local-coder"
    elif mutation == "scope":
        unit["scope_authority"]["modify"].append("src/other.py")
    elif mutation == "create":
        unit["scope_authority"]["create"] = ["src/new.py"]
    elif mutation == "evidence":
        catalog["known"]["evidence"] = ""
    if mutation:
        with pytest.raises(ValueError):
            limited.route_plan(plan, catalog)
    else:
        assert limited.route_plan(plan, catalog) == plan
