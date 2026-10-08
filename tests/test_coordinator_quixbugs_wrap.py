"""Protect external benchmark registration without running local models."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "benchmarks"))
import coordinator_quixbugs_wrap as fixture


def test_pinned_upstream_not_moving_branch():
    assert len(fixture.COMMIT) == 40
    assert fixture.COMMIT in fixture.UPSTREAM
    assert "master" not in fixture.UPSTREAM


def test_case_is_one_bounded_unit(tmp_path, monkeypatch):
    monkeypatch.setattr(fixture, "BASE", tmp_path)
    source = tmp_path / "upstream/python_programs/wrap.py"
    source.parent.mkdir(parents=True)
    source.write_text("def wrap(text, cols):\n    return []\n", encoding="utf-8")
    vectors = tmp_path / "upstream/json_testcases/wrap.json"
    vectors.parent.mkdir(parents=True)
    vectors.write_text('[["abc", 4], ["abc"]]\n', encoding="utf-8")
    case = fixture.case()
    assert len(case["units"]) == 1
    unit = case["units"][0]
    assert unit["path"] == "src/product/target.py"
    assert unit["dependencies"] == []
    assert unit["risk"] == case["feature_risk"] == case["integration_risk"] == "medium"
    assert case["files"]["tests/official-wrap.json"] == vectors.read_text(
        encoding="utf-8"
    )
    assert (
        "No wider" not in unit["contract"]
    )  # Scope is benchmark-specific, not copied datetime semantics.
    assert "real benchmark defect" in unit["contract"]


def test_official_and_boundary_coverage_is_distinct():
    functions = {
        node.name
        for node in ast.parse(fixture.TESTS).body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }
    assert len(functions) == 7
    assert {
        "test_official_cases",
        "test_narrow_leading_space_progress",
        "test_seeded_invariants",
    } <= functions
    assert "assert len(cases) == 5" in fixture.TESTS
    assert "range(80)" in fixture.TESTS


def test_no_extra_dependencies_for_nonprogress_guard():
    tree = ast.parse(fixture.TESTS)
    imports = {node.names[0].name for node in tree.body if isinstance(node, ast.Import)}
    assert imports == {"json", "random", "sys"}
    assert "sys.settrace(previous)" in fixture.TESTS
    assert "steps > 10000" in fixture.TESTS
    assert "cols = rng.randrange(1, 10)" in fixture.TESTS
