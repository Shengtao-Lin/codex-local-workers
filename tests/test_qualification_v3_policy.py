"""The candidate strengthens packet evidence without changing fixture behavior."""

import importlib.util
import sys
from pathlib import Path


def test_candidate_keeps_sources_tests_and_declares_observable_boundaries():
    benchmarks = Path(__file__).resolve().parents[1] / "benchmarks"
    sys.path.insert(0, str(benchmarks))
    try:
        spec = importlib.util.spec_from_file_location(
            "qualification_candidate_test", benchmarks / "qualification_matrix_v3.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        template = {
            "cases": [
                {
                    "case_id": "display-default",
                    "files": {"tests/test.py": "protected"},
                    "units": [{"unit_id": "qual-unit", "contract": "unchanged"}],
                }
            ]
        }
        result = module.scenarios(template)
        assert result["cases"][0]["files"] == template["cases"][0]["files"]
        assert "acceptance_scenarios" not in template["cases"][0]["units"][0]
        unit = result["cases"][0]["units"][0]
        assert unit["contract"] == "unchanged"
        boundaries = {
            row["id"]: row["observables"] for row in unit["acceptance_scenarios"]
        }
        assert boundaries["present-none"]["key_present"] is True
        assert boundaries["present-none"]["return_value"] is None
        assert boundaries["absent"]["key_present"] is False
        assert boundaries["absent"]["return_value"] == "unnamed"
    finally:
        sys.path.remove(str(benchmarks))
