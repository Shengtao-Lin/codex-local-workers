"""Repair evidence must survive protocol errors without replaying stale proposals."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import test_single_function_context as single

runtime = single.runtime


def history():
    return [
        {"role": "system", "content": "old system"},
        {"role": "user", "content": "old packet"},
        {"role": "assistant", "content": "STALE_EDIT_PROPOSAL"},
        {"role": "user", "content": 'OBSERVATION\n{"status":"ok"}'},
        {"role": "assistant", "content": "OLD_VALIDATION_ACTION"},
        {"role": "user", "content": 'REPAIR_REQUIRED\n{"rule":"OLD_EVIDENCE"}'},
        {"role": "assistant", "content": "FAILED_EDIT_PROPOSAL"},
        {"role": "user", "content": 'OBSERVATION\n{"error":"target missing"}'},
    ]


def test_pending_repair_survives_later_action_error(runtime):
    focus = {"check_id": "ruff-check", "rule": "E501", "path": single.SPEC["path"]}
    payload = {"repair_focus": focus, "source_excerpts": []}
    with (
        patch.object(runtime, "_required_repair_focus", return_value=focus),
        patch.object(runtime, "_compact_repair_payload", return_value=payload),
    ):
        result = runtime._trim_messages(history())
    assert result[-1]["content"] == "REPAIR_REQUIRED\n" + json.dumps(payload)
    assert "target missing" in result[-2]["content"]
    assert all(item["role"] != "assistant" for item in result)
    assert "OLD_EVIDENCE" not in json.dumps(result)
    assert (
        json.loads(result[1]["content"])["packet"]["required_behavior"]
        == runtime.packet["required_behavior"]
    )
    assert runtime.last_contract_check is None


def test_successful_edit_drops_obsolete_repair_history(runtime):
    runtime.safe_replace(single.edit(runtime))
    result = runtime._trim_messages(
        history() + [{"role": "user", "content": 'OBSERVATION\n{"edit_revision":1}'}]
    )
    assert len(result) == 3
    assert "REPAIR_REQUIRED" not in json.dumps(result)
    assert "PROPOSAL" not in json.dumps(result)
    assert "return 2" in json.loads(result[1]["content"])["target"]["source"]


def test_repair_prefetch_does_not_replay_previous_success(runtime):
    with (
        patch.object(runtime, "_required_repair_focus", return_value={"rule": "E501"}),
        patch.object(runtime, "_compact_repair_payload", return_value={"rule": "E501"}),
    ):
        result = runtime._trim_messages(history()[:6])
    assert len(result) == 3
    assert result[-1]["content"] == 'REPAIR_REQUIRED\n{"rule": "E501"}'


def test_no_pending_validation_does_not_invent_repair(runtime):
    runtime.validation = SimpleNamespace(status="passed")
    result = runtime._trim_messages(history()[:6])
    assert len(result) == 2
    assert "REPAIR_REQUIRED" not in json.dumps(result)
    assert runtime.last_contract_check is None


def test_transport_nudge_is_not_discarded(runtime):
    nudge = {"role": "user", "content": "NATIVE_TEXT_TRUNCATION_REPAIR\nno action executed"}
    result = runtime._trim_messages(history() + [nudge])
    assert result[-1] == nudge
    assert "PROPOSAL" not in json.dumps(result)
