from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
SPEC = importlib.util.spec_from_file_location(
    "localization_route_smoke_under_test",
    ROOT / "benchmarks" / "localization_route_smoke.py",
)
assert SPEC is not None and SPEC.loader is not None
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)


def test_runtime_manifest_is_stable_and_detects_role_configuration_changes() -> None:
    first = SMOKE.runtime_manifest({"explorer_model": "oss", "reviewer_model": "muse"})
    reordered = SMOKE.runtime_manifest(
        {"reviewer_model": "muse", "explorer_model": "oss"}
    )
    changed = SMOKE.runtime_manifest(
        {"explorer_model": "oss", "reviewer_model": "other"}
    )
    assert first == reordered
    assert first["runtime_sha256"] != changed["runtime_sha256"]
    assert first["runtime_manifest"]["files"]["benchmarks/localization_route_smoke.py"]


def test_preregistered_cohort_has_eleven_distinct_behavior_types() -> None:
    cohort = json.loads(
        (ROOT / "benchmarks" / "localization-cohort-v2.1.json").read_text(
            encoding="utf-8"
        )
    )
    names = cohort["standard_cases"]
    assert cohort["rounds"] == 2
    assert cohort["question_version"] == 2
    assert len(names) == len(set(names)) == 10
    assert cohort["split_case"] == "sample-identity"
    assert cohort["split_case"] not in names
    assert cohort["per_round_distinct_behavior_types"] == len(names) + 1 == 11
    available = {case.name for case in SMOKE.STABILITY.CASES}
    assert set(names) | {cohort["split_case"]} <= available
    config = json.loads(
        (ROOT / ".local-agents" / "config.json").read_text(encoding="utf-8-sig")
    )
    assert cohort["role_models"] == {
        role: config[f"{role}_model"] for role in ("explorer", "coder", "reviewer")
    }
