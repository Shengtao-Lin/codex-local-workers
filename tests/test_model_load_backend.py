"""Loader selection must not weaken lease, cancellation or residency gates."""

import importlib.util
import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "loader_backend_test",
    Path(__file__).parents[1] / ".local-agents/model_residency.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Response(io.BytesIO):
    def __exit__(self, *_args):
        self.close()


@pytest.fixture
def harness(tmp_path, monkeypatch):
    cli = tmp_path / "lms.exe"
    cli.touch()
    client = SimpleNamespace(
        base_url="http://127.0.0.1:12345/v1",
        model="test/reviewer",
        context_length=24576,
    )
    config = {
        "single_model_residency": True,
        "explorer_model": "test/explorer",
        "coder_model": "test/coder",
        "reviewer_model": client.model,
        "model_load_backend": "cli",
        "model_load_cli_path": str(cli),
        "model_switch_timeout_seconds": 17,
    }
    monkeypatch.setattr(MODULE.tempfile, "gettempdir", lambda: str(tmp_path))
    state = {"loaded": [], "actions": []}

    def inventory(*_args):
        state["actions"].append("inventory")
        return {
            key: {"loaded_instances": [i for k, i in state["loaded"] if k == key]}
            for key in (client.model, "test/coder", "external/model")
        }

    def run(argv, **kwargs):
        state["actions"].append("cli")
        assert argv == [
            str(cli),
            "load",
            client.model,
            "--identifier",
            client.model,
            "--parallel",
            "1",
            "--yes",
            "--context-length",
            "24576",
        ]
        assert kwargs == {
            "timeout": 17,
            "shell": False,
            "check": False,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        state["loaded"] = [
            (
                client.model,
                {
                    "id": client.model,
                    "config": {"context_length": 24576, "parallel": 1},
                },
            )
        ]
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(MODULE, "_inventory", inventory)
    monkeypatch.setattr(MODULE.subprocess, "run", run)
    return client, config, state


def test_cli_success_argv_and_exclusive_lease(harness, tmp_path):
    client, config, state = harness
    with MODULE.role_model_lease(client, config):
        assert state["actions"] == ["inventory", "inventory", "cli", "inventory"]
        with (
            pytest.raises(MODULE.ModelResidencyError, match="lease is held"),
            MODULE.role_model_lease(client, config),
        ):
            pytest.fail("second lease admitted")
    assert not list(tmp_path.glob("*.lock"))


@pytest.mark.parametrize(
    "failure",
    [
        "timeout",
        "exit",
        "missing_inventory",
        "bad_parallel",
        "missing_context",
        "small_context",
        "multiple_instances",
    ],
)
def test_cli_failures_never_yield_or_retry(harness, monkeypatch, tmp_path, failure):
    client, config, state = harness
    original = MODULE.subprocess.run
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, 17)
        if failure == "exit":
            return SimpleNamespace(returncode=4)
        result = original(argv, **kwargs)
        instance = state["loaded"][0][1]
        if failure == "missing_inventory":
            state["loaded"] = []
        elif failure == "bad_parallel":
            instance["config"]["parallel"] = 2
        elif failure == "missing_context":
            del instance["config"]["context_length"]
        elif failure == "small_context":
            instance["config"]["context_length"] = 4096
        elif failure == "multiple_instances":
            state["loaded"].append((client.model, {**instance, "id": "second"}))
        return result

    monkeypatch.setattr(MODULE.subprocess, "run", run)
    with (
        pytest.raises(MODULE.ModelResidencyError) as raised,
        MODULE.role_model_lease(client, config),
    ):
        pytest.fail("failed loader admitted worker")
    assert len(calls) == 1
    assert raised.value.stage == (
        "load_cli" if failure in ("timeout", "exit") else "inventory_after_load"
    )
    assert raised.value.elapsed_seconds >= 0
    assert not list(tmp_path.glob("*.lock"))


@pytest.mark.parametrize(
    "invalid", ["backend", "relative_path", "missing_path", "remote"]
)
def test_bad_config_fails_before_inventory(harness, invalid):
    client, config, state = harness
    if invalid == "backend":
        config["model_load_backend"] = "auto"
    elif invalid == "relative_path":
        config["model_load_cli_path"] = "lms.exe"
    elif invalid == "missing_path":
        config["model_load_cli_path"] += ".absent"
    else:
        client.base_url = "http://remote.invalid:12345/v1"
    with (
        pytest.raises(MODULE.ModelResidencyError) as raised,
        MODULE.role_model_lease(client, config),
    ):
        pytest.fail("invalid config admitted")
    assert raised.value.reason_code == "model_switch_config"
    assert not state["actions"]


def test_foreign_model_blocks_cli(harness):
    client, config, state = harness
    state["loaded"] = [("external/model", {"id": "external"})]
    with (
        pytest.raises(MODULE.ModelResidencyError) as raised,
        MODULE.role_model_lease(client, config),
    ):
        pytest.fail("foreign residency ignored")
    assert raised.value.reason_code == "foreign_model_loaded"
    assert state["actions"] == ["inventory"]


def test_unload_ack_without_actual_unload_blocks_cli(harness, monkeypatch):
    client, config, state = harness
    state["loaded"] = [("test/coder", {"id": "test/coder"})]
    monkeypatch.setattr(
        MODULE.urllib.request,
        "urlopen",
        lambda *_a, **_k: Response(b'{"instance_id":"test/coder"}'),
    )
    with (
        pytest.raises(MODULE.ModelResidencyError, match="remains loaded"),
        MODULE.role_model_lease(client, config),
    ):
        pytest.fail("second model load admitted")
    assert "cli" not in state["actions"]


def test_native_timeout_has_stage_no_cli_fallback(harness, monkeypatch):
    client, config, state = harness
    config["model_load_backend"] = "native"

    def fail(request, **_kwargs):
        assert json.loads(request.data)["model"] == client.model
        raise TimeoutError("ack timed out")

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", fail)
    with (
        pytest.raises(MODULE.ModelResidencyError) as raised,
        MODULE.role_model_lease(client, config),
    ):
        pytest.fail("native timeout admitted worker")
    assert raised.value.stage == "load_native"
    assert raised.value.reason_code == "model_switch_failed"
    assert "stage=load_native" in str(raised.value)
    assert "cli" not in state["actions"]


def test_verified_unload_precedes_cli_load(harness, monkeypatch):
    client, config, state = harness
    state["loaded"] = [("test/coder", {"id": "test/coder"})]

    def unload(request, timeout):
        assert timeout == 17
        assert request.full_url.endswith("/unload")
        assert json.loads(request.data) == {"instance_id": "test/coder"}
        state["actions"].append("unload")
        state["loaded"] = []
        return Response(b'{"instance_id":"test/coder"}')

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", unload)
    with MODULE.role_model_lease(client, config):
        assert state["actions"] == [
            "inventory",
            "unload",
            "inventory",
            "cli",
            "inventory",
        ]


def test_already_loaded_target_skips_cli_but_checks_context(harness):
    client, config, state = harness
    state["loaded"] = [
        (
            client.model,
            {"id": client.model, "config": {"context_length": 24576, "parallel": 1}},
        )
    ]
    with MODULE.role_model_lease(client, config):
        assert state["actions"] == ["inventory", "inventory", "inventory"]
