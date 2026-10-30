"""Analysis is untrusted, non-executing, bounded and cannot alter proposal scope."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
import limit_direct_trial as direct

saved = (direct.trial.BASE, direct.trial.SNAPSHOT, direct.trial.ARMS)
spec = importlib.util.spec_from_file_location(
    "limit_reasoning_test", BENCHMARKS / "limit_reasoning_trial.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
direct.trial.BASE, direct.trial.SNAPSHOT, direct.trial.ARMS = saved


@pytest.mark.parametrize("plain", [False, True])
def test_analysis_request_is_bounded_and_original_proposal_state_restored(
    monkeypatch, tmp_path, plain
):
    writes = []
    monkeypatch.setattr(
        module, "write", lambda path, value: writes.append((path, value))
    )

    class Client:
        def complete(self, messages):
            self.calls.append(
                (
                    self.structured_output,
                    self.max_tokens,
                    self.action_schema,
                    list(messages),
                )
            )
            self.last_request_stats = {"response_usage": {"total_tokens": 20}}
            if len(self.calls) == 1:
                return (
                    "Unverified boundary trace"
                    if plain
                    else json.dumps({"analysis": "Unverified boundary trace"})
                )
            return "PROPOSAL_ONLY"

    worker = SimpleNamespace(LMStudioClient=Client)
    module.install(worker, tmp_path, plain)
    client = Client()
    client.structured_output, client.max_tokens = True, 4096
    client.action_schema, client.schema_name, client.calls = (
        {"AUTHORIZED_PROPOSAL": True},
        "proposal",
        [],
    )
    original_schema = client.action_schema
    messages = [
        {"role": "system", "content": "ORIGINAL_POLICY"},
        {"role": "user", "content": "PROTECTED_SOURCE_TESTS_CONTRACT"},
    ]
    before = json.dumps(messages)
    assert client.complete(messages) == "PROPOSAL_ONLY"
    assert client.calls[0][:2] == (not plain, 1024)
    assert client.calls[0][3][1:] == messages[1:]
    assert client.calls[1][0:2] == (True, 4096)
    assert client.calls[1][2] is original_schema
    assert client.calls[1][3][:2] == messages
    assert "unverified" in client.calls[1][3][-1]["content"]
    assert json.dumps(messages) == before
    assert writes[0][1]["semantic_verification"] is False
    assert writes[0][1]["executed_actions"] is False
    assert client.action_schema is original_schema
    assert client.schema_name == "proposal"


def test_analysis_failure_never_requests_proposal_and_restores_state(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        module,
        "write",
        lambda *_: pytest.fail(
            "Invalid analysis cannot be archived as a successful plan"
        ),
    )

    class Client:
        def complete(self, messages):
            self.count += 1
            raise RuntimeError("truncated analysis")

    worker = SimpleNamespace(LMStudioClient=Client)
    module.install(worker, tmp_path, True)
    client = Client()
    (
        client.structured_output,
        client.action_schema,
        client.schema_name,
        client.max_tokens,
    ) = True, {"proposal": True}, "original", 4096
    client.count = 0
    with pytest.raises(RuntimeError, match="truncated"):
        client.complete([{"role": "system", "content": "ORIGINAL"}])
    assert client.count == 1
    assert (
        client.structured_output,
        client.action_schema,
        client.schema_name,
        client.max_tokens,
    ) == (True, {"proposal": True}, "original", 4096)
