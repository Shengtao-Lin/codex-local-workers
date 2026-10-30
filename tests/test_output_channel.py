"""Offline representation controls and real runtime/canonical handoff replay."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_fixture_support as F
import coder_output_channel as C
import output_channel_trial as TRIAL

I = F.load(F.KIT / ".local-agents/proposal-interface.py", "output_test_interface")
S = F.load(F.KIT / ".local-agents/single-function-context.py", "output_test_guard")
SOURCE = "def target(value: str) -> str:\n    return value\n"
BINDING = {"path": "src/target.py", "sha256": "a" * 64, "source": SOURCE}


@pytest.mark.parametrize("arm", ["raw", "schema"])
@pytest.mark.parametrize(
    "body",
    [
        '    """Unicode 中文 and quotes."""\n    return value\n',
        '    return value + "\\n"\n',
        '    return f"{value}!"\n',
    ],
)
def test_representation_preserves_body(arm, body):
    code = "def target(value: str) -> str:\n" + body
    args = (
        C.normalize_raw(code, BINDING)
        if arm == "raw"
        else I.normalize_whole(json.dumps({"replacement": code}), BINDING)
    )
    args = I.terminal_boundary(args)
    S.guard({"path": BINDING["path"], "symbol": "target"}, SOURCE, args)
    assert args["replace"] == code
    assert args["expected_sha256"] == BINDING["sha256"]


@pytest.mark.parametrize("arm", ["raw", "schema"])
@pytest.mark.parametrize(
    "code",
    [
        "```python\ndef target(value: str) -> str:\n    return value\n```",
        "def other(value: str) -> str:\n    return value\n",
        "def target(value: int) -> str:\n    return str(value)\n",
        "async def target(value: str) -> str:\n    return value\n",
        "def target(value: str) -> str:\n    return value\n\nx = 1\n",
        "Here is code:\ndef target(value: str) -> str:\n    return value\n",
    ],
)
def test_invalid_code_never_extracted_or_repaired(arm, code):
    with pytest.raises((ValueError, SyntaxError)):
        args = (
            C.normalize_raw(code, BINDING)
            if arm == "raw"
            else I.normalize_whole(json.dumps({"replacement": code}), BINDING)
        )
        args = I.terminal_boundary(args)
        S.guard({"path": BINDING["path"], "symbol": "target"}, SOURCE, args)


@pytest.mark.parametrize("arm", ["raw", "schema"])
def test_real_constructor_and_preflight(arm):
    row = TRIAL.T.read(TRIAL.BATCH / "cells.json")[arm + "-1"]
    root = Path(row["root"])
    worker = F.load(root / ".local-agents/worker-runtime.py", "output_offline_" + arm)
    host = F.load(root / ".local-agents/host-proposal.py", "output_offline_host_" + arm)
    packet, config = (
        TRIAL.T.read(root / ".agent/packet.json"),
        TRIAL.T.read(root / ".agent/config.json"),
    )
    from capture_coder_entry import install

    install(worker, F.POLICY_PATH, row["policy_sha256"])
    cls = C.make_runtime(worker, host, arm)
    client = type(
        "NoModel",
        (),
        {
            "structured_output": arm == "schema",
            "action_schema": I.WHOLE_SCHEMA,
            "native_tools": None,
            "typed_action_arguments": False,
            "timeout": 180,
        },
    )()
    runtime = cls(root, packet, config, client)
    try:
        runtime.preflight()
        assert runtime.host_request_cap == 6
        assert runtime.host_check_cap == runtime.host_edit_cap == 3
        messages, binding = runtime.proposal_context()
        facts = I.restore_literal(messages[1]["content"])
        assert facts["target"]["source"] == binding["source"]
        # Both representations preserve the exact same model-visible facts.
        assert messages[0]["content"] == (
            C.RAW_PROMPT if arm == "raw" else I.WHOLE_PROMPT
        )
    finally:
        runtime.close()
    wrong = copy.deepcopy(config)
    wrong["coder_structured_output"] = arm != "schema"
    with pytest.raises(worker.WorkerError, match="transport mismatch"):
        cls(root, packet, wrong, client)


def test_schema_is_not_generic_action_schema():
    worker = F.load(F.KIT / ".local-agents/worker-runtime.py", "output_wire_test")
    client = worker.LMStudioClient(
        "http://127.0.0.1:12345/v1",
        "qwen/qwen3-coder-30b",
        180,
        structured_output=True,
        action_schema=I.WHOLE_SCHEMA,
        schema_name="experimental_whole_function_v1",
    )
    assert client.action_schema == I.WHOLE_SCHEMA
    assert client.action_schema != worker.CODER_ACTION_SCHEMA


def test_malformed_json_remains_malformed():
    with pytest.raises(ValueError):
        I.normalize_whole(
            '{"replacement":"def target(value: str) -> str:\\n    """doc""""}', BINDING
        )


def test_private_tests_and_contract_unchanged():
    rows = TRIAL.T.read(TRIAL.BATCH / "cells.json")
    seed = TRIAL.T.read(TRIAL.M.BATCH / "prepared-cells-v3.json")[
        "metadata-candidate-1"
    ]
    packets, configs = [], []
    for row in rows.values():
        root = Path(row["root"])
        for p, sha in seed["files"].items():
            if p not in {".agent/packet.json", ".agent/config.json", F.POLICY_PATH}:
                assert TRIAL.T.sha(root / p) == sha
        packet = TRIAL.T.read(root / ".agent/packet.json")
        packet.pop("run_id")
        packets.append(packet)
        config = TRIAL.T.read(root / ".agent/config.json")
        config.pop("experimental_output_channel")
        config.pop("coder_structured_output")
        configs.append(config)
    assert all(p == packets[0] for p in packets)
    assert all(c == configs[0] for c in configs)


@pytest.mark.parametrize("arm", ["raw", "schema"])
def test_scripted_full_host_and_canonical_handoff(tmp_path, arm):
    import shutil

    import reviewer_canonical_capture as CANONICAL

    row = TRIAL.T.read(TRIAL.BATCH / "cells.json")[arm + "-1"]
    root = tmp_path / "isolated"
    shutil.copytree(row["root"], root)
    worker = F.load(root / ".local-agents/worker-runtime.py", "output_replay_" + arm)
    host = F.load(root / ".local-agents/host-proposal.py", "output_replay_host_" + arm)
    packet = TRIAL.T.read(root / ".agent/packet.json")
    config = TRIAL.T.read(root / ".agent/config.json")
    from capture_coder_entry import install

    install(worker, F.POLICY_PATH, row["policy_sha256"])
    cls = C.make_runtime(worker, host, arm)
    code = TRIAL.M.function(
        TRIAL.M.BATCH / "private/metadata/reference.py", "validate_metadata"
    )

    class Scripted:
        timeout = 180
        structured_output = arm == "schema"
        action_schema = I.WHOLE_SCHEMA
        native_tools = None
        typed_action_arguments = False

        def complete(self, messages):
            return code if arm == "raw" else json.dumps({"replacement": code})

    runtime = cls(root, packet, config, Scripted())
    runtime.preflight()
    report = runtime.run()
    assert report["status"] == "validation_passed_pending_review", report.get(
        "failure_reason"
    )
    assert report["worker_assessment"] is None
    gate = F.load(root / ".local-agents/local-unit.py", "output_replay_gate_" + arm)
    assert (
        gate.verify_handoff(root, report, config=config)["run_id"] == packet["run_id"]
    )
    # Full canonical consumer is tested by the already-frozen capture controls;
    # here we verify the actual new transport produces its unchanged input seal.
    assert CANONICAL is not None
    assert runtime.host_requests == 1
    assert runtime.validation_count <= 3
