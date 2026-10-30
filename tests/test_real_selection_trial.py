"""Verify the new held-out real source fixture independently of live archives."""

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCH))
spec = importlib.util.spec_from_file_location(
    "real_selection_tests", BENCH / "real_selection_trial.py"
)
trial = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = trial
spec.loader.exec_module(trial)


def test_original_closure_and_primary_tests_are_frozen():
    provenance = json.loads(
        (trial.FROZEN / "provenance.json").read_text(encoding="utf-8")
    )
    assert len(provenance["original_files"]) == 29
    for path, expected in provenance["original_files"].items():
        assert (
            hashlib.sha256((trial.FROZEN / path).read_bytes()).hexdigest() == expected
        )
    extra = provenance["primary_test"]
    assert (
        hashlib.sha256((trial.FROZEN / extra["path"]).read_bytes()).hexdigest()
        == extra["sha256"]
    )
    assert not provenance["production_bug_claimed"]
    assert (
        "src/evaluation_harness/datasets/generator.py" in provenance["original_files"]
    )


def test_task_is_not_timestamp_repetition_or_public_schema_change():
    tree = ast.parse((trial.FROZEN / trial.COMMON).read_text(encoding="utf-8"))
    assert any(
        isinstance(n, ast.FunctionDef) and n.name == "select_records" for n in tree.body
    )
    assert trial.COUNT == 24
    assert "global RNG state is unchanged" in trial.BEHAVIOR
    assert "callback exceptions propagate unchanged" in trial.BEHAVIOR
    assert trial.EXTRA in trial.TESTS
