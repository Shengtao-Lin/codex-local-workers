"""The ablation keeps scoped/hash/exact-match edits and unchanged acceptance."""

import importlib.util
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCH))
spec = importlib.util.spec_from_file_location("comparison_controls", BENCH / "harness_repair_comparison.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)
runtime = comparison.common.load("comparison_control_runtime", comparison.KIT / ".local-agents/worker-runtime.py")


@pytest.mark.parametrize("failure", ["scope", "stale", "noop", "absent", "duplicate", "fields"])
def test_rejected_proposal_never_mutates_source(tmp_path, failure):
    target = tmp_path / comparison.SOURCE
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 1\nVALUE = 1\n", encoding="utf-8")
    protected = tmp_path / "tests/protected.py"
    protected.parent.mkdir()
    protected.write_text("VALUE = 1\n", encoding="utf-8")
    before = target.read_bytes()
    proposal = {"path": comparison.SOURCE, "expected_sha256": comparison.common.sha(target),
                "find": "VALUE = 1\nVALUE = 1", "replace": "VALUE = 2"}
    if failure == "scope":
        proposal["path"] = "tests/protected.py"
        proposal["expected_sha256"] = comparison.common.sha(protected)
    elif failure == "stale":
        proposal["expected_sha256"] = "0" * 64
    elif failure == "noop":
        proposal["replace"] = proposal["find"]
    elif failure == "absent":
        proposal["find"] = "NOT_PRESENT"
    elif failure == "duplicate":
        proposal["find"] = "VALUE = 1"
    elif failure == "fields":
        proposal["shell"] = "invalid"
    with pytest.raises((ValueError, runtime.SafeEditError)):
        comparison.apply_patch_proposal(runtime, tmp_path, proposal)
    assert target.read_bytes() == before
    assert protected.read_text(encoding="utf-8") == "VALUE = 1\n"


def test_valid_exact_block_is_model_content_not_host_generated_repair(tmp_path):
    target = tmp_path / comparison.SOURCE
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 1\n", encoding="utf-8")
    proposal = {"path": comparison.SOURCE, "expected_sha256": comparison.common.sha(target),
                "find": "VALUE = 1", "replace": "VALUE = 2"}
    comparison.apply_patch_proposal(runtime, tmp_path, proposal)
    assert target.read_text(encoding="utf-8") == "VALUE = 2\n"


def test_experiment_has_fixed_original_acceptance_and_no_product_release():
    assert "159 > 100" in comparison.REPAIR
    assert "Keep all existing behavior" in comparison.REPAIR
    assert set(comparison.PATCH_SCHEMA["required"]) == {"path", "expected_sha256", "find", "replace"}
