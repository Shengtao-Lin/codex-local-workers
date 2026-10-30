import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_split_staged_adapter import install, model_tools, route
from test_reviewer_staged_assessment_adapter import (
    assessment,
    final_report,
    fixture_runtime,
)


def test_external_tool_schemas_are_disjoint_and_internal_schema_unchanged(tmp_path):
    reviewer, _ = fixture_runtime(tmp_path, install_adapter=install)
    internal = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    tools = model_tools(internal, False)
    schemas = {
        item["function"]["name"]: item["function"]["parameters"] for item in tools
    }
    assert "obligation_id" in schemas["ASSESS_CONTRACT"]["properties"]
    assert "decision" not in schemas["ASSESS_CONTRACT"]["properties"]
    assert "assessment_ids" in schemas["REPORT"]["properties"]
    assert not {"stage", "assessment", "contract_review"} & set(
        schemas["REPORT"]["properties"]
    )
    assert "ASSESS_CONTRACT" not in {
        item["function"]["name"] for item in model_tools(internal, True)
    }
    assert internal == reviewer.REVIEW_NATIVE_TOOLS
    assert (
        "ASSESS_CONTRACT"
        in reviewer.REVIEW_ACTION_SCHEMA["properties"]["action"]["enum"]
    )


@pytest.mark.parametrize("status", ["verified", "violated", "uncertain"])
def test_route_preserves_status_evidence_and_does_not_grant_acceptance(status):
    entry = assessment(status)["assessment"]
    raw = json.dumps({"action": "ASSESS_CONTRACT", "arguments": entry})
    routed = json.loads(route(raw, set(entry) | {"findings"}))
    assert routed == {
        "action": "REPORT",
        "arguments": {"stage": "assessment", "assessment": entry, "findings": []},
    }
    assert "decision" not in routed["arguments"]


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "null",
        '{"action":"ASSESS_CONTRACT","arguments":{"stage":"final"}}',
        '{"action":"READ_FILE","arguments":{"path":"anything"}}',
    ],
)
def test_invalid_or_other_action_is_not_silently_normalized(raw):
    assert route(raw, {"obligation_id", "status", "source_ref", "evidence"}) == raw


def test_actual_loop_routes_native_tool_identity_and_preserves_final_gates(tmp_path):
    reviewer, runtime = fixture_runtime(
        tmp_path, prepare=False, install_adapter=install
    )
    tools = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    runtime.client.native_tools = tools
    final = final_report()
    final.pop("stage")
    actions = iter(
        [
            {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
            {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
            {"action": "ASSESS_CONTRACT", "arguments": assessment()["assessment"]},
            {"action": "REPORT", "arguments": final},
        ]
    )
    shown = []

    def complete(messages):
        shown.append(copy.deepcopy(runtime.client.native_tools))
        return json.dumps(next(actions))

    runtime.client.complete = complete
    result = runtime.run()
    assert result["decision"] == "pass_to_primary"
    assert runtime.protocol_errors == 0
    assert (runtime.review_root / "assessment-1.json").exists()
    assert (runtime.review_root / "completed.json").exists()
    assert [item["function"]["name"] for item in shown[-1]] == ["REPORT"]
    assert "stage" not in shown[-1][0]["function"]["parameters"]["properties"]
    assert runtime.client.native_tools == tools
    assert runtime.client.complete == complete


def test_provisional_violated_status_cannot_be_replaced_by_final_verified_claim(
    tmp_path,
):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=install)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    raw = json.dumps(
        {"action": "ASSESS_CONTRACT", "arguments": assessment("violated")["assessment"]}
    )
    envelope = json.loads(
        route(raw, {"obligation_id", "status", "source_ref", "evidence"})
    )
    runtime.validate_report(envelope["arguments"])
    args = final_report()
    with pytest.raises(reviewer.ReviewError, match="source-backed|contradicts"):
        runtime.validate_report(args)
    assert not (runtime.review_root / "completed.json").exists()
