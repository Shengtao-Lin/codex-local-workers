"""Actual wire schema plus unchanged execution guards; no real model calls."""

import importlib.util
import io
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "c3_worker_helpers", ROOT / ".local-agents/tests/test_worker_runtime.py"
)
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)
RUNTIME = HELPERS.RUNTIME


@pytest.mark.parametrize("typed", [False, True])
def test_wire_and_current_execution_authority(typed):
    client = RUNTIME.LMStudioClient(
        "http://unused/v1", "unchanged-model", typed_action_arguments=typed
    )
    client.action_schema = RUNTIME.validation_only_action_schema(
        RUNTIME.CODER_ACTION_SCHEMA
    )
    captured = []

    def response(request, **kwargs):
        captured.append(json.loads(request.data))
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"action":"VALIDATE","arguments":{}}'
                            },
                            "finish_reason": "stop",
                        }
                    ]
                }
            ).encode()
        )

    with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=response):
        action = RUNTIME.parse_action(
            client.complete([{"role": "user", "content": "test"}])
        )
    schema = captured[0]["response_format"]["json_schema"]["schema"]
    assert schema == (
        RUNTIME.typed_coder_action_schema(client.action_schema)
        if typed
        else client.action_schema
    )
    if typed:
        branches = {b["properties"]["action"]["enum"][0]: b for b in schema["anyOf"]}
        assert set(branches) == set(
            client.action_schema["properties"]["action"]["enum"]
        )
        assert branches["VALIDATE"]["properties"]["arguments"]["required"] == []
    with TemporaryDirectory() as directory:
        root = Path(directory)
        HELPERS.WorkerRuntimeTests().make_tree(root)
        packet = HELPERS.packet_v2()
        packet["contract_check_required"] = True
        runtime = RUNTIME.WorkerRuntime(
            root, packet, {"python": sys.executable}, client
        )
        runtime.write_lock.acquire()
        try:
            runtime._prepare_run_archive()
            # Provider-valid shape is not a mandatory contract acknowledgement.
            with pytest.raises(RUNTIME.WorkerError, match="contract_check"):
                runtime.validate(action["arguments"])
            assert runtime.validation_count == 0
            observed = runtime.read_file({"path": "src/example.py"})
            args = {
                "path": "src/example.py",
                "expected_sha256": observed["sha256"],
                "replacement": "VALUE = 2",
            }
            with pytest.raises(RUNTIME.WorkerError):
                runtime.safe_replace_line(args)
            with pytest.raises(RUNTIME.SafeEditError):
                runtime.safe_replace_line(
                    {**args, "line": 1, "replacement": "VALUE = 2\nOTHER = 3"}
                )
            assert (root / "src/example.py").read_text() == "VALUE = 1\n"
            runtime.validation = RUNTIME.ValidationResult(
                "passed", {"status": "passed"}, {"status": "passed"}
            )
            runtime.validated_revision = runtime.edit_revision
            runtime.validated_input_facts = runtime._validation_facts()
            runtime.validation_phase = "final"
            assert runtime._validated_terminal_state()
            (root / "src/example.py").write_text("VALUE = 99\n")
            assert not runtime._validated_terminal_state()
            with pytest.raises(RUNTIME.SafeEditError):
                runtime.safe_replace_line({**args, "line": 1})
            assert runtime.edit_revision == 0
        finally:
            runtime.close()


def test_tagged_schema_unknown_action_and_state_allowlists():
    import copy

    for narrow in (
        RUNTIME.repair_only_action_schema(RUNTIME.CODER_ACTION_SCHEMA, "SAFE_REPLACE"),
        RUNTIME.post_edit_progress_schema(RUNTIME.CODER_ACTION_SCHEMA),
        RUNTIME.validation_only_action_schema(RUNTIME.CODER_ACTION_SCHEMA),
    ):
        tagged = RUNTIME.typed_coder_action_schema(narrow)
        assert {b["properties"]["action"]["enum"][0] for b in tagged["anyOf"]} == set(
            narrow["properties"]["action"]["enum"]
        )
    bad = copy.deepcopy(RUNTIME.CODER_ACTION_SCHEMA)
    bad["properties"]["action"]["enum"] = ["SHELL"]
    with pytest.raises(RUNTIME.WorkerError, match="unknown typed"):
        RUNTIME.typed_coder_action_schema(bad)
