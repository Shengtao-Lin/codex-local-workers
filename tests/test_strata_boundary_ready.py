import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import strata_boundary_ready_trial as candidate


def test_prepare_creates_wire_directory_before_config_is_saved(tmp_path, monkeypatch):
    path = tmp_path / "isolated/.agent/config.json"
    seen = []

    def save(p, value):
        assert (path.parent / "strata-wire").is_dir()
        seen.append(value)

    monkeypatch.setattr(candidate.B, "save", save)
    candidate.save(path, {"model": "iq3_s"})
    assert seen == [{"model": "iq3_s"}]


def test_prepared_config_does_not_create_archive_in_protected_preparation(
    tmp_path, monkeypatch
):
    path = tmp_path / ".agent/prepared/id/config.json"
    monkeypatch.setattr(candidate.B, "save", lambda p, v: None)
    candidate.save(path, {})
    assert not (path.parent / "strata-wire").exists()
