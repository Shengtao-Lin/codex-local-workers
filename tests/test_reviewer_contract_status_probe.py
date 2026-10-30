"""Matching context, hidden judge and real native-client transport controls."""

import copy
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_contract_status_probe as P


def action():
    return {
        "action": "PREDICT_STATUS",
        "arguments": {
            "predictions": [
                {
                    "case_index": i,
                    "status": "succeeded",
                    "reason": "Required by recognized-result rule.",
                }
                for i in range(6)
            ]
        },
    }


def test_eight_matched_messages_and_judge_not_supplied_before_live():
    reg = P.B.read(P.BATCH / "registration.json")
    assert len(reg["cells"]) == 8
    assert [r["arm"] for r in reg["cells"]] == P.ORDER
    groups = {"blind": [], "source": []}
    for row in reg["cells"]:
        cell = P.BATCH / "cells" / row["id"]
        assert not (cell / "result.json").exists()
        assert P.B.sha(cell / "messages.json") == row["messages_sha256"]
        messages = P.B.read(cell / "messages.json")
        assert messages[0] == {"role": "system", "content": P.SYSTEM}
        user = json.loads(messages[1]["content"])
        assert "outcome" not in user and "expected" not in user and "judge" not in user
        assert len(user["event_sequences"]) == 6
        for i, case in enumerate(user["event_sequences"]):
            assert case["case_index"] == i
            parts = case["input"]["parts"]
            assert len(parts) == 2 and parts[1]["type"] == "tool_result"
            assert parts[0]["call_id"] == parts[1]["call_id"]
        assert user["event_sequences"][0]["input"]["parts"][1]["result"] is None
        groups[row["arm"]].append(user)
    assert all(v == groups["blind"][0] for v in groups["blind"])
    assert all(v == groups["source"][0] for v in groups["source"])
    source = copy.deepcopy(groups["source"][0])
    code = source.pop("unreviewed_implementation")
    assert "if part.result is not None:" in code
    assert source == groups["blind"][0]
    assert P.B.read(P.BATCH / "judge.json")["statuses"] == ["succeeded"] * 6
    assert reg["budget"] == {
        "requests_per_cell": 1,
        "max_tokens": 4096,
        "timeout_seconds": 180,
        "repair": 0,
    }


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "bool_index", "unknown", "blank", "tool"]
)
def test_invalid_shapes_rejected_without_semantic_inference(change):
    value = action()
    rows = value["arguments"]["predictions"]
    if change == "missing":
        rows.pop()
    if change == "duplicate":
        rows[1]["case_index"] = 0
    if change == "bool_index":
        rows[0]["case_index"] = False
    if change == "unknown":
        rows[0]["status"] = "accepted"
    if change == "blank":
        rows[0]["reason"] = " "
    if change == "tool":
        value["action"] = "REPORT"
    with pytest.raises(ValueError):
        P.validate(json.dumps(value))


def test_valid_but_semantically_wrong_status_is_retained_not_auto_corrected():
    value = action()
    value["arguments"]["predictions"][0]["status"] = "requested"
    assert P.validate(json.dumps(value)) == value


def test_real_native_http_roundtrip_uses_registered_tool_and_original_limits():
    reg = P.B.read(P.BATCH / "registration.json")
    root = Path(reg["origin_root"])
    worker = P.R.load(root / ".local-agents/worker-runtime.py", "status_http_control")
    client = worker.LMStudioClient(
        "http://127.0.0.1:1/v1",
        "meta/muse-glimmer",
        timeout=180,
        max_tokens=4096,
        temperature=0,
        native_tools=P.TOOLS,
        context_length=24576,
    )
    seen = []

    def urlopen(request, **kwargs):
        seen.append((json.loads(request.data), kwargs["timeout"]))
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "call-status",
                                        "type": "function",
                                        "function": {
                                            "name": "PREDICT_STATUS",
                                            "arguments": json.dumps(
                                                action()["arguments"]
                                            ),
                                        },
                                    }
                                ]
                            },
                        }
                    ]
                }
            ).encode()
        )

    messages = P.B.read(P.BATCH / "cells/cell-01/messages.json")
    with patch.object(worker.urllib.request, "urlopen", side_effect=urlopen):
        result = P.validate(client.complete(messages))
    assert result == action() and len(seen) == 1
    body, timeout = seen[0]
    assert body["messages"] == messages and body["tools"] == P.TOOLS
    assert body["max_tokens"] == 4096 and body["temperature"] == 0 and timeout == 180
    assert body["tool_choice"] == "auto" and body["parallel_tool_calls"] is False
