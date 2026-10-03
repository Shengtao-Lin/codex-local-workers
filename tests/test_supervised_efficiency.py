import importlib.util
import json
import sys
from pathlib import Path

import pytest

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
SPEC = importlib.util.spec_from_file_location(
    "supervised_efficiency_test", BENCHMARKS / "supervised_efficiency.py"
)
assert SPEC and SPEC.loader
EFFICIENCY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EFFICIENCY)


class Client:
    model = "test-model"

    def __init__(self):
        self.last_request_stats = {}

    def complete(self, messages):
        self.observed_messages = messages
        self.last_request_stats = {
            "response_usage": {"total_tokens": 23},
            "reported_context_utilization": 0.1,
        }
        return '{"decision":"CONTINUE"}'


def test_observer_preserves_input_output_and_delegated_identity(tmp_path):
    client = Client()
    observer = EFFICIENCY.RequestObserver(client, tmp_path / "requests.jsonl")
    messages = [{"role": "user", "content": "private source"}]
    assert observer.complete(messages) == '{"decision":"CONTINUE"}'
    assert client.observed_messages is messages
    assert observer.model == "test-model"
    record = json.loads(observer.path.read_text())
    assert record["request_stats"]["response_usage"]["total_tokens"] == 23
    assert record["status"] == "completed"
    assert "private source" not in observer.path.read_text()
    client.last_request_stats["response_usage"]["total_tokens"] = 99
    assert observer.requests[0]["request_stats"]["response_usage"]["total_tokens"] == 23


def test_observer_does_not_overwrite_or_retry(tmp_path):
    path = tmp_path / "requests.jsonl"
    path.write_text("original", encoding="utf-8")
    with pytest.raises(FileExistsError):
        EFFICIENCY.RequestObserver(Client(), path)
    assert path.read_text() == "original"


def test_request_failure_propagates_and_is_recorded(tmp_path):
    class FailedClient(Client):
        def complete(self, messages):
            raise TimeoutError("slow model")

    observer = EFFICIENCY.RequestObserver(FailedClient(), tmp_path / "requests.jsonl")
    with pytest.raises(TimeoutError):
        observer.complete([])
    assert len(observer.requests) == 1
    assert observer.requests[0]["status"] == "failed"
    assert observer.requests[0]["error_type"] == "TimeoutError"


def test_missing_usage_is_unknown_not_zero():
    result = EFFICIENCY.usage([{"request_stats": {}}])
    assert result["requests"] == 1
    assert result["reported_total_tokens"] is None
    assert result["requests_missing_token_usage"] == 1
    assert result["max_reported_context_utilization"] is None


def test_usage_sums_actual_tokens_not_context_estimates():
    result = EFFICIENCY.usage(
        [
            {
                "request_stats": {
                    "response_usage": {"total_tokens": 7},
                    "estimated_input_tokens": 9000,
                    "reported_context_utilization": 0.2,
                }
            },
            {
                "request_stats": {
                    "response_usage": {"total_tokens": 11},
                    "reported_context_utilization": 0.3,
                }
            },
        ]
    )
    assert result["reported_total_tokens"] == 18
    assert result["max_reported_context_utilization"] == 0.3


def test_nested_reviewer_and_direct_worker_events_are_both_counted(tmp_path):
    path = tmp_path / "events.jsonl"
    events = [
        {"event": "model_request", "facts": {"response_usage": {"total_tokens": 7}}},
        {
            "event": "model_turn",
            "facts": {"model_request": {"response_usage": {"total_tokens": 11}}},
        },
        {"event": "diagnostic_action", "facts": {}},
    ]
    path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
    assert (
        EFFICIENCY.usage(EFFICIENCY.event_requests(path))["reported_total_tokens"] == 18
    )
