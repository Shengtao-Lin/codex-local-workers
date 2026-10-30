import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_protected_manifest import ProtectedManifestEvidence


def fixture(tmp_path, paths=None, identity=None):
    paths = paths or ["src/dependency.py", "pyproject.toml"]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("protected", encoding="utf-8")
    ident = {"task_id": "t", "unit_id": "u", "run_id": "r"}
    raw = json.dumps({"source_paths": paths, "identity": identity or ident}).encode()
    policy = tmp_path / "acceptance/capture-policy.json"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_bytes(raw)
    r = SimpleNamespace(
        packet=ident,
        config={"experimental_capture_policy_sha256": hashlib.sha256(raw).hexdigest()},
        ledger={},
    )
    r.editor = SimpleNamespace(
        read_bytes=lambda name: ((tmp_path / name).read_bytes(), "hash")
    )
    r._assert_read_allowed = lambda name: (name, tmp_path / name)
    return r


def build(runtime):
    return ProtectedManifestEvidence(
        runtime, policy_error=PermissionError, progress_error=RuntimeError
    )


def test_pool_is_prepared_sources_not_old_four_hints(tmp_path):
    r = fixture(tmp_path)
    r.config["experimental_evidence_files"] = ["unrelated"]
    assert build(r).paths == ["pyproject.toml", "src/dependency.py"]


def test_missing_or_changed_preparation_policy_fails_closed(tmp_path):
    r = fixture(tmp_path)
    r.config["experimental_capture_policy_sha256"] = "wrong"
    with pytest.raises(PermissionError, match="differs"):
        build(r)


def test_other_run_manifest_cannot_expand_evidence(tmp_path):
    with pytest.raises(PermissionError, match="identity"):
        build(fixture(tmp_path, identity={"task_id": "forged"}))


def test_packet_scope_still_overrides_prepared_list(tmp_path):
    r = fixture(tmp_path)

    def deny(name):
        raise PermissionError("packet denied")

    r._assert_read_allowed = deny
    with pytest.raises(PermissionError, match="packet denied"):
        build(r)


def test_unlisted_file_even_in_readable_root_still_denied(tmp_path):
    e = build(fixture(tmp_path))
    (tmp_path / "src/unlisted.py").write_text("not approved", encoding="utf-8")
    with pytest.raises(PermissionError, match="outside"):
        e.check_path("src/unlisted.py")


def test_more_than_thirty_frozen_files_allowed_but_no_new_actions(tmp_path):
    e = build(fixture(tmp_path, paths=[f"src/file{i}.py" for i in range(40)]))
    assert len(e.paths) == 40 and e.runtime.ledger["evidence_actions"] == 0
    e.runtime.ledger["evidence_actions"] = 4
    with pytest.raises(RuntimeError, match="exhausted"):
        e.perform({"search": {"path": "src", "query": "x"}})
