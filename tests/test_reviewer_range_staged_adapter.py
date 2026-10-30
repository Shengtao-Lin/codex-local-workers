import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_range_staged_adapter import install, model_tools, route
from test_reviewer_staged_assessment_adapter import (
    assessment,
    final_report,
    fixture_runtime,
)


def test_model_schema_has_exactly_one_range_array_and_compatible_repair(tmp_path):
    reviewer, _ = fixture_runtime(tmp_path, install_adapter=install)
    tools = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    repaired = reviewer.canonical_citation_tools(tools)
    for variant in (tools, repaired):
        external = model_tools(variant, False)
        assess = next(
            item["function"]["parameters"]
            for item in external
            if item["function"]["name"] == "ASSESS_CONTRACT"
        )
        assert "source_ranges" in assess["required"]
        assert not {"source_ref", "source_refs"} & set(assess["properties"])
    assert reviewer.REVIEW_NATIVE_TOOLS == tools


def test_route_does_not_allow_model_private_stage_or_citation_aliases():
    forbidden = json.dumps(
        {
            "action": "REPORT",
            "arguments": {
                "stage": "assessment",
                "assessment": assessment()["assessment"],
            },
        }
    )
    rejected = json.loads(
        route(forbidden, {"obligation_id", "status", "source_ranges", "evidence"})
    )
    assert rejected["action"] == "INVALID_MODEL_REPORT_FIELDS"
    assert rejected["arguments"] == json.loads(forbidden)["arguments"]
    aliases = json.dumps(
        {
            "action": "ASSESS_CONTRACT",
            "arguments": {"source_ref": {}, "source_refs": []},
        }
    )
    assert (
        route(aliases, {"obligation_id", "status", "source_ranges", "evidence"})
        == aliases
    )


def test_actual_loop_uses_range_codec_and_final_gate(tmp_path):
    reviewer, runtime = fixture_runtime(
        tmp_path, prepare=False, install_adapter=install
    )
    runtime.client.native_tools = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    entry = assessment()["assessment"]
    entry["source_ranges"] = [entry.pop("source_ref")]
    final = final_report()
    final.pop("stage")
    actions = iter(
        [
            {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
            {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
            {"action": "ASSESS_CONTRACT", "arguments": entry},
            {"action": "REPORT", "arguments": final},
        ]
    )
    runtime.client.complete = lambda messages: json.dumps(next(actions))
    report = runtime.run()
    assert report["decision"] == "pass_to_primary"
    assert (
        report["contract_review"][0]["source_refs"][0]["canonical_quote"] == "VALUE = 2"
    )
    assert runtime.protocol_errors == 0


@pytest.mark.parametrize("boundary", [True, False, "1"])
def test_bad_range_boundaries_remain_rejected_after_codec(tmp_path, boundary):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=install)
    runtime.read_file({"path": "src/example.py"})
    entry = assessment()["assessment"]
    ref = entry.pop("source_ref")
    ref["start_line"] = boundary
    entry["source_ranges"] = [ref]
    routed = json.loads(
        route(json.dumps({"action": "ASSESS_CONTRACT", "arguments": entry}), set(entry))
    )
    with pytest.raises(reviewer.ReviewError):
        runtime.validate_report(routed["arguments"])
    assert not runtime.staged_assessments
