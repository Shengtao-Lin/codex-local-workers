"""Explicit manifest hashing controls; not a canonical provenance claim."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_capture_envelope import CaptureRejected, source_manifest


def test_stable_sorted_manifest_and_source_drift(tmp_path):
    (tmp_path / "source.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "profile.json").write_text("{}", encoding="utf-8")
    paths = ["source.py", "profile.json"]
    first = source_manifest(tmp_path, paths, approved_paths=paths)
    assert first == source_manifest(
        tmp_path, list(reversed(paths)), approved_paths=paths
    )
    (tmp_path / "source.py").write_text("x = 2\n", encoding="utf-8")
    assert (
        first["sha256"]
        != source_manifest(tmp_path, paths, approved_paths=paths)["sha256"]
    )


@pytest.mark.parametrize(
    "name",
    [
        "../outside.py",
        "/absolute.py",
        "C:/outside.py",
        "dir\\file.py",
        "./source.py",
        "dir//source.py",
        "missing.py",
        "",
        ".",
    ],
)
def test_bad_paths(tmp_path, name):
    with pytest.raises(CaptureRejected):
        source_manifest(tmp_path, [name], approved_paths=[name])


def test_scope_and_case_alias(tmp_path):
    (tmp_path / "source.py").write_text("x = 1", encoding="utf-8")
    with pytest.raises(CaptureRejected):
        source_manifest(tmp_path, ["source.py"], approved_paths=[])
    for names in (["source.py", "source.py"], ["source.py", "SOURCE.py"]):
        with pytest.raises(CaptureRejected):
            source_manifest(tmp_path, names, approved_paths=names)


def test_reparse_rejected_without_requiring_symlink_privilege(tmp_path, monkeypatch):
    (tmp_path / "source.py").write_text("x = 1", encoding="utf-8")
    original = Path.lstat

    def flagged(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path.name != "source.py":
            return info
        from types import SimpleNamespace

        return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)

    monkeypatch.setattr(Path, "lstat", flagged)
    with pytest.raises(CaptureRejected, match="reparse"):
        source_manifest(tmp_path, ["source.py"], approved_paths=["source.py"])
