"""Setup must preserve existing work and never qualify drift or a stopped model."""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "strata_setup", Path(__file__).parents[1] / "tools/strata-setup.py"
)
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)


def archive(path, files):
    with zipfile.ZipFile(path, "x") as z:
        for name, raw in files.items():
            z.writestr(name, raw)
    return s.sha(path)


def material():
    raw = b"reviewed bytes"
    return {
        "file.py": raw,
        "manifest.json": json.dumps({"file.py": s.digest(raw)}).encode(),
    }


def test_unpack_checksum_and_exact_manifest(tmp_path):
    z = tmp_path / "bundle.zip"
    digest = archive(z, material())
    assert s.unpack(z, digest, tmp_path / "bundle")["status"] == "VERIFIED_BUNDLE"
    assert s.verify_bundle(tmp_path / "bundle")["file.py"] == s.digest(
        b"reviewed bytes"
    )
    with pytest.raises(FileExistsError):
        s.unpack(z, digest, tmp_path / "bundle")


@pytest.mark.parametrize(
    "case",
    ["checksum", "hash", "extra", "traversal", "casecollision", "backslash", "device"],
)
def test_invalid_archive_never_creates_destination(tmp_path, case):
    files = material()
    if case == "hash":
        files["file.py"] = b"changed"
    elif case == "extra":
        files["untrusted.py"] = b"extra"
    elif case in {"traversal", "casecollision", "backslash", "device"}:
        name = {
            "traversal": "../escape.py",
            "casecollision": "FILE.py",
            "backslash": "x\\y.py",
            "device": "CON.py",
        }[case]
        files[name] = b"bad"
    z = tmp_path / "bad.zip"
    digest = archive(z, files)
    with pytest.raises(s.SetupError):
        s.unpack(z, "0" * 64 if case == "checksum" else digest, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_bundle_rejects_extra_and_changed_files(tmp_path):
    z = tmp_path / "bundle.zip"
    digest = archive(z, material())
    s.unpack(z, digest, tmp_path / "bundle")
    (tmp_path / "bundle/file.py").write_bytes(b"changed")
    with pytest.raises(s.SetupError, match="drift"):
        s.verify_bundle(tmp_path / "bundle")


@pytest.mark.parametrize(
    "name", ["..", "/root", "x:stream", "x/../y", "AUX.txt", "x. "]
)
def test_unsafe_project_paths(name):
    with pytest.raises(s.SetupError):
        s.safe_name(name)


def test_checks_require_full_reviewed_map_and_no_fixes(tmp_path):
    (tmp_path / "tests").mkdir()
    spec = {
        "input_roots": ["tests"],
        "focused_tests": ["tests"],
        "commands": [
            {"id": "lint", "argv": ["{python}", "-m", "ruff", "check", "tests"]}
        ],
    }
    with pytest.raises(s.SetupError, match="must not modify"):
        s.check_spec(spec, tmp_path, __file__)
    spec["commands"][0]["argv"].append("--no-fix")
    assert s.check_spec(spec, tmp_path, __file__) == spec
    spec["commands"][0]["argv"].append("--fix")
    with pytest.raises(s.SetupError, match="Mutating"):
        s.check_spec(spec, tmp_path, __file__)


def test_guidance_appends_once_and_preserves_original(tmp_path):
    project, bundle = tmp_path / "p", tmp_path / "b"
    project.mkdir()
    bundle.mkdir()
    out = project / ".agent/strata-setup/first"
    out.mkdir(parents=True)
    original = b"# existing\r\nuser changes\r\n"
    (project / "AGENTS.md").write_bytes(original)
    s.guidance(bundle, project, out)
    expected = (project / "AGENTS.md").read_bytes()
    assert expected.startswith(original)
    assert (out / "AGENTS.preimage.bin").read_bytes() == original
    s.guidance(bundle, project, out)
    assert (project / "AGENTS.md").read_bytes() == expected


def test_inventory_catches_creation(tmp_path):
    (tmp_path / "src").mkdir()
    before = s.inventory(tmp_path, ["src"])
    (tmp_path / "src/new.py").write_text("pass")
    assert before != s.inventory(tmp_path, ["src"])


@pytest.mark.parametrize("entry", ["harness/lib/bin.js", "harness/apps/cli/lib/bin.js"])
def test_discover_installed_and_checkout_layout(tmp_path, entry):
    for name in ("node/node.exe", "control/python/python.exe", entry):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    assert s.discover(tmp_path) == tmp_path.resolve()


def test_tokenizer_discovery_uses_existing_instance_not_default(tmp_path, monkeypatch):
    monkeypatch.setattr(s.Path, "home", lambda: tmp_path)
    actual = tmp_path / "nondefault models/tokenizer"
    actual.mkdir(parents=True)
    for name in (
        "chat_template.jinja",
        "merges.txt",
        "tokenizer.json",
        "token_type.json",
        "vocab.json",
    ):
        (actual / name).write_text("fixture")
    instances = tmp_path / ".strata/data/native-instances"
    instances.mkdir(parents=True)
    (instances / "fixture.json").write_text(
        json.dumps({"aliases": ["iq3_s"], "tokenizer": str(actual)})
    )
    assert s.discover_tokenizer() == actual.resolve()


def test_unsupported_release_does_not_install(tmp_path):
    bundle = tmp_path / "b"
    project = tmp_path / "p"
    bundle.mkdir()
    project.mkdir()
    (bundle / "file.py").write_bytes(b"old")
    (bundle / "manifest.json").write_text(json.dumps({"file.py": s.digest(b"old")}))
    with pytest.raises(s.SetupError, match="UNSUPPORTED_RELEASE"):
        s.install(bundle, project)
    assert not (project / ".local-agents").exists()


@pytest.fixture
def setup_project(tmp_path, monkeypatch):
    home = tmp_path / "home"
    strata = tmp_path / "Strata"
    project = tmp_path / "project"
    bundle = tmp_path / "bundle"
    project.mkdir()
    (project / "tests").mkdir()
    (project / "tests/test_x.py").write_text("pass")
    (bundle / "examples").mkdir(parents=True)
    (bundle / "examples/config.coding.json").write_text("{}")
    for name in (
        "serve/server.py",
        "serve/frontend.py",
        "tools/strata_tokenizer.py",
        "python/python.exe",
    ):
        path = strata / "control" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    tokenizer = home / "Documents/Strata/packs/iq3_s/tokenizer"
    tokenizer.mkdir(parents=True)
    for name in (
        "chat_template.jinja",
        "merges.txt",
        "tokenizer.json",
        "token_type.json",
        "vocab.json",
    ):
        (tokenizer / name).write_text("fixture")
    monkeypatch.setattr(s.Path, "home", lambda: home)
    monkeypatch.setattr(s, "discover", lambda _: strata)
    monkeypatch.setattr(s, "install", lambda *_: {"status": "INSTALLED"})
    checks = {
        "input_roots": ["tests"],
        "focused_tests": ["tests"],
        "commands": [{"id": "tests", "argv": ["{python}", "-m", "pytest", "tests"]}],
    }
    return bundle, project, __file__, checks


def test_service_off_never_qualifies_config(setup_project, monkeypatch):
    calls = []
    monkeypatch.setattr(
        s,
        "run",
        lambda *args: calls.append(args) or (2, b'{"status":"unavailable"}', b""),
    )
    result = s.configure(*setup_project)
    assert result["status"] == "WAITING_FOR_STRATA" and result["ready"] is False
    assert len(calls) == 1
    out = Path(result["directory"])
    assert (out / "config.pending.json").exists()
    assert not (out / "config.json").exists()


def test_counter_mismatch_never_qualifies_config(setup_project, monkeypatch):
    monkeypatch.setattr(
        s,
        "run",
        lambda *_: (
            0,
            b'{"status":"ready","resident":{"status":"ready","model":"iq3_s","parallel":1,"context":65536}}',
            b"",
        ),
    )

    def reject(*_):
        raise s.SetupError("Counter/server mismatch")

    monkeypatch.setattr(s, "calibrate", reject)
    with pytest.raises(s.SetupError, match="mismatch"):
        s.configure(*setup_project)
    assert not (s.LAST_ATTEMPT / "config.json").exists()


@pytest.mark.parametrize("failure", ["failed-check", "input-creation", "counter-drift"])
def test_baseline_failure_or_mutation_never_qualifies(
    setup_project, monkeypatch, failure
):
    calls = []

    def command(*_):
        calls.append(1)
        if len(calls) == 1:
            return (
                0,
                b'{"status":"ready","resident":{"status":"ready","model":"iq3_s","parallel":1,"context":65536}}',
                b"",
            )
        if failure == "input-creation":
            (setup_project[1] / "tests/new.py").write_text("unexpected")
            return 0, b"", b""
        if failure == "counter-drift":
            (setup_project[1].parent / "Strata/control/serve/server.py").write_bytes(
                b"new version"
            )
            return 0, b"", b""
        return 1, b"failed baseline", b""

    monkeypatch.setattr(s, "run", command)
    monkeypatch.setattr(s, "calibrate", lambda *_: {"status": "PASS"})
    with pytest.raises(s.SetupError, match="baseline"):
        s.configure(*setup_project)
    assert not (s.LAST_ATTEMPT / "config.json").exists()
