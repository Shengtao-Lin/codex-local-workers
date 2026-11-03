"""Candidate packaging must preserve provenance and existing output."""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "supervised_package",
    Path(__file__).parents[1] / "tools/package-strata-supervised.py",
)
packager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packager)


@pytest.fixture
def source(tmp_path, monkeypatch):
    base = tmp_path / "frozen"
    base.mkdir()
    raw = b"frozen runtime bytes\n"
    (base / "runtime.py").write_bytes(raw)
    (base / "manifest.json").write_text(
        json.dumps({"runtime.py": packager.digest(raw)}), encoding="utf-8"
    )
    monkeypatch.setattr(packager, "BASE", base)
    return base


def test_bundle_preserves_frozen_bytes_and_support_is_manifested(source, tmp_path):
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    result = packager.package(tmp_path / "candidate")
    with zipfile.ZipFile(result["archive"]) as bundle:
        pins = json.loads(bundle.read("manifest.json"))
        assert bundle.read("runtime.py") == before["runtime.py"]
        assert "AGENTS.strata.md" in pins
        assert "tools/prepare-strata-return.py" in pins
        assert "tools/strata-setup.py" in pins
        assert "SETUP.md" in pins
        assert bundle.read("VERSION").decode().strip() == "0.3.0-supervised.2"
        metadata = json.loads(bundle.read("release-evidence.json"))
        assert metadata["version"] == "0.3.0-supervised.2"
        assert metadata["production_enabled"] is False
        assert (
            "remote"
            in metadata["qualification_details"]["remote_release_installation"].lower()
            or "pending"
            in metadata["qualification_details"]["remote_release_installation"].lower()
        )
        assert "skills/trace-behavior/SKILL.md" in pins
        assert "examples/config.investigation-followup.json" in pins
        assert not any(n.startswith(("benchmarks/", ".agent/", ".git/")) for n in pins)
        assert all(
            packager.digest(bundle.read(n)) == digest for n, digest in pins.items()
        )
    assert {p.name: p.read_bytes() for p in source.iterdir()} == before


@pytest.mark.parametrize("existing", ["folder", "zip"])
def test_existing_outputs_are_never_merged_or_overwritten(source, tmp_path, existing):
    dest = tmp_path / "candidate"
    if existing == "folder":
        dest.mkdir()
        preserved = dest / "prior.txt"
    else:
        preserved = tmp_path / "candidate.zip"
    preserved.write_bytes(b"existing material")
    with pytest.raises(FileExistsError):
        packager.package(dest)
    assert preserved.read_bytes() == b"existing material"


def test_runtime_drift_rejected_before_creating_output(source, tmp_path):
    (source / "runtime.py").write_bytes(b"changed")
    dest = tmp_path / "candidate"
    with pytest.raises(ValueError, match="drift"):
        packager.package(dest)
    assert not dest.exists() and not dest.with_suffix(".zip").exists()


def test_path_escape_in_source_manifest_rejected(source, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside")
    (source / "manifest.json").write_text(
        json.dumps({"../outside.txt": packager.digest(b"outside")}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Invalid frozen path"):
        packager.package(tmp_path / "candidate")


def test_identical_inputs_produce_byte_identical_archives(source, tmp_path):
    first = packager.package(tmp_path / "one")
    second = packager.package(tmp_path / "two")
    assert Path(first["archive"]).read_bytes() == Path(second["archive"]).read_bytes()
    assert first["sha256"] == second["sha256"]
