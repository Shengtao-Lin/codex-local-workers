import io
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_fixture_support as F
import reasoning_wire_candidate as W
import test_reviewer_contract_first as C


def test_installed_client_forwards_only_explicit_effort_and_preserves_default(tmp_path):
    seed = (
        F.KIT
        / "benchmarks/work/harness-convergence/supervised-release-20261019-4/cells/json-1/isolated/.local-agents"
    )
    target = tmp_path / ".local-agents"
    shutil.copytree(seed, target)
    W.patch_client(target / "worker-runtime.py", allowed_root=tmp_path)
    module = F.load(target / "worker-runtime.py", "reasoning_wire_client_control")
    observed = []
    response = {
        "choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}]
    }

    def fake_http(request, **_kwargs):
        observed.append(json.loads(request.data))
        return io.BytesIO(json.dumps(response).encode())

    client = module.LMStudioClient(
        "http://localhost:12345/v1", "same-model", max_tokens=4096
    )
    with patch.object(module.urllib.request, "urlopen", side_effect=fake_http):
        client.complete([{"role": "user", "content": "control"}])
        client.reasoning_effort = "low"
        client.complete([{"role": "user", "content": "control"}])
    assert "reasoning_effort" not in observed[0]
    assert observed[1].pop("reasoning_effort") == "low"
    assert observed[0] == observed[1]
    client.reasoning_effort = "unsupported"
    with pytest.raises(module.WorkerError, match="Unsupported explicit"):
        client.complete([{"role": "user", "content": "control"}])


def test_root_production_client_cannot_be_patched():
    with pytest.raises(ValueError, match="isolated"):
        W.patch_client(F.KIT / ".local-agents/worker-runtime.py", allowed_root=F.KIT)


def test_phase_effort_is_forwarded_and_recovery_stays_within_original_budget(tmp_path):
    runtime, _, client = C.make(
        tmp_path, ["output_token_limit", C.predict(), C.report()]
    )
    runtime.forward_effort = True
    client.reasoning_effort = None
    original = client.complete
    levels = []

    def complete(messages):
        levels.append(client.reasoning_effort)
        return original(messages)

    client.complete = complete
    one, two = C.facts(C.profile())
    with one, two:
        report = runtime.run()
    assert report["decision"] == "pass_to_primary"
    assert levels == ["medium", "low", "low"]
    assert client.reasoning_effort is None
    assert report["reviewer_model_calls"] == 3
    assert report["shared_error_budget_used"] == 1


def test_flag_fails_closed_for_unpatched_client(tmp_path):
    runtime, module, client = C.make(tmp_path, [C.predict(), C.report()])
    runtime.forward_effort = True
    one, two = C.facts(C.profile())
    with one, two, pytest.raises(module.ReviewError, match="cannot forward"):
        runtime.run()
    assert client.calls == 0
