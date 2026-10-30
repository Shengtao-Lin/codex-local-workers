import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_fixture_origin as origin


def test_same_wrong_pair_is_rejected_even_when_pair_hashes_match(tmp_path):
    wanted = hashlib.sha256(b"frozen baseline").hexdigest()
    for arm in ("baseline", "candidate"):
        root = tmp_path / arm
        (root / "src").mkdir(parents=True)
        (root / "src/a.py").write_bytes(b"already repaired historical result")
        with pytest.raises(ValueError, match="upstream pre-run freeze"):
            origin.require_origin(root, {"src/a.py": wanted})
    assert origin.B.sha(tmp_path / "baseline/src/a.py") == origin.B.sha(tmp_path / "candidate/src/a.py")


def test_correct_origin_and_windows_manifest_paths(tmp_path):
    (tmp_path / "src").mkdir()
    path = tmp_path / "src/a.py"
    path.write_bytes(b"frozen baseline")
    origin.require_origin(tmp_path, {"src\\a.py": origin.B.sha(path), ".agent/packet.json": "identity is separately registered"})
    path.write_bytes(b"external change")
    with pytest.raises(ValueError):
        origin.require_origin(tmp_path, {"src/a.py": "old"})


def test_empty_origin_cannot_greenlight_a_fixture(tmp_path):
    with pytest.raises(ValueError, match="No source"):
        origin.require_origin(tmp_path, {".agent/config.json": "not source"})
