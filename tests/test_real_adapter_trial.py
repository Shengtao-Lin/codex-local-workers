"""Deterministic scope/provenance checks without importing the sibling repo."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCH))
spec = importlib.util.spec_from_file_location(
    "real_trial_tests", BENCH / "real_adapter_trial.py"
)
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


@pytest.mark.parametrize("mode", ["reference", "naive", "swallow", "combined"])
def test_mutation_preserves_actual_non_helper_code(mode):
    frozen = trial.KIT / "benchmarks/fixtures/real-adapter-datetime-v3"
    source = (frozen / trial.COMMON).read_text(encoding="utf-8")
    mutated = trial.mutate(source, mode)

    def others(text):
        return [
            ast.dump(node)
            for node in ast.parse(text).body
            if not (isinstance(node, ast.FunctionDef) and node.name == "_datetime")
        ]

    assert others(source) == others(mutated)
    assert (source == mutated) is (mode == "reference")


def test_frozen_fixture_provenance_and_real_callers_are_preserved():
    frozen = trial.KIT / "benchmarks/fixtures/real-adapter-datetime-v3"
    provenance = trial.read(frozen / "provenance.json")
    for relative, sha in provenance["copied_original_files"].items():
        assert trial.digest(frozen / relative) == sha
    assert len(provenance["copied_original_files"]) == 21
    assert "tests/unit/test_adapters.py" in provenance["copied_original_files"]
    assert (
        "src/evaluation_harness/adapters/registry.py"
        in provenance["copied_original_files"]
    )
    assert "src/evaluation_harness/errors.py" in provenance["copied_original_files"]
    summary = trial.read(frozen / "trial-summary.json")
    assert summary["local_model_calls"] == 0
    assert summary["source_project_modified"] is False
    assert summary["reference_tests_passed"] == 10
