"""Portable preview boundaries, with no provider calls or dependency install."""

import importlib.util
import json
from pathlib import Path

import pytest
from strata_native_host_v4 import NativeV4Client
from test_strata_native_agent_budget import client, frame

KIT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENTRY = load("strata_preview_entry_test", KIT / ".local-agents/strata-worker.py")
INSTALL = load("strata_preview_install_test", KIT / "tools/install-strata-preview.py")


def config(tmp_path):
    node = tmp_path / "node.exe"
    node.write_text("not executed")
    harness = tmp_path / "harness"
    harness.mkdir()
    (harness / "BUNDLE.json").write_text(
        json.dumps({"component": "deepseek-harness", "version": "0.2.1-alpha.3"})
    )
    return {
        "strata_node_path": str(node),
        "strata_harness_root": str(harness),
        "strata_base_url": "http://127.0.0.1:47831/v1",
        "coder_model": "iq3_s",
        "experimental_strata_subagent": True,
        "coordinator_enabled": False,
    }


def test_explicit_existing_runtime_only(tmp_path):
    value = config(tmp_path)
    assert ENTRY.checked_config(value)["model"] == "iq3_s"
    del value["strata_node_path"]
    with pytest.raises(ValueError, match="Explicit"):
        ENTRY.checked_config(value)


@pytest.mark.parametrize(
    "url",
    [
        "https://cloud.invalid/v1",
        "http://localhost:47831/v1",
        "http://127.0.0.1:47831/v1?cloud=1",
        "http://user:secret@127.0.0.1:47831/v1",
        "http://127.0.0.1:47831/other",
    ],
)
def test_no_provider_fallback_or_credential_url(tmp_path, url):
    value = config(tmp_path)
    value["strata_base_url"] = url
    with pytest.raises(ValueError, match="Only explicit"):
        ENTRY.checked_config(value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("coder_model", "different"),
        ("experimental_strata_subagent", False),
        ("coordinator_enabled", True),
    ],
)
def test_capability_expansion_requires_other_qualification(tmp_path, key, value):
    settings = config(tmp_path)
    settings[key] = value
    with pytest.raises(ValueError):
        ENTRY.checked_config(settings)


def test_different_harness_fails_closed(tmp_path):
    settings = config(tmp_path)
    (tmp_path / "harness/BUNDLE.json").write_text(
        '{"component":"deepseek-harness","version":"future"}'
    )
    with pytest.raises(ValueError, match="version"):
        ENTRY.checked_config(settings)


def test_create_only_install_and_runtime_drift(tmp_path, monkeypatch):
    installed = INSTALL.install(tmp_path)
    assert installed["files"] > 30
    monkeypatch.setattr(ENTRY, "ROOT", tmp_path / ".local-agents")
    assert ENTRY.verify_installation()["version"] == "0.1.0-preview-candidate.4.1"
    with pytest.raises(FileExistsError):
        INSTALL.install(tmp_path)
    module = tmp_path / ".local-agents/strata/strata_native_agent_core.mjs"
    assert "F:/Strata" not in module.read_text()
    module.write_text("tampered")
    with pytest.raises(ValueError, match="drift"):
        ENTRY.verify_installation()


def v4():
    c = client()
    c.__class__ = NativeV4Client
    return c


@pytest.mark.parametrize("requests,reservations", [(10, 8), (12, 6), (5, 8)])
def test_v4_model_limits_are_finite(requests, reservations):
    c = v4()
    c.runtime.ledger.update(requests=requests, native_request_reservations=reservations)
    frame(c, "native_model_permit", body={"model": "iq3_s", "max_tokens": 12288})
    with pytest.raises(RuntimeError, match="Shared"):
        c.receive()
    assert not c.sent


def test_multiple_native_tool_calls_cannot_exceed_combined_budget():
    c = v4()
    c.runtime.ledger.update(requests=12, native_request_reservations=7)
    frame(c, "host_action", action="propose")
    with pytest.raises(RuntimeError, match="Shared native"):
        c.receive()
