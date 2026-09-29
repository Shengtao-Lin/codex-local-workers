from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
SPEC = importlib.util.spec_from_file_location(
    "sample_identity_split_route",
    ROOT / "benchmarks" / "sample_identity_split_route.py",
)
assert SPEC is not None and SPEC.loader is not None
SPLIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SPLIT)


def test_split_plan_owns_disjoint_contracts_and_protected_tests() -> None:
    base = {
        "required_behavior": [
            {
                "id": f"behavior-{index}",
                "text": f"Behavior {index}",
                "risk_floor": "medium",
            }
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


def test_split_inspection_replays_both_run_refs_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed = []

    def fake_run(root: Path, argv: list[str], timeout: int) -> SimpleNamespace:
        observed.append((root, argv, timeout))
        return SimpleNamespace(
            returncode=0, stdout=json.dumps({"status": "eligible"}), stderr=""
        )

    monkeypatch.setattr(SPLIT.STABILITY, "run_command", fake_run)
    result = SPLIT.inspect_feature(tmp_path)
    assert result == {"inspection_exit": 0, "inspection": {"status": "eligible"}}
    assert observed[0][0] == tmp_path
    assert observed[0][2] == 30
    argv = observed[0][1]
    assert "--inspect-feature" in argv
    assert argv.count("--run-ref") == 2
    assert argv[-8:] == [
        "--run-ref",
        "fingerprint",
        SPLIT.TASK_ID,
        "fingerprint-a1",
        "--run-ref",
        "reuse-key",
        SPLIT.TASK_ID,
        "reuse-key-a1",
    ]
    assert list(tmp_path.iterdir()) == []


def test_split_phases_reject_changed_frozen_provenance(tmp_path: Path) -> None:
    path = tmp_path / ".agent" / "split-provenance.json"
    SPLIT.STABILITY.write_json(path, SPLIT.split_provenance())
    SPLIT.require_frozen_provenance(tmp_path)
    changed = SPLIT.read_json(path)
    changed["case_input_sha256"] = "0" * 64
    SPLIT.STABILITY.write_json(path, changed)
    with pytest.raises(ValueError, match="runtime, role config, or case input changed"):
        SPLIT.require_frozen_provenance(tmp_path)
