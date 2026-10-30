import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_evidence_catalog_adapter import EvidenceCatalog, install
from reviewer_evidence_catalog_adapter_v2 import install as install_v2


def test_catalog_only_observed_lines_preserves_gaps_and_never_extends_twenty_lines():
    catalog = EvidenceCatalog()
    ledger = {"source": set(range(1, 24)) | {40, 41}}
    hashes = {"source": "actual hash"}
    added = catalog.observe(ledger, hashes)
    assert [(entry["start_line"], entry["end_line"]) for entry in added] == [
        (1, 20),
        (21, 23),
        (40, 41),
    ]
    assert catalog.observe(ledger, hashes) == []
    assert catalog.refs(["E2", "E3"], ledger, hashes) == [
        {"path": "source", "start_line": 21, "end_line": 23},
        {"path": "source", "start_line": 40, "end_line": 41},
    ]


@pytest.mark.parametrize(
    "ids", [[], ["E1"] * 2, ["E1"] * 4, "E1", [True], ["invented"]]
)
def test_catalog_rejects_invalid_or_invented_handles(ids):
    catalog = EvidenceCatalog()
    catalog.observe({"source": {1}}, {"source": "hash"})
    with pytest.raises(ValueError):
        catalog.refs(ids, {"source": {1}}, {"source": "hash"})


def test_catalog_rejects_stale_or_no_longer_observed_ranges():
    catalog = EvidenceCatalog()
    catalog.observe({"source": {1, 2}}, {"source": "old"})
    with pytest.raises(ValueError, match="stale"):
        catalog.refs(["E1"], {"source": {1, 2}}, {"source": "new"})
    with pytest.raises(ValueError, match="unread"):
        catalog.refs(["E1"], {"source": {1}}, {"source": "old"})


@pytest.mark.parametrize("installer", [install, install_v2])
def test_catalog_transport_preserves_real_runtime_contract_and_read_gates(
    tmp_path, installer
):
    source = (
        Path(__file__).resolve().parents[1]
        / ".local-agents/tests/test_reviewer_runtime.py"
    )
    spec = importlib.util.spec_from_file_location("catalog_actual_runtime_test", source)
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    reviewer = tests.REVIEWER
    installer(reviewer)
    fixture = tests.ReviewerRuntimeTests()
    runtime = reviewer.ReviewerRuntime(
        tmp_path, fixture.make_run(tmp_path, risk="high"), {}, tests.FakeClient([])
    )
    before = dict(runtime.read_lines)
    with pytest.raises(reviewer.ReviewError, match="unknown"):
        runtime.validate_report(
            {
                "contract_review": [
                    {
                        "obligation_id": "behavior-1",
                        "status": "verified",
                        "source_evidence_ids": ["E1"],
                        "evidence": "not yet read",
                    }
                ]
            }
        )
    assert runtime.read_lines == before
    observed = runtime.read_file({"path": "src/example.py"})
    assert observed["new_source_evidence"][0]["id"] == "E1"
    runtime.read_file({"path": "tests/test_example.py"})
    arguments = {
        "decision": "pass_to_primary",
        "findings": [],
        "verified_contract_ids": ["behavior-1"],
        "unverified_claims": [],
        "contract_review": [
            {
                "obligation_id": "behavior-1",
                "status": "verified",
                "source_evidence_ids": ["E1"],
                "evidence": "Read implementation sets VALUE to 2.",
            }
        ],
    }
    result = runtime.validate_report(arguments)
    assert result["contract_review"][0]["canonical_quote"] == "VALUE = 2"
    assert arguments["contract_review"][0]["source_evidence_ids"] == ["E1"]
    arguments["contract_review"][0]["source_ref"] = {
        "path": "src/example.py",
        "start_line": 1,
        "end_line": 1,
    }
    with pytest.raises(reviewer.ReviewError, match="mixed legacy"):
        runtime.validate_report(arguments)
    arguments["contract_review"][0].pop("source_ref")
    arguments["contract_review"][0]["status"] = "violated"
    with pytest.raises(
        reviewer.ReviewError, match="contradicts|source-backed contract_review"
    ):
        runtime.validate_report(arguments)
    (tmp_path / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        runtime.validate_report(arguments)
