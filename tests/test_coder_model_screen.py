import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import coder_model_screen as screen  # noqa: E402
from coder_model_screen_audit import apply_complete_files  # noqa: E402


def test_complete_file_noop_does_not_dispatch_edit(tmp_path):
    (tmp_path / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b = 1\n", encoding="utf-8")
    edits = []

    class Runtime:
        def read_file(self, args):
            assert args["path"] == "b.py"
            return {"sha256": "observed-hash"}

        def safe_replace(self, args):
            edits.append(args)

    skipped = apply_complete_files(
        Runtime(),
        tmp_path,
        [
            {"path": "a.py", "content": "a = 1\n"},
            {"path": "b.py", "content": "b = 2\n"},
        ],
    )
    assert skipped == ["a.py"]
    assert len(edits) == 1
    assert edits[0]["expected_sha256"] == "observed-hash"


@pytest.mark.parametrize(
    "change", [{"status": "busy"}, {"queued": 1}, {"identifier": "foreign"}]
)
def test_reject_unsafe_switch(change):
    row = {"identifier": screen.MODELS[0], "status": "idle", "queued": 0}
    with pytest.raises(ValueError):
        screen.guard_residents([dict(row, **change)])
    with pytest.raises(ValueError):
        screen.guard_residents([row, row])


def test_empty_and_single_residency():
    screen.guard_residents([])
    with pytest.raises(ValueError):
        screen.guard_residents([], screen.MODELS[0])
    screen.guard_residents(
        [{"identifier": screen.MODELS[0], "status": "idle", "queued": 0}],
        screen.MODELS[0],
    )


@pytest.mark.parametrize(
    "change", [{"context_length": 4096}, {"parallel": 2}, {"flash_attention": False}]
)
def test_reject_loaded_config_drift(monkeypatch, change):
    config = dict(context_length=24576, parallel=1, flash_attention=True)
    config.update(change)
    monkeypatch.setattr(
        screen.FA,
        "api",
        lambda: {
            "models": [
                {"key": screen.MODELS[0], "loaded_instances": [{"config": config}]}
            ]
        },
    )
    with pytest.raises(ValueError):
        screen.loaded_config(screen.MODELS[0])
