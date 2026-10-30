import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import tool_deadline_fresh_trial as trial
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes


def test_prepared_unit_is_fresh_scoped_and_preserves_twenty_protected_tests(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(trial, "BASE", tmp_path / "fresh")
    trial.register()
    for arm in ("control-1", "candidate-1"):
        trial.prepare(arm)
        root = trial.BASE / arm
        packet = read(root / ".agent/packet.json")
        config = read(root / ".agent/config.json")
        assert config["reviewer_require_approved_execution"] is True
        inputs = read(root / ".agent/inputs.json")
        assert packet["run_id"] == "fresh-" + arm + "-a1"
        assert packet["review_feedback"] == []
        assert trial.TEST in packet["scope"]["readonly"]
        assert trial.TEST in packet["focused_tests"]
        assert packet["scope"]["modify"] == [trial.TARGET]
        assert trial.TEST not in packet["scope"]["create"]
        assert digest(root / trial.TARGET) == digest(trial.FROZEN / trial.TARGET)
        verify_hashes(root, {**inputs["files"], **inputs["protected"]})
        assert config["reviewer_dependency_evidence"][0]["anchors"] == [
            "copy_context",
            "ctx.run",
        ]
        profile = config["validation_profiles"]["project-strict"]
        assert (
            "--basetemp=" + str(root / ".agent/worker-temp-a1")
            in profile["pytest_argv"]
        )
        assert all(trial.TEST in check["argv"] for check in profile["commands"][:2])
        with pytest.raises(FileExistsError):
            trial.prepare(arm)
    with pytest.raises(FileExistsError):
        trial.register()
