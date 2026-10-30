import io
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_required_probe as H


def test_identical_four_inputs_no_failure_removed():
    old = H.B.read(H.OLD / "registration.json")
    new = H.B.read(H.BATCH / "registration.json")
    assert old["cells"] == new["cells"]
    assert H.B.read(H.OLD / "decision.json")["correct"] == 3
    for row in new["cells"]:
        assert (
            H.B.sha(H.BATCH / "cells" / row["id"] / "messages.json")
            == row["messages_sha256"]
        )
    assert new["usage_ceiling"] == 45 and new["registered"] == 4


@pytest.mark.parametrize("finish", ["tool_calls", "length"])
def test_actual_wire_only_tool_choice_changes_and_length_still_rejected(finish):
    row = H.B.read(H.OLD / "registration.json")["cells"][0]
    root = Path(row["origin_root"])
    worker = H.P.H.R.load(
        root / ".local-agents/worker-runtime.py", "required_probe_test_" + finish
    )
    config = H.B.read(root / ".agent/experiment-config.json")
    body = {
        "choices": [
            {
                "finish_reason": finish,
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_control",
                            "type": "function",
                            "function": {
                                "name": "REPORT",
                                "arguments": json.dumps(
                                    {"verdict": "uncertain", "explanation": "Control"}
                                ),
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": 4096 if finish == "length" else 20,
        },
    }
    sent = []

    def urlopen(request, timeout):
        assert timeout == config["model_request_timeout_seconds"]
        sent.append(json.loads(request.data))
        return io.BytesIO(json.dumps(body).encode())

    clients = [worker.LMStudioClient, H.required_client(worker.LMStudioClient)]
    for cls in clients:
        client = cls(
            config["lmstudio_base_url"],
            config["reviewer_model"],
            config["model_request_timeout_seconds"],
            max_tokens=config["reviewer_max_tokens"],
            temperature=config["reviewer_temperature"],
            top_p=config["reviewer_top_p"],
            top_k=config["reviewer_top_k"],
            min_p=config["reviewer_min_p"],
            repeat_penalty=config["reviewer_repeat_penalty"],
            structured_output=False,
            native_tools=H.P.TOOLS,
            context_length=config["reviewer_context_length"],
            context_safety_margin=config["model_context_safety_margin"],
        )
        with mock.patch.object(worker.urllib.request, "urlopen", urlopen):
            if finish == "length":
                with pytest.raises(
                    worker.ModelRequestError, match="output-token limit"
                ):
                    client.complete(H.B.read(H.BATCH / "cells/probe-01/messages.json"))
            else:
                assert (
                    worker.parse_action(
                        client.complete(
                            H.B.read(H.BATCH / "cells/probe-01/messages.json")
                        )
                    )["arguments"]["verdict"]
                    == "uncertain"
                )
    assert sent[0].pop("tool_choice") == "auto"
    assert sent[1].pop("tool_choice") == "required"
    assert sent[0] == sent[1]
    assert sent[1]["max_tokens"] == 4096
    assert len(sent) == 2  # No output-limit retry.
