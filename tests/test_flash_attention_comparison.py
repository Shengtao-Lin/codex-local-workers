import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import flash_attention_comparison as fa  # noqa: E402


def test_only_fa_can_differ():
    original = {"flash_attention": True, "context_length": 24576, "parallel": 1}
    fa.require_config(dict(original, flash_attention=False), original, False)
    with pytest.raises(ValueError, match="context_length"):
        fa.require_config(
            dict(original, flash_attention=False, context_length=4096), original, False
        )
    with pytest.raises(ValueError):
        fa.require_config({"flash_attention": False}, original, False)


def test_foreign_or_extra_instances_refused():
    inventory = {
        "models": [
            {"key": fa.MODEL, "loaded_instances": [{"id": fa.MODEL, "config": {}}]}
        ]
    }
    assert fa.instance(inventory)["id"] == fa.MODEL
    inventory["models"].append(
        {"key": "foreign", "loaded_instances": [{"id": "foreign"}]}
    )
    with pytest.raises(ValueError, match="refuse foreign"):
        fa.instance(inventory)


def test_restore_noop_and_changed_config(monkeypatch, tmp_path):
    original = {"flash_attention": True, "context_length": 24576}
    state = {
        "models": [
            {
                "key": fa.MODEL,
                "loaded_instances": [
                    {"id": fa.MODEL, "config": dict(original, flash_attention=False)}
                ],
            }
        ]
    }
    monkeypatch.setattr(fa, "api", lambda *args: state)
    calls = []

    def reload(saved, enabled, directory, label):
        calls.append((saved, enabled, label))
        state["models"][0]["loaded_instances"][0]["config"] = dict(saved)

    monkeypatch.setattr(fa, "reload_model", reload)
    fa.restore_model(original, tmp_path)
    assert calls == [(original, True, "restore")]
    assert fa.read(tmp_path / "restoration.json")["restored"] is True


def test_restore_after_failed_load(monkeypatch, tmp_path):
    original = {key: 1 for key in fa.LOAD_KEYS}
    original["flash_attention"] = True
    state = {"models": [{"key": fa.MODEL, "loaded_instances": []}]}
    requests = []

    def api(suffix="", body=None):
        if suffix == "/load":
            requests.append(body)
            state["models"][0]["loaded_instances"] = [
                {"id": fa.MODEL, "config": original}
            ]
            return {"status": "loaded"}
        return state

    monkeypatch.setattr(fa, "api", api)
    fa.restore_model(original, tmp_path)
    assert requests[0]["flash_attention"] is True
    assert fa.read(tmp_path / "restoration.json")["restored"] is True
