import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import strata_complex_tasks as tasks


def test_only_supported_capture_units_are_registered():
    specs = tasks.tasks()
    assert set(specs) == {"tools", "raw"}
    assert specs["tools"]["family"] == "collect-tools-json-observation-v1"
    assert specs["raw"]["family"] == "mapping-raw-utf8-v1"
    assert all(spec["cases"] for spec in specs.values())


def test_public_private_and_references_parse_and_external_fixture_is_explicit():
    for spec in tasks.tasks().values():
        for key in ("public", "private", "reference"):
            ast.parse(spec[key])
    assert "from tests.conftest import application" in tasks.tasks()["tools"]["private"]
