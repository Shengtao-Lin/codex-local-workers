"""Native BLOCK transports never expand the underlying runtime action allowlist."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import coder_native_block_adapter as adapter


def test_block_tools_preserve_terminal_allowlist_without_exposing_line():
    tools = adapter.block_tools({}, ["SAFE_REPLACE", "SAFE_REPLACE_LINE"])
    assert [tool["function"]["name"] for tool in tools] == ["SAFE_REPLACE"]
    terminal = adapter.block_tools({}, ["FINISH_SUCCESS"])
    assert [tool["function"]["name"] for tool in terminal] == ["FINISH_SUCCESS"]
    with pytest.raises(ValueError):
        adapter.block_tools({}, ["SAFE_REPLACE_LINE"])


def test_invented_unadvertised_line_call_is_rejected_before_runtime_dispatch(
    monkeypatch,
):
    class Client:
        action_schema = {
            "properties": {"action": {"enum": ["SAFE_REPLACE", "SAFE_REPLACE_LINE"]}}
        }

        def complete(self, messages):
            self.last_request_stats = {"native_tool_call": "SAFE_REPLACE_LINE"}
            return json.dumps({"action": "SAFE_REPLACE_LINE", "arguments": {}})

    monkeypatch.setattr(adapter.native, "tools_for", adapter.original_tools)
    worker = SimpleNamespace(LMStudioClient=Client, WorkerError=RuntimeError)
    adapter.install(worker, {})
    client = Client()
    messages = [
        {"role": "system", "content": "Available actions and their arguments: original"}
    ]
    before = json.dumps(messages)
    with pytest.raises(RuntimeError, match="currently advertised"):
        client.complete(messages)
    assert json.dumps(messages) == before
    assert [tool["function"]["name"] for tool in client.native_tools] == [
        "SAFE_REPLACE"
    ]
