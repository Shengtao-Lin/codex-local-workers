"""Diagnostic proposal scope and approval are independent of model claims."""

import importlib.util
import sys
from pathlib import Path

import pytest

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
spec = importlib.util.spec_from_file_location(
    "limit_direct_guard_test", BENCHMARKS / "limit_direct_trial.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_proposal_requires_exact_existing_writable_path_and_complete_string():
    good = {"path": module.trial.COMMON, "content": "# proposal\n"}
    assert module.checked_proposal(good) == good
    for invalid in (
        {"path": "../sibling.py", "content": "# escaped"},
        {"path": "tests/unit/test_limit_recovery.py", "content": "# weakened"},
        {"path": module.trial.COMMON, "content": "", "success": True},
        {"path": module.trial.COMMON, "content": ""},
        {"path": module.trial.COMMON, "content": 1},
        {"path": module.trial.COMMON, "content": "x" * 20_001},
    ):
        with pytest.raises(ValueError):
            module.checked_proposal(invalid)


def test_apply_requires_review_of_exact_proposal_before_editor_construction(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(module.trial, "BASE", tmp_path)
    root = tmp_path / "semantic-direct-1"
    (root / ".agent").mkdir(parents=True)
    module.write(root / ".agent/manifest.json", {"files": {}})
    module.write(
        root / ".agent/direct-proposal.json",
        {"path": module.trial.COMMON, "content": "# untrusted"},
    )
    module.write(
        root / ".agent/direct-primary-review.json",
        {"proposal_sha256": "wrong", "safe_to_validate": True},
    )
    monkeypatch.setattr(
        module,
        "load_worker",
        lambda _: pytest.fail("Editor must not be constructed before approval"),
    )
    with pytest.raises(ValueError, match="Primary review required"):
        module.apply_reviewed("semantic-direct-1")
