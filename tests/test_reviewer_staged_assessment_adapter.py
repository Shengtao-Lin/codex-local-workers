import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_staged_assessment_adapter import install


def fixture_runtime(root, *, prepare=True, install_adapter=install, risk="high"):
    source = (
        Path(__file__).resolve().parents[1]
        / ".local-agents/tests/test_reviewer_runtime.py"
    )
    spec = importlib.util.spec_from_file_location("staged_actual_runtime_test", source)
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    reviewer = tests.REVIEWER
    install_adapter(reviewer)
    fixture = tests.ReviewerRuntimeTests()
    runtime = reviewer.ReviewerRuntime(
        root,
        fixture.make_run(root, risk=risk),
        {"reviewer_require_source_and_test_reads": True},
        tests.FakeClient([]),
    )
    if prepare:
        runtime.prepare()
    return reviewer, runtime


def assessment(status="verified"):
    return {
        "stage": "assessment",
        "assessment": {
            "obligation_id": "behavior-1",
            "status": status,
            "source_ref": {"path": "src/example.py", "start_line": 1, "end_line": 1},
            "evidence": "Source assigns value two.",
        },
    }


def final_report():
    return {
        "stage": "final",
        "assessment_ids": ["behavior-1"],
        "decision": "pass_to_primary",
        "findings": [],
        "verified_contract_ids": ["behavior-1"],
        "unverified_claims": [],
    }


def test_partial_is_source_bound_immutable_and_never_acceptance(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path)
    proposal = assessment()
    with pytest.raises(reviewer.ReviewError, match="was not read"):
        runtime.validate_report(proposal)
    assert not runtime.staged_assessments
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    partial = runtime.validate_report(proposal)
    assert partial["decision"] == "escalate"
    assert runtime._prepass_challenge(partial)["provisional_only"]
    assert (runtime.review_root / "assessment-1.json").exists()
    assert not (runtime.review_root / "completed.json").exists()
    with pytest.raises(reviewer.ReviewError, match="cannot finalize"):
        runtime.finalize(partial)
    with pytest.raises(reviewer.ReviewError, match="already recorded"):
        runtime.validate_report(proposal)
    assert not (runtime.review_root / "assessment-2.json").exists()
    report = runtime.validate_report(final_report())
    assert report["contract_review"][0]["canonical_quote"] == "VALUE = 2"
    assert runtime._prepass_challenge(report) is None
    assert proposal == assessment()


@pytest.mark.parametrize("status", ["violated", "uncertain"])
def test_final_pass_cannot_overwrite_nonverified_assessment(tmp_path, status):
    reviewer, runtime = fixture_runtime(tmp_path)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    runtime.validate_report(assessment(status))
    with pytest.raises(reviewer.ReviewError, match="source-backed|contradicts"):
        runtime.validate_report(final_report())
    assert runtime.staged_assessments["behavior-1"]["entry"]["status"] == status


@pytest.mark.parametrize("ids", [[], ["unknown"], ["behavior-1", "behavior-1"], [True]])
def test_final_rejects_missing_unknown_duplicate_and_boolean_ids(tmp_path, ids):
    reviewer, runtime = fixture_runtime(tmp_path)
    args = final_report()
    args["assessment_ids"] = ids
    with pytest.raises(reviewer.ReviewError, match="obligation ID|recorded obligation"):
        runtime.validate_report(args)
    assert not (runtime.review_root / "completed.json").exists()


def test_final_revalidates_input_version_and_original_reads(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path)
    runtime.read_file({"path": "src/example.py"})
    runtime.validate_report(assessment())
    with pytest.raises(reviewer.ReviewError, match="focused test"):
        runtime.validate_report(final_report())
    runtime.read_file({"path": "tests/test_example.py"})
    (tmp_path / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        runtime.validate_report(final_report())


def test_model_cannot_inject_private_marker_or_replace_recorded_entry(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path)
    args = final_report()
    args["staged_assessment_id"] = "behavior-1"
    with pytest.raises(reviewer.ReviewError, match="final stage"):
        runtime.validate_report(args)
    args = copy.deepcopy(assessment())
    args["decision"] = "pass_to_primary"
    with pytest.raises(reviewer.ReviewError, match="assessment stage accepts only"):
        runtime.validate_report(args)


def test_final_cannot_discard_or_rewrite_recorded_findings(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    finding = {
        "id": "f1",
        "severity": "medium",
        "category": "test_gap",
        "path": "src/example.py",
        "line": 1,
        "evidence": "The source alone does not establish boundary behavior.",
        "contract_id": "behavior-1",
        "suggested_fix": "Add an independently reviewed boundary test.",
    }
    args = assessment("uncertain")
    args["findings"] = [finding]
    runtime.validate_report(args)
    discarded = final_report()
    discarded.update(decision="escalate", verified_contract_ids=[])
    with pytest.raises(reviewer.ReviewError, match="retain every recorded"):
        runtime.validate_report(discarded)
    final = final_report()
    final.update(decision="rework", assessment_ids=[], verified_contract_ids=[])
    rewritten = copy.deepcopy(finding)
    rewritten["evidence"] = "A different claim."
    final["findings"] = [rewritten]
    with pytest.raises(reviewer.ReviewError, match="retain every recorded"):
        runtime.validate_report(final)
    final["findings"] = [finding]
    assert runtime.validate_report(final)["decision"] == "rework"


def test_final_keeps_original_configured_check_gate(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    runtime.validate_report(assessment())
    runtime.validation["configured_checks"] = [{"id": "check-one", "status": "passed"}]
    with pytest.raises(reviewer.ReviewError, match="acknowledgement"):
        runtime.validate_report(final_report())
    final = final_report()
    final["verified_check_ids"] = ["check-one"]
    assert runtime.validate_report(final)["decision"] == "pass_to_primary"


def test_real_runtime_loop_preserves_provisional_then_final_handoff(tmp_path):
    _, runtime = fixture_runtime(tmp_path, prepare=False)
    actions = iter(
        [
            {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
            {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
            {"action": "REPORT", "arguments": assessment()},
            {"action": "REPORT", "arguments": final_report()},
        ]
    )
    messages_seen = []

    def complete(messages):
        messages_seen.append(messages)
        return json.dumps(next(actions))

    runtime.client.complete = complete
    result = runtime.run()
    assert result["decision"] == "pass_to_primary"
    assert (runtime.review_root / "assessment-1.json").exists()
    assert (runtime.review_root / "completed.json").exists()
    assert runtime.client.complete == complete
    last_state = json.loads(messages_seen[-1][-1]["content"].split("\n", 1)[1])
    assert last_state["provisional_only"]
    assert last_state["next_obligation"] is None
    assert last_state["assessments"][0]["id"] == "behavior-1"
