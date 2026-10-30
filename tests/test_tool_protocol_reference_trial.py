import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from inherited_context_recovery import read
from layer_isolation import verify_hashes


@pytest.mark.parametrize(
    "module",
    ["tool_reviewer_protocol_reference_trial", "tool_reviewer_test_consistency_trial"],
)
def test_real_blind_validation_and_oracle_are_distinct_from_coder_credit(
    tmp_path, monkeypatch, module
):
    trial = importlib.import_module(module)
    monkeypatch.setattr(trial, "BASE", tmp_path / "controls")
    trial.register()
    for arm in ("hidden-candidate-1", "clean-candidate-1"):
        trial.prepare(arm)
        root = trial.BASE / arm
        request = read(root / ".agent/request.json")
        config = read(root / ".agent/config.json")
        archive = (
            root / ".agent/tasks" / request["task_id"] / "runs" / request["run_id"]
        )
        assert read(archive / "completed.json")["coder_invoked"] is False
        assert (
            read(archive / "validation.json")["focused_tests"]["junit"]["executed"]
            == 18
        )
        assert len(read(archive / "validation.json")["configured_checks"]) == 3
        assert read(root / ".agent/oracle-1.json")["exit"] == int(
            arm.startswith("hidden")
        )
        assert not (root / "reference/upstream").exists()
        spec = importlib.util.spec_from_file_location(
            "protocol_reference_actual_reviewer",
            trial.SNAPSHOT / ".local-agents/reviewer-runtime.py",
        )
        reviewer = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reviewer
        spec.loader.exec_module(reviewer)
        runtime = reviewer.ReviewerRuntime(root, request, config, None)
        runtime.prepare()
        observed = runtime.read_file({"path": "reference/awaitable_protocol.txt"})
        assert "B.__dict__[method] is None" in observed["content"]
        with pytest.raises(reviewer.ReviewError, match="outside review read scope"):
            runtime._assert_read_allowed("reference/upstream/inspect.py")
        verify_hashes(root, read(root / ".agent/freeze.json")["files"])
        with pytest.raises(FileExistsError):
            trial.prepare(arm)
    with pytest.raises(FileExistsError):
        trial.register()
