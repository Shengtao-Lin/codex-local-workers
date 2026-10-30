"""Portable checks for the strengthened fixture registration."""

import ast
import sys
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

import real_adapter_fidelity as trial


def test_strengthened_contract_and_collection():
    assert trial.EXPECTED_COUNT == 47
    assert trial.EXTRA in trial.TESTS
    assert "original parser exception object" in trial.BEHAVIOR
    assert "All tests and other source files are read-only" in trial.BEHAVIOR
    tree = ast.parse(trial.SUPPORT.read_text(encoding="utf-8"))
    functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {
        "test_exception_identity",
        "test_adapter_error_fidelity",
        "test_adapter_additional_timestamp_forms",
    } <= functions


def test_repetitions_have_independent_paths_and_unchanged_models():
    source = (BENCHMARKS / "real_adapter_fidelity.py").read_text(encoding="utf-8")
    assert 'f"real-adapter-fidelity-r{round_number}"' in source
    assert "choices=(1, 2, 3)" in source
    assert trial.live.SNAPSHOT.name == "real-adapter-live-baseline-1"
