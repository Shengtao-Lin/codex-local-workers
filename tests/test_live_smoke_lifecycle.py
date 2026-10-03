from __future__ import annotations

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "live_smoke_lifecycle_under_test",
    Path(__file__).resolve().parents[1] / "benchmarks" / "live_smoke.py",
)
assert SPEC is not None and SPEC.loader is not None
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)


def test_active_lifecycle_policy_is_preserved() -> None:
    source = {
        "single_model_residency": True,
        "model_switch_timeout_seconds": 360,
        "reviewer_preload_model": True,
        "reviewer_model_load_timeout_seconds": 360,
        "reviewer_reasoning_strength": "low",
        "python": "do-not-copy",
    }
    target = {"python": "fixture-python"}
    SMOKE.inherit_lifecycle_config(source, target)
    assert target == {**source, "python": "fixture-python"}


def test_absent_optional_settings_do_not_change_legacy_defaults() -> None:
    target = {"reviewer_require_approved_execution": True}
    SMOKE.inherit_lifecycle_config({}, target)
    assert target == {"reviewer_require_approved_execution": True}
