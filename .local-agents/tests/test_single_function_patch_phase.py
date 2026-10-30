"""Patch phase uses the real edit/validation loop, not a second trusted editor."""

import copy
import json
from unittest.mock import patch

import pytest
import test_single_function_context as single
import test_single_function_terminal as terminal

R = single.R
runtime = single.runtime


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        {"find": "x"},
        {"blocked_reason": ""},
        {"blocked_reason": 1},
        {"action": "FINISH_SUCCESS", "arguments": {}},
    ],
)
def test_invalid_proposal_cannot_be_action(value):
    with pytest.raises(ValueError):
        R.SINGLE_FUNCTION.patch_action(json.dumps(value))


@pytest.mark.parametrize(
    "variant", ["stale", "scope", "signature", "neighbor", "noop", "missing", "ambiguous"]
)
def test_patch_parser_does_not_grant_edit_authority(runtime, variant):
    args = single.edit(runtime)
    if variant == "stale":
        args["expected_sha256"] = "0" * 64
    if variant == "scope":
        args["path"] = "tests/test_example.py"
    if variant == "signature":
        args.update(find="def target():", replace="def target(x):")
    if variant == "neighbor":
        args.update(find="return 9", replace="return 8")
    if variant == "noop":
        args["replace"] = args["find"]
    if variant == "missing":
        args["find"] = "absent source"
    if variant == "ambiguous":
        args.update(find="return", replace="yield")
    action = R.SINGLE_FUNCTION.patch_action(json.dumps(args))
    with pytest.raises((R.WorkerError, R.SafeEditError)):
        runtime.execute(action)
    assert (runtime.repo_root / single.SPEC["path"]).read_text() == single.SOURCE
    assert not runtime._validated_terminal_state()


def test_block_is_not_success(runtime):
    _, report = runtime.execute(R.SINGLE_FUNCTION.patch_action('{"blocked_reason":"need Primary"}'))
    assert report["status"] == "blocked"
    assert (runtime.repo_root / single.SPEC["path"]).read_text() == single.SOURCE


@pytest.mark.parametrize("case", ["success", "blocked", "transport", "malformed"])
def test_patch_phase_real_loop_requires_fresh_validation(tmp_path, case):
    instance = terminal.runtime_at(tmp_path)
    instance.single_function_patch_repair = True
    instance.client.structured_output = True
    instance.client.action_schema = copy.deepcopy(R.CODER_ACTION_SCHEMA)
    instance.client.schema_name = "original"
    instance.client.typed_action_arguments = True
    instance.config["validation_profiles"]["python-focused"]["commands"][0]["id"] = "ruff-check"
    original_schema = copy.deepcopy(instance.client.action_schema)
    seen = []

    def complete(messages):
        seen.append(messages)
        turn = len(seen)
        if turn == 1:
            return json.dumps({"action": "SAFE_REPLACE", "arguments": single.edit(instance)})
        if turn == 3:
            assert instance.validation.status == "failed"
            assert instance.client.action_schema == R.SINGLE_FUNCTION.PATCH_SCHEMA
            assert instance.client.typed_action_arguments is False
            assert messages[0]["content"] == R.SINGLE_FUNCTION.PATCH_PROMPT
            if case == "blocked":
                return '{"blocked_reason":"cannot repair within this scope"}'
            if case == "transport":
                raise R.WorkerError("transport test interruption")
            if case == "malformed":
                return '{"action":"FINISH_SUCCESS","arguments":{"summary":["fake"]}}'
            return json.dumps(single.edit(instance, find="return 2", replace="return 3"))
        if case == "malformed" and turn == 4:
            assert instance.client.action_schema == R.SINGLE_FUNCTION.PATCH_SCHEMA
            assert instance.edit_revision == 1
            return '{"blocked_reason":"invalid proposal retained without execution"}'
        if turn in {4, 5, 6}:
            assert instance.client.typed_action_arguments is True
            assert instance.noop_validation_pending
            assert instance.last_contract_check is None
            assert (
                "SAFE_REPLACE" not in instance.client.action_schema["properties"]["action"]["enum"]
            )
            if turn == 4:
                return json.dumps(
                    {"action": "READ_FILE", "arguments": {"path": single.SPEC["path"]}}
                )
            if turn == 5:
                return json.dumps({"action": "VALIDATE", "arguments": {}})
        if turn == 7:
            return json.dumps({"action": "FINISH_SUCCESS", "arguments": {"summary": ["checked"]}})
        return json.dumps(
            {
                "action": "VALIDATE",
                "arguments": {"contract_check": instance.contract_check_template()},
            }
        )

    def command(argv):
        failed = "return 2" in (tmp_path / single.SPEC["path"]).read_text()
        result = terminal.fake_command(argv, fail=failed and "--version" in argv)
        if result["status"] == "failed":
            result["output"] = "src/example.py:2:1: E501 Line too long (120 > 100)"
        return result

    with (
        patch.object(instance.client, "complete", side_effect=complete),
        patch.object(instance, "_run_command", side_effect=command),
    ):
        report = instance.run()
    assert instance.client.action_schema == original_schema
    assert instance.client.schema_name == "original"
    assert instance.client.typed_action_arguments is True
    if case != "success":
        assert report["status"] == ("failed" if case == "transport" else "blocked")
        assert instance.edit_revision == 1
        assert len(seen) == (4 if case == "malformed" else 3)
        assert not instance._validated_terminal_state()
        return
    assert report["status"] == "ready_for_review", report
    assert len(seen) == 7
    assert instance.validation_count == 2  # Missing confirmation did not run validation.
    assert instance.client.action_schema == original_schema
    assert instance.client.schema_name == "original"
    assert (tmp_path / single.SPEC["path"]).read_text() == single.SOURCE.replace(
        "return 1", "return 3"
    )
    events = (tmp_path / report["evidence_refs"]["run_archive"] / "events.jsonl").read_text()
    assert "single_function_patch_phase" in events
    assert "single_function_patch_confirmation_required" in events


@pytest.mark.parametrize(
    "case", ["ok", "not-single", "no-contract", "native", "typed", "unstructured", "invalid-flag"]
)
def test_patch_mode_configuration_is_explicit_and_narrow(tmp_path, case):
    base = terminal.runtime_at(tmp_path)
    config = copy.deepcopy(base.config)
    packet = copy.deepcopy(base.packet)
    client = base.client
    base.close()
    config["coder_single_function_patch_repair"] = True
    client.structured_output = True
    if case == "not-single":
        config.pop("coder_single_function")
    if case == "no-contract":
        packet["contract_check_required"] = False
    if case == "native":
        client.native_tools = []
    if case == "typed":
        client.typed_action_arguments = True
    if case == "unstructured":
        client.structured_output = False
    if case == "invalid-flag":
        config["coder_single_function_patch_repair"] = "true"
    if case in {"ok", "typed"}:
        instance = R.WorkerRuntime(tmp_path, packet, config, client)
        assert instance.single_function_patch_repair
        assert not instance.pending_failed_validation
        instance.close()
    else:
        with pytest.raises(R.WorkerError):
            R.WorkerRuntime(tmp_path, packet, config, client)
