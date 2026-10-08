import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
from atomic_acceptance_cases import apply_ledger


@pytest.mark.parametrize("case", ["window-groups", "timeout-roundtrip"])
def test_ledger_preserves_unit_authority_goal_and_risk(case):
    packet = {
        "unit_id": "one-cohesive-unit",
        "goal": "unchanged original contract",
        "risk": {"unit": "medium", "feature": "medium", "integration": "high"},
        "scope": {
            "read": ["src", "tests"],
            "modify": ["src/a.py"],
            "readonly": ["tests/test_a.py"],
        },
        "focused_tests": ["tests/test_a.py"],
        "required_behavior": [{"id": "old", "text": "unchanged original contract"}],
        "owned_contract_ids": ["old"],
        "acceptance_scenarios": [{"id": "normal", "text": "tests pass"}],
    }
    before = copy.deepcopy(packet)
    revised = apply_ledger(packet, case)
    assert packet == before
    changed = {key for key in packet if packet[key] != revised[key]}
    assert changed == {
        "required_behavior",
        "owned_contract_ids",
        "acceptance_scenarios",
    }
    assert (
        len(revised["owned_contract_ids"])
        == len(set(revised["owned_contract_ids"]))
        == 5
    )
    assert all(
        item["risk_floor"] == packet["risk"]["unit"]
        for item in revised["required_behavior"]
    )
    assert revised["scope"] == packet["scope"]
    assert "subclass" in str(revised["required_behavior"])
    assert "Do not mutate" in str(
        revised["required_behavior"]
    ) or "Neither function mutates" in str(revised["required_behavior"])
