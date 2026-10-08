import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import typed_counterexample_probe as probe  # noqa: E402


def test_failed_subclass_observation_retains_actual_type():
    value = probe.Child(1)
    result = probe.observe(
        lambda x: x, (value,), {"kind": "raise", "type": "ValueError"}
    )
    assert result["arguments"][0]["repr"] == "1"
    assert result["arguments"][0]["type"].endswith(".Child")
    assert result["actual"] == {"kind": "return", "repr": "1", "type": "Child"}


def test_observations_are_actual_and_correct_inputs_omitted():
    assert probe.observe(lambda x: x, (80,), {"kind": "return", "repr": "80"}) is None
    result = probe.observe(
        lambda x: int(x), ("８０",), {"kind": "raise", "type": "ValueError"}
    )
    assert result["actual"]["repr"] == "80"
    assert "８０" in result["arguments"][0]["repr"]


def test_window_probe_exercises_both_arguments(monkeypatch):
    calls = []

    def window(items, start, size):
        calls.append((start, size))
        return []

    monkeypatch.setattr(
        probe.importlib, "import_module", lambda name: SimpleNamespace(window=window)
    )
    result = probe.probe("window-bounds")
    assert result["observations_executed"] == 25
    assert any(type(start) is probe.Child for start, size in calls)
    assert any(type(size) is probe.Child for start, size in calls)
    assert result["counterexamples"]
