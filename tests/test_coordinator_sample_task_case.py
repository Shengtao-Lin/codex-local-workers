import ast
import importlib.util
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCH))
spec = importlib.util.spec_from_file_location(
    "sample_task_case", BENCH / "coordinator_sample_task_case.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def test_sample_task_preserves_qualified_scope_and_adds_boundary_coverage():
    task = fixture.case()
    assert task["feature_risk"] == task["integration_risk"] == "medium"
    assert len(task["units"]) == 3
    assert task["units"][0]["paths"] == [
        "src/product/schema.py",
        "src/product/labels.py",
    ]
    assert task["units"][2]["dependencies"] == ["normalize-unit", "collect-unit"]
    names = {
        node.name
        for node in ast.parse(fixture.TESTS).body
        if isinstance(node, ast.FunctionDef)
    }
    assert len(names) == 7
    assert "1_000" in fixture.TESTS and "1__0" in fixture.TESTS
    assert "Pending" in task["units"][0]["contract"]
    assert "separately owned" in task["units"][1]["contract"]


def test_case_is_fresh_and_does_not_mutate_original():
    first = fixture.case()
    first["units"][0]["contract"] = "changed"
    assert fixture.case()["units"][0]["contract"] != "changed"
    assert fixture.numeric.case()["files"]["tests/test_target.py"] != fixture.TESTS
