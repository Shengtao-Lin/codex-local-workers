from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "coordinator_runtime_test", ROOT / "coordinator-runtime.py"
)
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


class Client:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.messages = []

    def complete(self, messages):
        self.messages.append(list(messages))
        return next(self.outputs)


def plan():
    return json.loads((ROOT / "example-feature-plan.json").read_text())


def test_decision_has_fresh_context_and_no_dispatch_authority():
    client = Client(['{"decision":"CONTINUE","unit_id":"worker-success-finalization"}'])
    result = RUNTIME.probe(plan(), {}, "decision", client)
    assert result["status"] == "protocol_valid"
    assert result["semantic_qualification"] == "not_evaluated"
    assert result["dispatch_allowed"] is False
    assert result["feature_accepted"] is False
    assert len(client.messages[0]) == 2


def test_optional_reasoning_profile_preserves_authority_and_rejects_invalid_value():
    client = Client(['{"decision":"CONTINUE","unit_id":"worker-success-finalization"}'])
    result = RUNTIME.probe(plan(), {}, "decision", client, reasoning_strength="low")
    assert "Reasoning strength: low." in client.messages[0][0]["content"]
    assert result["dispatch_allowed"] is False
    assert result["feature_accepted"] is False
    with pytest.raises(ValueError, match="coordinator_reasoning_strength"):
        RUNTIME.probe(plan(), {}, "decision", Client([]), reasoning_strength="turbo")


def test_probe_archives_each_actual_request_stats_without_aliasing():
    class ObservedClient(Client):
        last_request_stats = None

        def complete(self, messages):
            raw = super().complete(messages)
            self.last_request_stats = {"response_usage": {"total_tokens": len(self.messages)}}
            return raw

    client = ObservedClient(
        ["not JSON", '{"decision":"CONTINUE","unit_id":"worker-success-finalization"}']
    )
    result = RUNTIME.probe(plan(), {}, "decision", client)
    assert [item["response_usage"]["total_tokens"] for item in result["model_requests"]] == [1, 2]
    client.last_request_stats["response_usage"]["total_tokens"] = 99
    assert result["model_requests"][1]["response_usage"]["total_tokens"] == 2
    assert "not JSON" not in json.dumps(result["model_requests"])


def test_illegal_acceptance_gets_one_correction_not_execution():
    client = Client(['{"decision":"ACCEPT","unit_id":"worker-success-finalization"}', "{}"])
    result = RUNTIME.probe(plan(), {}, "decision", client)
    assert result["status"] == "protocol_failed"
    assert result["model_turns"] == 2
    assert len(result["correction_errors"]) == 2
    assert "ACCEPT" not in client.messages[1][-1]["content"]


def test_packet_cannot_inject_primary_risk_or_contract():
    client = Client(['{"risk":"small","required_behavior":[]}', "{}"])
    result = RUNTIME.probe(plan(), {}, "proposal", client)
    assert result["status"] == "protocol_failed"
    assert "authority-bearing" in result["correction_errors"][0]


def test_non_json_correction_does_not_echo_raw_response():
    client = Client(
        [
            "secret untrusted invalid output",
            '{"decision":"ESCALATE_PRIMARY","unit_id":"worker-success-finalization","reason_code":"scope-expansion"}',
        ]
    )
    result = RUNTIME.probe(plan(), {}, "decision", client)
    assert result["status"] == "protocol_valid"
    assert result["model_turns"] == 2
    assert "secret" not in client.messages[1][-1]["content"]


def test_probe_report_never_overwrites_or_escapes_workspace(tmp_path):
    assert RUNTIME.report_target(tmp_path, Path(".agent/probes/a1.json")) == (
        tmp_path / ".agent/probes/a1.json"
    )
    with pytest.raises(ValueError, match="inside workspace"):
        RUNTIME.report_target(tmp_path, Path("../elsewhere.json"))
    existing = tmp_path / ".agent/probes/a1.json"
    existing.parent.mkdir(parents=True)
    existing.write_text("old outcome")
    with pytest.raises(ValueError, match="target exists"):
        RUNTIME.report_target(tmp_path, existing)
    assert existing.read_text() == "old outcome"


