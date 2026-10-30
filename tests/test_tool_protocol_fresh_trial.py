import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes


@pytest.mark.parametrize(
    "module",
    [
        "tool_protocol_fresh_trial",
        "tool_bundle_fresh_trial",
        "tool_retained_fresh_trial",
    ],
)
def test_new_real_units_keep_twenty_protected_tests_and_approved_execution(
    tmp_path, monkeypatch, module
):
    trial = importlib.import_module(module)
    monkeypatch.setattr(trial, "BASE", tmp_path / "fresh")
    trial.register()
    for arm in trial.ARMS:
        trial.prepare(arm)
        root = trial.BASE / arm
        packet = read(root / ".agent/packet.json")
        config = read(root / ".agent/config.json")
        assert packet["risk"]["unit"] == "high"
        assert packet["scope"]["modify"] == [trial.TARGET]
        assert packet["scope"]["create"] == []
        assert packet["review_feedback"] == []
        assert digest(root / trial.TARGET) == digest(trial.FROZEN / trial.TARGET)
        assert config["reviewer_require_approved_execution"] is True
        assert len(config["reviewer_contract_test_reads"]) == 2
        for rule in config["reviewer_contract_test_reads"]:
            assert rule["path"] in packet["scope"]["readonly"]
            assert rule["path"] in packet["focused_tests"]
        assert "reference/awaitable_protocol.txt" in packet["scope"]["readonly"]
        assert not (root / "reference/upstream").exists()
        assert trial.TEST in packet["focused_tests"]
        inputs = read(root / ".agent/inputs.json")
        verify_hashes(root, {**inputs["files"], **inputs["protected"]})
        with pytest.raises(FileExistsError):
            trial.prepare(arm)
    with pytest.raises(FileExistsError):
        trial.register()
