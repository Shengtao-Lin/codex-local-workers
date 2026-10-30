import hashlib
import inspect
import json
from pathlib import Path


def test_capsule_matches_pinned_actual_stdlib_ranges_and_live_protocol_boundary():
    root = (
        Path(__file__).resolve().parents[1]
        / "benchmarks/fixtures/tool-library-reference-v2"
    )
    metadata = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    for name, expected in metadata["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
    source_paths = {
        Path(name).name: root / "upstream" / Path(name).name
        for name in metadata["source_files"]
    }
    capsule = (root / "awaitable_protocol.txt").read_text(encoding="utf-8")
    for item in metadata["ranges"]:
        lines = source_paths[item["source"]].read_text(encoding="utf-8").splitlines()
        assert "\n".join(lines[item["start_line"] - 1 : item["end_line"]]) in capsule

    class PlainMapping(dict):
        __await__ = None

    value = PlainMapping(value=7)
    assert hasattr(value, "__await__")
    assert not inspect.isawaitable(value)
