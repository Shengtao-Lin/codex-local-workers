"""Experimental transport must preserve bounds before any action is dispatched."""

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
from capability_fit import load_worker
from native_reasoning_client import build_client

WORKER = load_worker(KIT)


def client(**kwargs):
    return build_client(
        WORKER,
        "http://localhost:12345/v1",
        "meta/muse-glimmer",
        reasoning="high",
        context_length=24576,
        **kwargs,
    )


def response(output=None, tokens=10):
    return io.StringIO(
        json.dumps(
            {
                "output": output
                if output is not None
                else [
                    {
                        "type": "message",
                        "content": '{"action":"READ_FILE","arguments":{"path":"probe.py"}}',
                    }
                ],
                "stats": {"total_output_tokens": tokens, "reasoning_output_tokens": 4},
            }
        )
    )


def test_native_request_has_real_reasoning_and_bounded_transcript():
    requests = []

    def reply(request, timeout):
        requests.append(request)
        return response()

    with patch("native_reasoning_client.urllib.request.urlopen", side_effect=reply):
        c = client()
        assert c.probe_structured_output() == "native_plain_json_supported"
    body = json.loads(requests[0].data)
    assert requests[0].full_url == "http://localhost:12345/api/v1/chat"
    assert body["reasoning"] == "high"
    assert body["store"] is False
    assert "integrations" not in body and "tools" not in body
    assert json.loads(body["input"])[0]["role"] == "user"
    assert c.last_request_stats["reasoning_requested"] == "high"


@pytest.mark.parametrize(
    "output",
    [
        [],
        [{"type": "tool_call"}],
        [{"type": "invalid_tool_call"}],
        [{"type": "message", "content": ""}],
        [{"type": "message", "content": "a"}, {"type": "message", "content": "b"}],
        [None],
    ],
)
def test_native_rejects_ambiguous_or_tool_output(output):
    with (
        patch(
            "native_reasoning_client.urllib.request.urlopen",
            return_value=response(output),
        ),
        pytest.raises(WORKER.WorkerError),
    ):
        client().complete([{"role": "user", "content": "test"}])


@pytest.mark.parametrize("tokens", [4096, 4097, True, None, -1])
def test_native_rejects_truncation_and_invalid_accounting(tokens):
    with (
        patch(
            "native_reasoning_client.urllib.request.urlopen",
            return_value=response(tokens=tokens),
        ),
        pytest.raises(WORKER.WorkerError),
    ):
        client().complete([{"role": "user", "content": "test"}])


def test_context_rejected_before_http():
    with patch("native_reasoning_client.urllib.request.urlopen") as http:
        with pytest.raises(WORKER.ModelRequestError):
            client().complete([{"role": "user", "content": "x" * 100000}])
        http.assert_not_called()


@pytest.mark.parametrize("kwargs", [{"native_tools": []}, {"structured_output": True}])
def test_unsupported_provider_modes_fail_before_request(kwargs):
    with pytest.raises(ValueError):
        client(**kwargs)


def test_plain_json_probe_is_required_and_fails_closed():
    with (
        patch(
            "native_reasoning_client.urllib.request.urlopen",
            return_value=response([{"type": "message", "content": "```json\n{}\n```"}]),
        ),
        pytest.raises(WORKER.PreflightBlocked),
    ):
        client().probe_structured_output()
