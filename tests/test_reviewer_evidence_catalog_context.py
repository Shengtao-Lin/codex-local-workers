import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_evidence_catalog_adapter_v2 import install


def test_readable_context_outside_validation_inputs_is_hash_bound(tmp_path):
    source = (
        Path(__file__).resolve().parents[1]
        / ".local-agents/tests/test_reviewer_runtime.py"
    )
    spec = importlib.util.spec_from_file_location(
        "catalog_context_runtime_test", source
    )
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    reviewer = tests.REVIEWER
    install(reviewer)
    fixture = tests.ReviewerRuntimeTests()
    runtime = reviewer.ReviewerRuntime(
        tmp_path, fixture.make_run(tmp_path, risk="high"), {}, tests.FakeClient([])
    )
    reference = tmp_path / "src/reference.py"
    reference.write_text("REFERENCE = 1\n", encoding="utf-8")
    assert "src/reference.py" not in runtime.expected_inputs
    observed = runtime.read_file({"path": "src/reference.py"})
    entry = observed["new_source_evidence"][0]
    assert entry["path"] == "src/reference.py"
    assert runtime.read_lines["src/reference.py"] == {1}
    reference.write_text("REFERENCE = 2\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        runtime.validate_report(
            {
                "contract_review": [
                    {
                        "obligation_id": "behavior-1",
                        "status": "verified",
                        "source_evidence_ids": [entry["id"]],
                        "evidence": "stale source",
                    }
                ]
            }
        )
    with pytest.raises(reviewer.ReviewError, match="changed"):
        runtime.read_file({"path": "src/example.py"})
    assert "src/example.py" not in runtime.read_lines
