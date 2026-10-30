import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reviewer_catalog_staged_adapter import install as install_catalog
from reviewer_citation_bundle_adapter import candidates, decode
from reviewer_range_staged_adapter import install as install_range
from test_reviewer_staged_assessment_adapter import fixture_runtime


def combined(reviewer):
    install_range(reviewer)
    install_catalog(reviewer)


def test_bundles_require_read_application_and_declared_dependency(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    assert candidates(runtime) == []
    runtime.config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "behavior-1",
            "path": "tests/test_example.py",
            "anchors": ["assert"],
        }
    ]
    runtime.read_file({"path": "src/example.py"})
    assert candidates(runtime) == []
    runtime.read_file({"path": "tests/test_example.py"})
    ledger = copy.deepcopy(runtime.read_lines)
    options = candidates(runtime)
    assert options
    for option in options:
        refs = runtime.evidence_catalog.refs(
            option["source_evidence_ids"],
            runtime.read_lines,
            runtime.observed_read_hashes,
        )
        assert 1 <= len(refs) <= 3
        assert {ref["path"] for ref in refs} == {
            "src/example.py",
            "tests/test_example.py",
        }
        assert all(ref["end_line"] - ref["start_line"] < 20 for ref in refs)
        assert "status" not in option and "verified" not in option
    assert ledger == runtime.read_lines
    assert not runtime.staged_assessments
    (tmp_path / "tests/test_example.py").write_text("assert False\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        candidates(runtime)


@pytest.mark.parametrize("status", ["verified", "violated", "uncertain"])
def test_bundle_decode_only_transports_selected_existing_refs(tmp_path, status):
    _, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    runtime.read_file({"path": "src/example.py"})
    bundle = candidates(runtime)[0]
    original = {
        "action": "ASSESS_CONTRACT",
        "arguments": {
            "obligation_id": "behavior-1",
            "status": status,
            "citation_bundle_id": "B1",
            "evidence": "untrusted model claim",
            "findings": [{"id": "unchanged"}],
        },
    }
    raw = json.dumps(original)
    decoded = json.loads(decode(runtime, raw, {"B1": bundle}))
    assert decoded["arguments"]["status"] == status
    assert decoded["arguments"]["evidence"] == "untrusted model claim"
    assert decoded["arguments"]["findings"] == original["arguments"]["findings"]
    assert decoded["arguments"]["source_evidence_ids"] == bundle["source_evidence_ids"]
    assert "citation_bundle_id" not in decoded["arguments"]
    assert json.loads(raw) == original
    assert not runtime.staged_assessments
    for change in (
        {"citation_bundle_id": "unknown"},
        {"obligation_id": "wrong"},
        {"source_evidence_ids": bundle["source_evidence_ids"]},
    ):
        bad = copy.deepcopy(original)
        bad["arguments"].update(change)
        with pytest.raises(ValueError):
            decode(runtime, json.dumps(bad), {"B1": bundle})
