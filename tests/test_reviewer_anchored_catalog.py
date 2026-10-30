import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_anchored_catalog_adapter import AnchoredCatalog


def test_anchor_window_spans_chunk_boundary_but_never_unread_gap():
    catalog = AnchoredCatalog()
    ledger, hashes = {"src/example.py": set(range(1, 41))}, {"src/example.py": "v1"}
    catalog.observe(ledger, hashes)
    added = catalog.observe_anchors(
        ledger, hashes, "src/example.py", "19: def target():\n", ["def target"]
    )
    assert len(added) == 1
    assert (added[0]["start_line"], added[0]["end_line"]) == (19, 38)
    assert catalog.refs([added[0]["id"]], ledger, hashes)[0]["end_line"] == 38
    assert not catalog.observe_anchors(
        ledger, hashes, "src/example.py", "19: def target():\n", ["def target"]
    )
    ledger["src/example.py"].remove(25)
    with pytest.raises(ValueError, match="unread"):
        catalog.refs([added[0]["id"]], ledger, hashes)
    other = AnchoredCatalog()
    narrow = other.observe_anchors(
        ledger, hashes, "src/example.py", "19: def target():\n", ["def target"]
    )
    assert narrow[0]["end_line"] == 24


def test_anchor_metadata_is_not_read_evidence_or_semantic_truth():
    catalog = AnchoredCatalog()
    ledger, hashes = {"src/example.py": {1, 2}}, {"src/example.py": "v1"}
    assert not catalog.observe_anchors(
        ledger, hashes, "src/example.py", "3: target\n", ["target"]
    )
    assert not catalog.entries
    entry = catalog.observe_anchors(
        ledger, hashes, "src/example.py", "1: target\n", ["target"]
    )[0]
    assert "status" not in entry and "verified" not in entry
    assert ledger == {"src/example.py": {1, 2}}
    with pytest.raises(ValueError, match="stale"):
        catalog.refs([entry["id"]], ledger, {"src/example.py": "v2"})


def test_actual_reviewer_read_installs_catalog_without_fabricating_evidence(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from reviewer_anchored_catalog_adapter import install
    from reviewer_catalog_staged_adapter import install as install_catalog
    from reviewer_range_staged_adapter import install as install_range
    from test_reviewer_staged_assessment_adapter import fixture_runtime

    def combined(reviewer):
        install_range(reviewer)
        install_catalog(reviewer)
        install(reviewer)

    _, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    first = runtime.read_file({"path": "src/example.py"})
    assert first["content"].startswith("1:")
    assert isinstance(runtime.evidence_catalog, AnchoredCatalog)
    assert first["new_source_evidence"][0]["path"] == "src/example.py"
    before = dict(runtime.evidence_catalog.entries)
    second = runtime.read_file({"path": "src/example.py"})
    assert second["status"] == "already_read"
    assert second["new_source_evidence"] == []
    assert all(
        runtime.evidence_catalog.entries[key] == value for key, value in before.items()
    )
    # The existing runtime may supply an actually displayed protected-test read
    # inside a duplicate-source observation. It is not fabricated by this adapter.
    for entry in runtime.evidence_catalog.entries.values():
        assert (
            set(range(entry["start_line"], entry["end_line"] + 1))
            <= runtime.read_lines[entry["path"]]
        )
    assert [
        entry
        for entry in runtime.evidence_catalog.entries.values()
        if entry["path"] == "src/example.py"
    ] == list(before.values())
