import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from coder_native_history_adapter import adapt_history


def test_only_correlated_real_native_calls_are_translated_without_mutation():
    raw = json.dumps({"action": "READ_FILE", "arguments": {"path": "src/a.py"}})
    native = {
        "id": "provider-1",
        "type": "function",
        "function": {"name": "READ_FILE", "arguments": '{"path":"src/a.py"}'},
    }
    history = [
        {"role": "assistant", "content": raw},
        {
            "role": "user",
            "content": 'OBSERVATION\n{"status":"error","error":"scope denied"}',
        },
        {"role": "assistant", "content": raw},
        {
            "role": "user",
            "content": 'OBSERVATION\n{"status":"ok","sha256":"actual-old-hash"}',
        },
    ]
    before = json.dumps([history, native])
    result = adapt_history(history, {raw: native})
    assert [item["role"] for item in result] == [
        "assistant",
        "tool",
        "assistant",
        "tool",
    ]
    assert result[0]["tool_calls"][0]["id"] == result[1]["tool_call_id"]
    assert result[1]["content"] == history[1]["content"]
    assert result[0]["tool_calls"][0]["id"] != result[2]["tool_calls"][0]["id"]
    assert result[3]["content"] == history[3]["content"]
    assert json.dumps([history, native]) == before


def test_unknown_unpaired_repair_and_malformed_observations_remain_unchanged():
    raw = '{"action":"READ_FILE","arguments":{}}'
    call = {
        "id": "1",
        "type": "function",
        "function": {"name": "READ_FILE", "arguments": "{}"},
    }
    for history, calls in (
        ([{"role": "assistant", "content": raw}], {raw: call}),
        (
            [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": "REPAIR_REQUIRED\n{}"},
            ],
            {raw: call},
        ),
        (
            [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": "OBSERVATION\nnot json"},
            ],
            {raw: call},
        ),
        (
            [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": "OBSERVATION\n{}"},
            ],
            {},
        ),
    ):
        assert adapt_history(history, calls) == history


def test_repair_history_only_correlates_real_validate_and_retains_exact_payload():
    raw = '{"action":"VALIDATE","arguments":{"phase":"check"}}'
    call = {
        "id": "1",
        "type": "function",
        "function": {"name": "VALIDATE", "arguments": '{"phase":"check"}'},
    }
    messages = [
        {"role": "assistant", "content": raw},
        {
            "role": "user",
            "content": 'REPAIR_REQUIRED\n{"required_next_action":"SAFE_REPLACE","source_excerpts":[]}',
        },
    ]
    assert adapt_history(messages, {raw: call}) == messages
    actual = adapt_history(messages, {raw: call}, repair_history=True)
    assert actual[1]["role"] == "tool"
    assert actual[1]["content"] == messages[1]["content"]
    wrong = {**call, "function": {"name": "READ_FILE", "arguments": "{}"}}
    assert adapt_history(messages, {raw: wrong}, repair_history=True) == messages
    assert adapt_history(messages[1:], {raw: call}, repair_history=True) == messages[1:]