def proposal():
    return {
        "unit_id": "worker-success-finalization",
        "run_id": "probe-a1",
        "attempt": 1,
        "packet_revision": 1,
        "goal": "Preserve post-handler lease fencing.",
        "scope": {
            "read": ["src/agent_runtime", "tests/test_lease_fencing.py"],
            "modify": ["src/agent_runtime/worker.py"],
            "create": [],
        },
        "edit_targets": [{"path": "src/agent_runtime/worker.py", "anchor": "def execute_job"}],
        "focused_tests": ["tests/test_lease_fencing.py"],
        "supplemental_tests": [],
        "implementation_guidance": [],
    }


def test_proposal_binds_identity_and_keeps_primary_obligations():
    value = proposal()
    identity = {key: value[key] for key in ("unit_id", "run_id", "attempt", "packet_revision")}
    result = RUNTIME.probe(plan(), {"identity": identity}, "proposal", Client([json.dumps(value)]))
    assert result["status"] == "protocol_valid"
    assert result["verified"]["risk"]["unit"] == "high"
    assert result["verified"]["scope"]["readonly"] == ["tests/test_lease_fencing.py"]
    identity["run_id"] = "different-run"
    result = RUNTIME.probe(
        plan(), {"identity": identity}, "proposal", Client([json.dumps(value)] * 2)
    )
    assert result["status"] == "protocol_failed"
    assert "Primary-granted identity" in result["correction_errors"][0]


def test_valid_shape_cannot_expand_scope():
    value = proposal()
    identity = {key: value[key] for key in ("unit_id", "run_id", "attempt", "packet_revision")}
    value["scope"]["modify"].append("src/agent_runtime/outside.py")
    result = RUNTIME.probe(
        plan(), {"identity": identity}, "proposal", Client([json.dumps(value)] * 2)
    )
    assert result["status"] == "protocol_failed"
    assert "authority" in result["correction_errors"][0]


def test_reason_code_correction_supplies_exact_legal_shape_without_normalizing():
    client = Client(
        [
            '{"decision":"ESCALATE_PRIMARY","unit_id":"lease-test-support","reason_code":"PRIMARY_PENDING"}',
            '{"decision":"ESCALATE_PRIMARY","unit_id":"lease-test-support","reason_code":"primary-unit-pending"}',
        ]
    )
    result = RUNTIME.probe(plan(), {}, "decision", client)
    assert result["status"] == "protocol_valid"
    assert result["model_turns"] == 2
    hint = client.messages[1][-1]["content"]
    assert '"reason_code": "primary-unit-pending"' in hint
    assert "PRIMARY_PENDING" not in hint
    assert result["output"]["reason_code"] == "primary-unit-pending"


def test_coder_schema_error_is_bounded_proposal_correction_not_crash():
    valid = proposal()
    invalid = json.loads(json.dumps(valid))
    invalid["edit_targets"].append("src/agent_runtime/worker.py")
    identity = {key: valid[key] for key in ("unit_id", "run_id", "attempt", "packet_revision")}
    client = Client([json.dumps(invalid), json.dumps(valid)])
    result = RUNTIME.probe(plan(), {"identity": identity}, "proposal", client)
    assert result["status"] == "protocol_valid"
    assert result["model_turns"] == 2
    assert "Coder packet schema rejected" in result["correction_errors"][0]
    assert "never bare strings" in client.messages[1][-1]["content"]


def test_feature_ready_unit_correction_supplies_legal_unit_ids():
    client = Client(
        [
            '{"decision":"FEATURE_READY","unit_id":"lease-fencing"}',
            '{"decision":"FEATURE_READY","unit_id":"lease-documentation"}',
        ]
    )
    result = RUNTIME.probe(plan(), {}, "decision", client)
    assert result["status"] == "protocol_valid"
    assert result["model_turns"] == 2
    hint = client.messages[1][-1]["content"]
    assert "Never use feature_id" in hint
    assert '"lease-documentation"' in hint
    assert result["dispatch_allowed"] is False
