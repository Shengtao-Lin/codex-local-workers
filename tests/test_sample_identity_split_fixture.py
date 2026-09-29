from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
SPEC = importlib.util.spec_from_file_location(
    "sample_identity_split_route", ROOT / "benchmarks" / "sample_identity_split_route.py"
)
assert SPEC is not None and SPEC.loader is not None
SPLIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SPLIT)


def test_split_plan_owns_disjoint_contracts_and_protected_tests() -> None:
    base = {
        "required_behavior": [
            {"id": f"behavior-{index}", "text": f"Behavior {index}", "risk_floor": "medium"}
            for index in range(1, 5)
        ],
        "acceptance_criteria": [
            {"id": "focused-tests", "text": "Protected focused tests pass."},
            {"id": "static", "text": "Ruff checks pass."},
        ],
    }
    plan = SPLIT.feature_plan(base)
    contract = SPLIT.contract_module()
    assert contract.validate_feature_plan(plan)["effective_unit_risk"] == {
        "fingerprint": "medium",
        "reuse-key": "medium",
    }
    first, second = plan["units"]
    assert first["owned_contract_ids"] == ["behavior-1"]
    assert second["owned_contract_ids"] == ["behavior-2", "behavior-3", "behavior-4"]
    assert second["dependencies"] == ["fingerprint"]
    assert first["scope_authority"]["modify"] == [SPLIT.UNITS["fingerprint"]["target"]]
    assert second["scope_authority"]["modify"] == [SPLIT.UNITS["reuse-key"]["target"]]
    for unit in plan["units"]:
        assert unit["scope_authority"]["readonly"] == [SPLIT.TEST]
        assert all(
            test.startswith(SPLIT.TEST + "::")
            for test in unit["packet_contract"]["required_focused_tests"]
        )
