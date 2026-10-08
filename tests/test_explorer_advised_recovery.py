"""Diagnostic orchestration must not turn an Explorer status into edit authority."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
SPEC = importlib.util.spec_from_file_location(
    "explorer_advice_test", BENCHMARKS / "explorer_advised_recovery.py"
)
EXPERIMENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPERIMENT)


@pytest.fixture
def experiment(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    snapshot = tmp_path / "snapshot"
    base = tmp_path / "cohort"
    (root / "src").mkdir(parents=True)
    (root / "src/target.py").write_text("value = 1\n", encoding="utf-8")
    EXPERIMENT.write(
        root / ".agent/fresh-context-a2.json",
        {"task_id": "task", "unit_id": "unit", "run_id": "task-a2"},
    )
    EXPERIMENT.write(root / ".agent/config.json", {"explorer_mode": "locate"})
    snapshot.mkdir()
    runtime = snapshot / "runtime.py"
    runtime.write_text("value = 1\n", encoding="utf-8")
    EXPERIMENT.write(
        snapshot / "freeze.json", {"files": {"runtime.py": EXPERIMENT.digest(runtime)}}
    )
    for name, value in (("ROOT", root), ("BASE", base), ("SNAPSHOT", snapshot)):
        monkeypatch.setattr(EXPERIMENT, name, value)
    EXPERIMENT.prepare()
    return root, snapshot, base


def test_prepare_preserves_parent_and_separates_diagnostic_mode(experiment):
    root, _, base = experiment
    assert EXPERIMENT.read(root / ".agent/config.json")["explorer_mode"] == "locate"
    assert (
        EXPERIMENT.read(base / "explorer-config.json")["explorer_mode"] == "investigate"
    )
    plan = EXPERIMENT.read(base / "plan.json")
    assert plan["max_calls"]["coder"] == 1
    assert plan["coordinator_started"] is False
    EXPERIMENT.check(plan)
    with pytest.raises(FileExistsError):
        EXPERIMENT.prepare()


@pytest.mark.parametrize("target", ["draft", "runtime", "config", "explorer_config"])
def test_input_drift_stops_before_model(experiment, target):
    root, snapshot, base = experiment
    paths = {
        "draft": root / "src/target.py",
        "runtime": snapshot / "runtime.py",
        "config": root / ".agent/config.json",
        "explorer_config": base / "explorer-config.json",
    }
    with paths[target].open("a", encoding="utf-8") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="drift"):
        EXPERIMENT.check(EXPERIMENT.read(base / "plan.json"))


def test_rejected_advice_cannot_launch_coder(experiment, monkeypatch):
    root, _, base = experiment
    EXPERIMENT.write(root / ".agent/explorer-advice-a3.json", {"status": "success"})
    EXPERIMENT.write(
        base / "primary-advice-review.json", {"decision": "reject_local_recommendation"}
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Rejected Explorer advice must not start any model or worker")

    monkeypatch.setattr(EXPERIMENT.subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="no accepted local recommendation"):
        EXPERIMENT.run("coder")
    assert not (base / "coder-started.json").exists()
    assert not (root / ".agent/explorer-advised-a3.json").exists()


def test_explorer_launch_is_single_and_task_attached(experiment, monkeypatch):
    root, snapshot, base = experiment
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="fake read-only report", stderr="")

    monkeypatch.setattr(EXPERIMENT.subprocess, "run", fake_run)
    EXPERIMENT.run("explorer")
    command, options = calls[0]
    assert command[1] == str(snapshot / ".local-agents/local-explore.py")
    assert command[command.index("--task-id") + 1] == "task"
    assert options["cwd"] == root
    assert (
        json.loads((base / "explorer-result.json").read_text())["primary_accepted"]
        is False
    )
    with pytest.raises(FileExistsError):
        EXPERIMENT.run("explorer")
    assert len(calls) == 1
