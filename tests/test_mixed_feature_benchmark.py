from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
CORPUS = json.loads((KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text())
SPEC = importlib.util.spec_from_file_location(
    "mixed_source_test", KIT / "benchmarks/mixed_source_freeze.py"
)
assert SPEC and SPEC.loader
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)


def test_corpus_has_six_distinct_goals_not_six_success_claims():
    cases = CORPUS["cases"] + CORPUS["external_cases"]
    assert len(cases) == len({case["case_id"] for case in cases}) == 6
    assert CORPUS["rounds"] == 2
    assert all(
        case["official_score"] is False
        for case in cases
        if case["origin"] == "SWE-bench-Lite"
    )


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda case: case["case_id"])
def test_authored_goals_have_real_dependency_and_protected_roundtrip(case):
    units = case["units"]
    assert len(units) == 2
    assert units[1]["dependencies"] == [units[0]["unit_id"]]
    assert units[0]["path"] != units[1]["path"]
    assert units[0]["tests"][0] in units[1]["tests"]
    assert all(test in case["files"] for unit in units for test in unit["tests"])
    assert all(unit["risk"] == case["feature_risk"] for unit in units)


@pytest.mark.parametrize("relative", ["../escape.py", "nested/../../escape.py"])
def test_snapshot_destination_rejects_escape(tmp_path, relative):
    with pytest.raises(ValueError):
        SOURCE.destination(tmp_path, relative)


def test_snapshot_destination_accepts_scoped_file(tmp_path):
    assert SOURCE.destination(tmp_path, "src/example.py") == tmp_path / "src/example.py"
