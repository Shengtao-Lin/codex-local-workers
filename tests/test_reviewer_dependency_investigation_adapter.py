import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reviewer_dependency_investigation_adapter import install
from test_reviewer_dependency_evidence_adapter import make_runtime, report


@pytest.mark.parametrize("status", ["verified", "uncertain", "violated"])
def test_unread_declared_dependency_is_not_a_verdict_or_observation(tmp_path, status):
    reviewer, runtime = make_runtime(tmp_path)
    install(reviewer)
    args = report(status)
    with pytest.raises(reviewer.ReviewError, match="investigation incomplete"):
        runtime.validate_report(args)
    repair = runtime.report_repair(
        "declared dependency investigation incomplete: src/dependency.py", args
    )
    assert repair["suggested_action"]["arguments"]["path"] == "src/dependency.py"
    assert "src/dependency.py" not in runtime.read_paths
    assert "src/dependency.py" not in runtime.observed_read_hashes
    runtime.read_file({"path": "src/dependency.py", "start_line": 1, "end_line": 1})
    with pytest.raises(reviewer.ReviewError, match="investigation incomplete"):
        runtime.validate_report(args)


def test_reading_dependency_leaves_uncertainty_legal_and_verified_quote_gate_intact(
    tmp_path,
):
    reviewer, runtime = make_runtime(tmp_path)
    install(reviewer)
    runtime.read_file({"path": "src/dependency.py"})
    with pytest.raises(reviewer.ReviewError, match="assessment citation missing"):
        runtime.validate_report(report("uncertain"))
    args = report("uncertain")
    entry = args["contract_review"][0]
    entry["source_refs"] = [
        entry.pop("source_ref"),
        {"path": "src/dependency.py", "start_line": 1, "end_line": 2},
    ]
    assert runtime.validate_report(args)["decision"] == "escalate"
    with pytest.raises(reviewer.ReviewError, match="assessment citation missing"):
        runtime.validate_report(report())
    (tmp_path / "src/dependency.py").write_text("COPY = 3\nRUN = 4\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        runtime.validate_report(report("uncertain"))


def test_pending_dependency_cannot_read_outside_packet_scope(tmp_path):
    reviewer, runtime = make_runtime(tmp_path)
    install(reviewer)
    runtime.config["reviewer_dependency_evidence"][0]["path"] = ".agent/private.py"
    with pytest.raises(reviewer.ReviewError, match="excluded|forbidden|scope"):
        runtime.validate_report(report("uncertain"))


def test_staged_uncertainty_cannot_record_without_dependency_but_remains_legal(
    tmp_path,
):
    from reviewer_range_staged_adapter import install as install_range
    from test_reviewer_staged_assessment_adapter import assessment, fixture_runtime

    def combined(reviewer):
        install_range(reviewer)
        install(reviewer)

    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    (tmp_path / "src/dependency.py").write_text("COPY = 1\nRUN = 2\n", encoding="utf-8")
    runtime.config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "behavior-1",
            "path": "src/dependency.py",
            "anchors": ["COPY", "RUN"],
        }
    ]
    runtime.read_file({"path": "src/example.py"})
    args = assessment("uncertain")
    with pytest.raises(reviewer.ReviewError, match="investigation incomplete"):
        runtime.validate_report(args)
    assert not runtime.staged_assessments
    assert not list(runtime.review_root.glob("assessment-*.json"))
    runtime.read_file({"path": "src/dependency.py"})
    with pytest.raises(reviewer.ReviewError, match="assessment citation missing"):
        runtime.validate_report(args)
    entry = args["assessment"]
    entry["source_refs"] = [
        entry.pop("source_ref"),
        {"path": "src/dependency.py", "start_line": 1, "end_line": 2},
    ]
    checked = runtime.validate_report(args)
    assert checked["contract_review"][0]["status"] == "uncertain"
    assert runtime.staged_assessments["behavior-1"]["entry"]["status"] == "uncertain"
