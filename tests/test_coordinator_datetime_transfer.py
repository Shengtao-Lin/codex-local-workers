"""Fixture authority and boundary coverage, independent of live outcomes."""

import ast
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "benchmarks"))
import coordinator_datetime_transfer as fixture


def test_single_private_unit_preserves_protected_context():
    case = fixture.case()
    assert len(case["units"]) == 1
    unit = case["units"][0]
    assert unit["path"] == "src/product/target.py"
    assert unit["dependencies"] == []
    assert unit["risk"] == case["feature_risk"] == case["integration_risk"] == "medium"
    assert {scenario["id"] for scenario in unit["acceptance_scenarios"]} == {
        "normal",
        "error",
        "boundary",
    }
    assert "No wider adapter, public API" in unit["contract"]


def test_seven_actual_protected_assertion_functions():
    names = {
        node.name
        for node in ast.parse(fixture.TESTS).body
        if isinstance(node, ast.FunctionDef)
    }
    tests = fixture.case()["units"][0]["tests"]
    assert len(tests) == len(names) == 7
    assert {node.split("::")[1] for node in tests} == names
    assert 'normalize_time("bad", DEFAULT)' in fixture.TESTS
    assert "assert _datetime(value, DEFAULT) is value" in fixture.TESTS
    assert "assert _datetime(value, DEFAULT) is DEFAULT" in fixture.TESTS


def test_injected_mutant_is_not_a_production_bug_claim():
    namespace = {}
    exec(compile(fixture.INITIAL, "<registered-mutant>", "exec"), namespace)  # noqa: S102 - trusted registered fixture
    convert = namespace["_datetime"]
    default = datetime(2000, 1, 1, tzinfo=UTC)
    assert convert("2026-10-07T03:04:05", default).tzinfo is None
    assert convert("invalid", default) is default
    value = datetime(2026, 1, 1)  # noqa: DTZ001 - naive identity is the tested contract
    assert convert(value, default) is value


def test_frozen_original_private_function_satisfies_boundaries():
    # Read-only production definition; tests never run the real project's module
    # imports, fixtures or plugins and never write there.
    source = fixture.SOURCE.read_text(encoding="utf-8")
    definition = source[source.index("def _datetime(") :]
    namespace = {}
    exec(compile(fixture.HEADER + definition, "<frozen-original>", "exec"), namespace)  # noqa: S102 - trusted read-only extraction
    convert = namespace["_datetime"]
    default = datetime(2000, 1, 1, tzinfo=UTC)
    assert convert("2026-10-07T03:04:05", default).tzinfo is UTC
    assert convert(None, default) is default
    with pytest.raises(ValueError):
        convert("invalid", default)
