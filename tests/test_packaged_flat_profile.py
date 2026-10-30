"""Installed compatibility selection and original residency invariants."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / ".local-agents"))
sys.path.insert(0, str(KIT / "benchmarks"))
import bounded_evidence_support as S
import tagged_proposal_wire as FROZEN
from bounded import compatibility_profile as PROFILE
from bounded import static_focus_rules as BASE
from bounded import tagged_wire


def test_default_is_exact_old_rules_and_profile_does_not_mutate_them():
    assert PROFILE.proposal_rules({}, BASE) is BASE
    selected = PROFILE.proposal_rules(
        {"bounded_compatibility_profile": "flat-v1"}, BASE
    )
    assert selected.SCHEMA == FROZEN.SCHEMA
    assert selected.PROMPT == FROZEN.PROMPT
    assert selected.guard is BASE.guard and selected.materialize is BASE.materialize
    assert "oneOf" in BASE.SCHEMA
    assert selected.decode('{"kind":"blocked","content":"need caller"}') == (
        {"blocked_reason": "need caller"},
        [],
    )
    assert PROFILE.proposal_rules({}, BASE) is BASE


@pytest.mark.parametrize("value", [True, False, "unknown", 1, {}])
def test_unknown_profile_fails_before_any_model(value):
    with pytest.raises(ValueError):
        PROFILE.proposal_rules({"bounded_compatibility_profile": value}, BASE)


def test_packaged_decoder_matches_frozen_wire_normalization():
    namespace = {"decode": BASE.decode}
    FROZEN.extend(namespace)
    for kind in ("replacement", "blocked"):
        raw = json.dumps({"kind": kind, "content": 'def f():\n    return "雪"\n'})
        assert tagged_wire.decode(raw) == namespace["decode"](raw)


def test_installed_profile_uses_flat_schema_and_real_canonical_checks():
    import limited_family_trial as L
    from test_installable_bounded import archive, project, run

    with tempfile.TemporaryDirectory(prefix="packaged-flat-") as directory:
        root = Path(directory)
        project(root, "labels", "packaged-flat-offline")
        config_path = root / ".agent/config.json"
        config = S.read(config_path)
        config.update(
            bounded_compatibility_profile="flat-v1",
            model_load_ack_policy="api_verified",
        )
        config_path.write_text(json.dumps(config), encoding="utf-8")
        result = run(
            root, [{"kind": "replacement", "content": L.TASKS["labels"]["reference"]}]
        )
        assert result.returncode == 0, result.stderr
        report = S.read(root / ".agent/unit-report.json")
        assert report["status"] == "validation_passed_pending_review"
        assert report["consolidated_harness"]["actual"]["post_edit_checks"] == 1
        request = S.read(archive(root) / "proposal-request-1.json")
        assert request["schema"] == FROZEN.SCHEMA
        assert request["messages"][0]["content"] == FROZEN.PROMPT
        assert S.read(root / ".agent/unit-summary.json")["reviewer_input_authenticated"]


@pytest.mark.parametrize(
    "state,policy,passes",
    [
        ({"context_length": 24576, "parallel": 1}, "api_verified", True),
        ({"context_length": 24576, "parallel": 1}, "strict", False),
        ({"context_length": 1000, "parallel": 1}, "api_verified", False),
        ({"context_length": 24576, "parallel": 2}, "api_verified", False),
        ({"parallel": 1}, "api_verified", False),
        (None, "api_verified", False),
        ("extra", "api_verified", False),
    ],
)
def test_cli_timeout_never_skips_original_inventory_context_or_parallel(
    tmp_path, state, policy, passes
):
    spec = importlib.util.spec_from_file_location(
        "packaged_residency", KIT / ".local-agents/model_residency.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = SimpleNamespace(
        base_url="http://127.0.0.1:12345/v1",
        model="meta/muse-glimmer",
        context_length=24576,
    )
    config = {
        "single_model_residency": True,
        "model_load_backend": "cli",
        "model_load_ack_policy": policy,
        "model_switch_timeout_seconds": 1,
        "explorer_model": "openai/gpt-oss-20b",
        "coder_model": "qwen/qwen3-coder-30b",
        "reviewer_model": client.model,
    }
    empty = {client.model: {"loaded_instances": []}}
    instances = (
        []
        if state is None
        else [
            {
                "id": client.model,
                "config": state
                if state != "extra"
                else {"parallel": 1, "context_length": 24576},
            }
        ]
    )
    after = {client.model: {"loaded_instances": instances}}
    if state == "extra":
        after["qwen/qwen3-coder-30b"] = {
            "loaded_instances": [{"id": "other", "config": {}}]
        }
    with (
        patch.object(module, "_cli_path", return_value=Path(__file__)),
        patch.object(module, "_inventory", side_effect=[empty, empty, after]),
        patch.object(module.tempfile, "gettempdir", return_value=str(tmp_path)),
        patch.object(
            module.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired("lms load", 1),
        ),
    ):
        if passes:
            with module.role_model_lease(client, config):
                assert client.last_model_residency["api_readiness_verified"] is True
        else:
            with pytest.raises(module.ModelResidencyError), module.role_model_lease(client, config):
                pytest.fail("Unverified model admitted")
    assert not list(tmp_path.glob("*.lock"))
