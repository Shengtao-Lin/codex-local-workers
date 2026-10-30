"""Replay frozen controls from immutable initial bytes, not a mutated live tree."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_fixture_support as F
import unified_preparation_trial as TRIAL

OLD = F.load(
    Path(__file__).with_name("test_unified_preparation.py"), "frozen_unified_controls"
)


@pytest.mark.parametrize("tamper", ["none", "source"])
def test_immutable_preimage_replay(tmp_path, monkeypatch, tamper):
    manifest_path = TRIAL.BATCH / "cells.json"
    rows = TRIAL.T.read(manifest_path)
    row = rows["new-1"]
    live = Path(row["root"])
    archive = live / ".agent/tasks/fresh-metadata/runs/unified-new-1"
    preimages = {p["path"]: p for p in TRIAL.T.read(archive / "preimages.json")}
    pristine = tmp_path / "initial-snapshot"
    for relative, sha in row["files"].items():
        source = live / relative
        if TRIAL.T.sha(source) != sha:
            entry = preimages[relative]
            assert entry["sha256"] == sha
            source = live / entry["archive_path"]
        assert TRIAL.T.sha(source) == sha
        target = pristine / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    assert not (pristine / ".agent/tasks").exists()
    rows["new-1"] = {**row, "root": str(pristine)}
    original = TRIAL.T.read

    def read(path):
        return rows if Path(path) == manifest_path else original(path)

    monkeypatch.setattr(TRIAL.T, "read", read)
    OLD.test_real_repair_and_canonical_gate_with_one_formatter_three_checks(
        tmp_path, tamper
    )
