"""Transport-only switch must not relax the parser or editing boundary."""

import io
import json
import sys
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r2_decoding as trial
import test_harness_r2_output as prior

root = prior.root


def complete(module, messages, arm, raw, requests):
    def respond(request, **kwargs):
        requests.append(json.loads(request.data))
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [{"message": {"content": raw}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 10},
                }
            ).encode()
        )

    with (
        trial.decoding(module, arm),
        patch.object(urllib.request, "urlopen", side_effect=respond),
    ):
        client = module.LMStudioClient(
            "http://127.0.0.1:12345",
            "qwen/qwen3-coder-30b",
            structured_output=True,
            action_schema=trial.output.WHOLE_SCHEMA,
            typed_action_arguments=False,
        )
        return client.complete(messages)


def test_real_client_wire_diff_only_response_format(root):
    module = trial.old.load_runtime()
    bound = prior.binding(root)
    messages = [
        {"role": "system", "content": trial.output.WHOLE_PROMPT},
        {"role": "user", "content": json.dumps({"target": bound})},
    ]
    raw = json.dumps({"replacement": prior.repaired(bound["source"])})
    requests = []
    original = module.LMStudioClient
    for arm in ("schema", "plain"):
        with trial.output.interface(module, "whole", bound):
            received = complete(module, messages, arm, raw, requests)
            assert received == raw
            action = module.SINGLE_FUNCTION.patch_action(received)
            assert action["arguments"]["replace"] == prior.repaired(bound["source"])
        assert module.LMStudioClient is original
    schema, plain = requests
    assert "response_format" in schema
    assert "response_format" not in plain
    for arm, request in zip(("schema", "plain"), requests, strict=True):
        assert trial.wire_matches(request, {"arm": arm, "messages": messages}, plain)
    schema.pop("response_format")
    assert schema == plain
    changed = {**plain, "max_tokens": 1}
    assert not trial.wire_matches(
        changed, {"arm": "plain", "messages": messages}, plain
    )
    assert not trial.wire_matches(
        {**plain, "response_format": None},
        {"arm": "plain", "messages": messages},
        plain,
    )


@pytest.mark.parametrize("arm", ["schema", "plain"])
@pytest.mark.parametrize(
    "raw",
    [
        "not JSON",
        '```json\n{"replacement":"x"}\n```',
        '{"replacement":"x","extra":true}',
        '{"replacement":"x","blocked_reason":"x"}',
        '{"replacement":"first","replacement":"second"}',
    ],
)
def test_both_transports_retain_identical_strict_rejection(root, arm, raw):
    module = trial.old.load_runtime()
    bound = prior.binding(root)
    requests = []
    before = (root / trial.B.SOURCE).read_bytes()
    with trial.output.interface(module, "whole", bound):
        received = complete(module, [], arm, raw, requests)
        with pytest.raises(ValueError):
            module.SINGLE_FUNCTION.patch_action(received)
    assert len(requests) == 1
    assert (root / trial.B.SOURCE).read_bytes() == before


@pytest.mark.parametrize("arm", ["schema", "plain"])
def test_transport_exception_restores_every_patch(root, arm):
    module = trial.old.load_runtime()
    original = module.LMStudioClient
    parser = module.SINGLE_FUNCTION.patch_action
    schema = module.SINGLE_FUNCTION.PATCH_SCHEMA
    with (
        pytest.raises(RuntimeError),
        trial.output.interface(module, "whole", prior.binding(root)),
        trial.decoding(module, arm),
    ):
        raise RuntimeError("transport error")
    assert module.LMStudioClient is original
    assert module.SINGLE_FUNCTION.patch_action is parser
    assert module.SINGLE_FUNCTION.PATCH_SCHEMA is schema


def test_unknown_arm_fails_closed():
    with pytest.raises(ValueError), trial.decoding(trial.old.load_runtime(), "other"):
        pytest.fail("must not enter")
