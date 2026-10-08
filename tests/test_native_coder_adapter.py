"""Candidate tool schemas cannot broaden dispatch or fabricate contract facts."""

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
SPEC = importlib.util.spec_from_file_location(
    "native_coder_test", BENCHMARKS / "native_coder_adapter.py"
)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


def test_tools_preserve_exact_allowed_actions_and_single_line_shape():
    tools = ADAPTER.tools_for({}, ["SAFE_REPLACE_LINE", "FINISH_BLOCKED"])
    assert [t["function"]["name"] for t in tools] == [
        "SAFE_REPLACE_LINE",
        "FINISH_BLOCKED",
    ]
    pattern = tools[0]["function"]["parameters"]["properties"]["replacement"]["pattern"]
    assert re.fullmatch(pattern, "x = 1")
    assert not re.fullmatch(pattern, "x = 1\ny = 2")
    assert not re.fullmatch(pattern, "x = 1\r")
    for illegal in ([], ["SHELL"], ["READ_FILE", "READ_FILE"]):
        with pytest.raises(ValueError):
            ADAPTER.tools_for({}, illegal)


def test_contract_check_shape_matches_runtime_without_setting_answers():
    schema = ADAPTER.tools_for({"contract_check_required": True}, ["VALIDATE"])[0][
        "function"
    ]["parameters"]
    assert schema["required"] == ["contract_check"]
    check = schema["properties"]["contract_check"]["properties"]
    assert check["unrelated_changes"]["type"] == "array"
    assert check["required_order_confirmed"]["type"] == ["boolean", "null"]
    assert "default" not in json.dumps(check)
    assert (
        ADAPTER.tools_for({}, ["VALIDATE"])[0]["function"]["parameters"]["required"]
        == []
    )


@pytest.mark.parametrize(
    "native_name,action",
    [
        ("READ_FILE", "READ_FILE"),
        (None, "READ_FILE"),
        ("SAFE_CREATE", "SAFE_CREATE"),
        ("READ_FILE", "SAFE_CREATE"),
    ],
)
def test_adapter_follows_live_gate_and_leaves_original_messages_untouched(
    native_name, action
):
    class Client:
        def complete(self, messages):
            self.received = messages
            self.last_request_stats = {"native_tool_call": native_name}
            return json.dumps({"action": action, "arguments": {"path": "src/a.py"}})

    worker = SimpleNamespace(LMStudioClient=Client, WorkerError=ValueError)
    ADAPTER.install(worker, {})
    client = Client()
    client.action_schema = {"properties": {"action": {"enum": ["READ_FILE"]}}}
    messages = [
        {
            "role": "system",
            "content": "Old JSON header\nAvailable actions and their arguments:UNCHANGED_CONTRACT",
        },
        {"role": "user", "content": "ORIGINAL_PACKET"},
    ]
    before = json.dumps(messages)
    if native_name == action == "READ_FILE":
        assert json.loads(client.complete(messages))["action"] == "READ_FILE"
    else:
        with pytest.raises(ValueError, match="currently allowed"):
            client.complete(messages)
    assert json.dumps(messages) == before
    assert client.received[0]["content"].endswith("UNCHANGED_CONTRACT")
    assert client.received[1] == messages[1]
    assert [t["function"]["name"] for t in client.native_tools] == ["READ_FILE"]
    assert client.native_tool_choice == "required"
