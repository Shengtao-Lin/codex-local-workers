"""Protect mixed coverage registration independently of model outcomes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "benchmarks"))
import coordinator_numeric_case as fixture


def test_parser_is_one_cohesive_two_file_unit():
    case = fixture.case()
    parser, collector, receipt = case["units"]
    assert parser["paths"] == ["src/product/schema.py", "src/product/labels.py"]
    assert set(parser["anchors"]) == set(parser["paths"])
    assert all(unit["risk"] == "medium" for unit in case["units"])
    assert receipt["dependencies"] == [parser["unit_id"], collector["unit_id"]]
    assert case["feature_risk"] == case["integration_risk"] == "medium"


def test_contract_has_numeric_boundary_and_no_io_rejection():
    case = fixture.case()
    scenarios = {s["id"]: s for s in case["units"][2]["acceptance_scenarios"]}
    assert scenarios["numeric-rejection-before-io"]["observables"]["fetch_calls"] == 0
    assert scenarios["numeric-roundtrip"]["observables"]["keys"] == [2, -1, 0, 3, 2]
    assert "assert type(key) is int" in fixture.TESTS
    assert 'asyncio.run(run_batch(fetch,["1","bad","2"]))' in fixture.TESTS
    assert set(fixture.REFERENCE) <= set(case["files"])
