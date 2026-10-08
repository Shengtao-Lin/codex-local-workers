"""Post-edit field shapes are navigation, never confirmations or validation."""

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / ".local-agents/worker-runtime.py"
SPEC = importlib.util.spec_from_file_location("coder_post_edit_hint_test", MODULE)
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


def runtime(tmp_path, config):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/value.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_value.py").write_text(
        "def test_value():\n    assert True\n", encoding="utf-8"
    )
    packet = {
        "schema_version": 2,
        "contract_check_required": True,
        "task_id": "hint-test",
        "run_id": "hint-test-a1",
        "unit_id": "value",
        "goal": "Change value",
        "plan_revision": 1,
        "packet_revision": 1,
        "validation_profile": "python-focused",
        "scope": {
            "read": ["src", "tests"],
            "modify": ["src/value.py"],
            "create": [],
            "forbidden": [],
        },
        "required_behavior": [{"id": "value", "text": "VALUE is 2"}],
        "acceptance_criteria": [{"id": "test", "text": "Tests pass"}],
        "acceptance_scenarios": [
            {"id": "boundary", "text": "Value", "observables": {"value": 2}}
        ],
        "focused_tests": ["tests/test_value.py"],
    }
    return RUNTIME.WorkerRuntime(tmp_path, packet, config, None)


def edit(worker):
    observed = worker.read_file({"path": "src/value.py"})
    worker.write_lock.acquire()
    try:
        return worker.safe_replace(
            {
                "path": "src/value.py",
                "expected_sha256": observed["sha256"],
                "find": "VALUE = 1",
                "replace": "VALUE = 2",
            }
        )
    finally:
        worker.close()


def test_successful_edit_exposes_unknown_packet_shape_without_validation(tmp_path):
    worker = runtime(tmp_path, {"coder_post_edit_validation_hint": True})
    result = edit(worker)
    hint = result["validation_hint"]
    check = hint["example"]["arguments"]["contract_check"]
    assert hint["example"]["action"] == "VALIDATE"
    assert check["required_behavior_ids"] == ["value"]
    assert check["observable_scenario_ids"] == ["boundary"]
    assert check["required_order_confirmed"] is None
    assert check["forbidden_orderings_absent"] is None
    assert worker.last_contract_check is None
    assert worker.validation is None and worker.validation_count == 0
    assert worker.edit_revision == 1 and worker.protocol_errors == 0
    assert worker.packet["required_behavior"][0]["id"] == "value"
    with pytest.raises(RUNTIME.WorkerError, match="requires contract_check"):
        worker._contract_check({})


def test_default_does_not_change_edit_response(tmp_path):
    worker = runtime(tmp_path, {})
    assert "validation_hint" not in edit(worker)


def test_unknown_hint_cannot_confirm_required_order(tmp_path):
    worker = runtime(tmp_path, {"coder_post_edit_validation_hint": True})
    worker.packet["required_order"] = [{"id": "order", "text": "read before write"}]
    check = edit(worker)["validation_hint"]["example"]["arguments"]["contract_check"]
    with pytest.raises(RUNTIME.WorkerError, match="must be boolean true"):
        worker._contract_check({"contract_check": check})
    assert worker.last_contract_check is None


def test_optional_contract_does_not_gain_a_new_requirement(tmp_path):
    worker = runtime(tmp_path, {"coder_post_edit_validation_hint": True})
    worker.packet["contract_check_required"] = False
    assert "validation_hint" not in edit(worker)
    assert worker._contract_check({}) is None


def test_failed_edit_never_creates_hint_or_validation(tmp_path):
    worker = runtime(tmp_path, {"coder_post_edit_validation_hint": True})
    observed = worker.read_file({"path": "src/value.py"})
    worker.write_lock.acquire()
    try:
        with pytest.raises(RUNTIME.SafeEditError, match="not found"):
            worker.safe_replace(
                {
                    "path": "src/value.py",
                    "expected_sha256": observed["sha256"],
                    "find": "absent",
                    "replace": "new",
                }
            )
        assert worker.edit_revision == 0
        assert worker.validation_count == 0 and worker.last_contract_check is None
    finally:
        worker.close()


@pytest.mark.parametrize("invalid", ["true", 1, None])
def test_hint_flag_is_strict_boolean(tmp_path, invalid):
    with pytest.raises(RUNTIME.WorkerError, match="must be a boolean"):
        runtime(tmp_path, {"coder_post_edit_validation_hint": invalid})
