import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_staged_final_gate_adapter import final_phase, install
from test_reviewer_staged_assessment_adapter import (
    assessment,
    final_report,
    fixture_runtime,
)


@pytest.mark.parametrize(
    "action", ["read_file", "search", "run_approved_test", "run_approved_static_check"]
)
def test_final_phase_rejects_other_actions_without_execution(tmp_path, action):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=install)
    runtime.read_file({"path": "src/example.py"})
    runtime.validate_report(assessment())
    assert not final_phase(runtime)  # Mandatory focused-test read is still permitted.
    runtime.read_file({"path": "tests/test_example.py"})
    assert final_phase(runtime)
    before = copy.deepcopy(runtime.read_lines)
    with pytest.raises(reviewer.ReviewError, match="final phase permits only"):
        getattr(runtime, action)({})
    assert runtime.read_lines == before
    assert not runtime.approved_execution
    with pytest.raises(reviewer.ReviewError, match="final phase permits only"):
        runtime.validate_report(assessment())
    assert not (runtime.review_root / "completed.json").exists()
    assert runtime.validate_report(final_report())["decision"] == "pass_to_primary"


def test_mandatory_search_and_execution_are_not_blocked_early(tmp_path):
    _, runtime = fixture_runtime(tmp_path, install_adapter=install)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    runtime.validate_report(assessment())
    runtime.config["reviewer_require_search"] = True
    assert not final_phase(runtime)
    runtime.search({"query": "VALUE", "paths": ["src/example.py"]})
    assert final_phase(runtime)
    runtime.config["reviewer_require_approved_execution"] = True
    runtime.validation["configured_checks"] = [{"id": "check-one", "status": "passed"}]
    assert not final_phase(runtime)
    runtime.approved_execution.append(
        {"kind": "test", "id": "focused-tests", "status": "passed"}
    )
    assert not final_phase(runtime)
    runtime.approved_execution.append(
        {"kind": "static_check", "id": "check-one", "status": "failed"}
    )
    assert not final_phase(runtime)
    runtime.approved_execution.append(
        {"kind": "static_check", "id": "check-one", "status": "passed"}
    )
    assert final_phase(runtime)


@pytest.mark.parametrize("decision", ["rework", "escalate"])
def test_final_phase_never_forces_pass_or_relabels_uncertainty(tmp_path, decision):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=install)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    runtime.validate_report(assessment("uncertain"))
    assert final_phase(runtime)
    with pytest.raises(reviewer.ReviewError, match="source-backed|contradicts"):
        runtime.validate_report(final_report())
    args = final_report()
    args.update(decision=decision, verified_contract_ids=[])
    if decision == "rework":
        args["findings"] = [
            {
                "id": "gap",
                "severity": "medium",
                "category": "test_gap",
                "path": "src/example.py",
                "line": 1,
                "evidence": "Source assignment alone is insufficient evidence for the boundary.",
                "contract_id": "behavior-1",
                "suggested_fix": "Primary should review the boundary contract.",
            }
        ]
    assert runtime.validate_report(args)["decision"] == decision


def test_actual_loop_narrows_native_schema_and_rejects_plain_action_bypass(tmp_path):
    reviewer, runtime = fixture_runtime(
        tmp_path, prepare=False, install_adapter=install
    )
    tools = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    runtime.client.native_tools = tools
    actions = iter(
        [
            {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
            {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
            {"action": "REPORT", "arguments": assessment()},
            {"action": "SEARCH", "arguments": {"query": "VALUE"}},
            {"action": "REPORT", "arguments": final_report()},
        ]
    )
    schemas = []

    def complete(messages):
        schemas.append(copy.deepcopy(runtime.client.native_tools))
        return json.dumps(next(actions))

    runtime.client.complete = complete
    report = runtime.run()
    assert report["decision"] == "pass_to_primary"
    assert runtime.protocol_errors == 1
    assert runtime.search_count == 0
    assert [item["function"]["name"] for item in schemas[-1]] == ["REPORT"]
    schema = schemas[-1][0]["function"]["parameters"]
    assert schema["properties"]["stage"]["enum"] == ["final"]
    assert "decision" in schema["required"]
    assert runtime.client.native_tools == tools
    assert runtime.client.complete == complete
    prompt = runtime.system_prompt()
    assert "REPORT arguments: decision" not in prompt
    assert "automatic" not in report["decision"]
