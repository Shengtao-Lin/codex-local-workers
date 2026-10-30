import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_dependency_evidence_adapter import install
from test_reviewer_staged_assessment_adapter import assessment, fixture_runtime


def make_runtime(root, *, risk="high"):
    reviewer, runtime = fixture_runtime(root, install_adapter=install, risk=risk)
    (root / "src/dependency.py").write_text("COPY = 1\nRUN = 2\n", encoding="utf-8")
    runtime.config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "behavior-1",
            "path": "src/dependency.py",
            "anchors": ["COPY", "RUN"],
        }
    ]
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    return reviewer, runtime


def report(status="verified"):
    return {
        "decision": "escalate",
        "findings": [],
        "verified_contract_ids": [],
        "unverified_claims": [],
        "contract_review": [assessment(status)["assessment"]],
    }


def test_verified_claim_requires_actual_dependency_quote_not_path_hint(tmp_path):
    reviewer, runtime = make_runtime(tmp_path)
    args = report()
    with pytest.raises(reviewer.ReviewError, match="dependency evidence missing"):
        runtime.validate_report(args)
    assert "src/dependency.py" not in runtime.read_paths
    repair = runtime.report_repair(
        "dependency evidence missing for behavior-1: src/dependency.py", args
    )
    assert repair["suggested_action"]["arguments"]["path"] == "src/dependency.py"
    assert "src/dependency.py" not in runtime.read_paths
    entry = args["contract_review"][0]
    entry["source_refs"] = [
        entry.pop("source_ref"),
        {"path": "src/dependency.py", "start_line": 1, "end_line": 2},
    ]
    with pytest.raises(reviewer.ReviewError, match="not read"):
        runtime.validate_report(args)
    runtime.read_file({"path": "src/dependency.py"})
    assert runtime.validate_report(args)["contract_review"][0]["status"] == "verified"
    original = copy.deepcopy(args)
    entry["source_refs"][1]["end_line"] = 1
    with pytest.raises(reviewer.ReviewError, match="dependency evidence missing"):
        runtime.validate_report(args)
    (tmp_path / "src/dependency.py").write_text("COPY = 3\nRUN = 4\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        runtime.validate_report(original)


def test_uncertainty_remains_legal_without_dependency_truth_claim(tmp_path):
    _, runtime = make_runtime(tmp_path)
    assert runtime.validate_report(report("uncertain"))["decision"] == "escalate"
    assert "src/dependency.py" not in runtime.read_paths


def test_dependency_rule_cannot_expand_packet_scope(tmp_path):
    reviewer, runtime = make_runtime(tmp_path)
    runtime.config["reviewer_dependency_evidence"][0]["path"] = ".agent/private.py"
    with pytest.raises(reviewer.ReviewError, match="forbidden|scope|excluded"):
        runtime.system_prompt()


def test_declared_rule_cannot_be_skipped_via_small_optional_contract_review(tmp_path):
    reviewer, runtime = make_runtime(tmp_path, risk="small")
    args = {
        "decision": "pass_to_primary",
        "findings": [],
        "verified_contract_ids": ["behavior-1"],
        "unverified_claims": [],
    }
    with pytest.raises(reviewer.ReviewError, match="dependency evidence missing"):
        runtime.validate_report(args)


def test_staged_missing_dependency_never_records_and_final_rechecks(tmp_path):
    from reviewer_range_staged_adapter import install as install_range
    from test_reviewer_staged_assessment_adapter import final_report

    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=install_range)
    (tmp_path / "src/dependency.py").write_text("COPY = 1\nRUN = 2\n", encoding="utf-8")
    runtime.config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "behavior-1",
            "path": "src/dependency.py",
            "anchors": ["COPY", "RUN"],
        }
    ]
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    with pytest.raises(reviewer.ReviewError, match="dependency evidence missing"):
        runtime.validate_report(assessment())
    assert not runtime.staged_assessments
    assert not list(runtime.review_root.glob("assessment-*.json"))
    runtime.read_file({"path": "src/dependency.py"})
    args = assessment()
    entry = args["assessment"]
    entry["source_refs"] = [
        entry.pop("source_ref"),
        {"path": "src/dependency.py", "start_line": 1, "end_line": 2},
    ]
    runtime.validate_report(args)
    assert runtime.validate_report(final_report())["decision"] == "pass_to_primary"
    runtime.staged_assessments["behavior-1"]["entry"]["source_refs"].pop()
    with pytest.raises(reviewer.ReviewError, match="dependency evidence missing"):
        runtime.validate_report(final_report())
