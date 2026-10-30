import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reviewer_catalog_staged_adapter import decode, install, model_tools
from reviewer_range_staged_adapter import install as install_range
from test_reviewer_staged_assessment_adapter import final_report, fixture_runtime


def combined(reviewer):
    install_range(reviewer)
    install(reviewer)


def test_real_staged_loop_transports_only_actual_read_ids_and_keeps_status(tmp_path):
    reviewer, runtime = fixture_runtime(
        tmp_path, prepare=False, install_adapter=combined
    )
    runtime.client.native_tools = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    final = final_report()
    final.pop("stage")
    actions = iter(
        [
            {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
            {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
            {
                "action": "ASSESS_CONTRACT",
                "arguments": {
                    "obligation_id": "behavior-1",
                    "status": "verified",
                    "source_evidence_ids": ["E1"],
                    "evidence": "VALUE equals 2.",
                },
            },
            {"action": "REPORT", "arguments": final},
        ]
    )
    schemas = []

    def complete(messages):
        schemas.append(copy.deepcopy(runtime.client.native_tools))
        return json.dumps(next(actions))

    runtime.client.complete = complete
    report = runtime.run()
    assert report["decision"] == "pass_to_primary"
    assert report["contract_review"][0]["canonical_quote"] == "VALUE = 2"
    assessment_tool = next(
        tool["function"]["parameters"]
        for tool in schemas[2]
        if tool["function"]["name"] == "ASSESS_CONTRACT"
    )
    assert "source_evidence_ids" in assessment_tool["required"]
    assert (
        not {"source_ref", "source_refs", "source_ranges"}
        & assessment_tool["properties"].keys()
    )
    assert runtime.protocol_errors == 0


@pytest.mark.parametrize("ids", [["E999"], ["E1", "E1"], [True], [], ["E1"] * 4])
def test_unread_unknown_or_invalid_ids_never_become_source_evidence(tmp_path, ids):
    _, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    runtime.read_file({"path": "src/example.py"})
    with pytest.raises(ValueError):
        decode(
            runtime,
            json.dumps(
                {"action": "ASSESS_CONTRACT", "arguments": {"source_evidence_ids": ids}}
            ),
        )
    assert not runtime.staged_assessments


def test_mixed_aliases_not_dropped_and_changed_source_rejected(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    runtime.read_file({"path": "src/example.py"})
    raw = json.dumps(
        {
            "action": "ASSESS_CONTRACT",
            "arguments": {"source_evidence_ids": ["E1"], "source_ranges": []},
        }
    )
    rejected = json.loads(decode(runtime, raw))
    assert rejected["action"] == "INVALID_MODEL_CATALOG_FIELDS"
    assert rejected["arguments"] == json.loads(raw)["arguments"]
    (tmp_path / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        decode(runtime, raw)


def test_codec_preserves_uncertainty_claims_and_isolated_native_schema(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    runtime.read_file({"path": "src/example.py"})
    original = {
        "action": "ASSESS_CONTRACT",
        "arguments": {
            "obligation_id": "behavior-1",
            "status": "uncertain",
            "source_evidence_ids": ["E1"],
            "evidence": "still uncertain",
            "findings": [],
        },
    }
    decoded = json.loads(decode(runtime, json.dumps(original)))
    assert decoded["arguments"]["status"] == "uncertain"
    assert decoded["arguments"]["evidence"] == "still uncertain"
    assert decoded["arguments"]["findings"] == []
    tools = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    model_tools(tools)
    assert tools == reviewer.REVIEW_NATIVE_TOOLS
