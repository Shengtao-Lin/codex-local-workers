"""Non-model safety/attribution checks for the registered Reviewer diagnostics."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import coder_block_preflight as probe
import tool_reviewer_adjudication as audit
import tool_reviewer_transfer as transfer
from native_coder_adapter import tools_for


def test_failed_report_uses_trusted_request_identity_without_inventing_semantic_pass():
    request = {key: key + "-1" for key in ("task_id", "unit_id", "run_id", "review_id")}
    assert audit.review_identity({"decision": "failed"}, request) == request
    with pytest.raises(ValueError, match="lacks identity"):
        audit.review_identity({"decision": "pass_to_primary"}, request)
    with pytest.raises(ValueError, match="differs"):
        audit.review_identity(
            {"decision": "failed", "identity": {**request, "run_id": "other"}}, request
        )


def test_unregistered_reviewer_arm_cannot_prepare_or_invoke_any_worker():
    with patch.object(transfer, "command") as command:
        with pytest.raises(ValueError, match="unregistered arm"):
            transfer.run("not-registered")
        command.assert_not_called()


def test_block_probe_has_no_line_or_shell_action_and_requires_typed_contract_check():
    tools = tools_for({"contract_check_required": True}, probe.ALLOWED)
    names = {tool["function"]["name"] for tool in tools}
    assert names == set(probe.ALLOWED)
    assert names.isdisjoint({"SAFE_REPLACE_LINE", "SHELL", "GIT"})
    validate = next(
        tool["function"]["parameters"]
        for tool in tools
        if tool["function"]["name"] == "VALIDATE"
    )
    assert validate["required"] == ["contract_check"]
    assert (
        "required_order_confirmed"
        in validate["properties"]["contract_check"]["required"]
    )
    assert all(action in names for action, _ in probe.PROBES)


def test_native_probe_grades_canonical_fields_not_parser_warning_metadata():
    arguments = {"path": "src/example.py", "start_line": 1, "end_line": 2}
    returned = {"action": "READ_FILE", "arguments": arguments, "_warnings": []}
    stats = {
        "native_tool_call": "READ_FILE",
        "response_parts": {"tool_calls": {"count": 1}},
    }
    assert probe.exact_native_action(returned, "READ_FILE", arguments, stats)
    assert not probe.exact_native_action(
        {**returned, "_warnings": ["extra action"]}, "READ_FILE", arguments, stats
    )
    assert not probe.exact_native_action(
        returned, "READ_FILE", {"path": "other.py"}, stats
    )
    assert not probe.exact_native_action(
        returned, "READ_FILE", arguments, {**stats, "native_tool_call": "SAFE_REPLACE"}
    )
