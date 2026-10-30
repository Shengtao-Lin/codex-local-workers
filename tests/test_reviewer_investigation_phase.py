import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reviewer_investigation_phase_adapter import pending_reads, phase_tools
from test_reviewer_staged_assessment_adapter import fixture_runtime


def test_schema_phase_preserves_status_and_final_report_without_auto_verdict():
    tools = [
        {
            "function": {
                "name": "ASSESS_CONTRACT",
                "parameters": {
                    "properties": {
                        "obligation_id": {"type": "string"},
                        "status": {"enum": ["verified", "violated", "uncertain"]},
                    }
                },
            }
        },
        {
            "function": {
                "name": "REPORT",
                "parameters": {
                    "properties": {
                        "decision": {"enum": ["pass_to_primary", "rework", "escalate"]}
                    }
                },
            }
        },
        {"function": {"name": "READ_FILE"}},
    ]
    original = copy.deepcopy(tools)
    assert [
        t["function"]["name"] for t in phase_tools(tools, [{"path": "test"}], ["a"])
    ] == ["READ_FILE"]
    ready = phase_tools(tools, [], ["b"])
    assert ready[0]["function"]["parameters"]["properties"]["obligation_id"][
        "enum"
    ] == ["b"]
    assert (
        ready[0]["function"]["parameters"]["properties"]["status"]
        == original[0]["function"]["parameters"]["properties"]["status"]
    )
    assert ready[1] == original[1]
    assert [t["function"]["name"] for t in phase_tools(tools, [], [])] == [
        "REPORT",
        "READ_FILE",
    ]
    assert tools == original


def test_pending_navigation_is_not_read_and_advances_past_first_window(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path)
    runtime.config["reviewer_contract_test_reads"] = [
        {"path": "tests/test_example.py", "contract_id": "behavior-1"}
    ]
    pending = pending_reads(runtime)
    assert pending[0]["start_line"] == 1
    assert not runtime.read_lines
    runtime.read_file({"path": "tests/test_example.py"})
    assert not pending_reads(runtime)
    runtime.config["reviewer_dependency_evidence"] = [
        {"path": "src/example.py", "anchors": ["VALUE"]}
    ]
    assert pending_reads(runtime)[0]["path"] == "src/example.py"
    assert "src/example.py" not in runtime.read_lines
    runtime.read_file({"path": "src/example.py"})
    assert not pending_reads(runtime)
    (tmp_path / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        pending_reads(runtime)


def test_test_navigation_does_not_replay_already_read_prefix(tmp_path):
    _, runtime = fixture_runtime(tmp_path)
    path = tmp_path / "tests/long.py"
    path.write_text(
        "\n".join("assert True" for _ in range(150)) + "\n", encoding="utf-8"
    )
    runtime.read_roots.append("tests/long.py")
    runtime.config["reviewer_contract_test_reads"] = [
        {"path": "tests/long.py", "contract_id": "behavior-1"}
    ]
    assert pending_reads(runtime)[0]["end_line"] == 100
    runtime.read_file({"path": "tests/long.py", "start_line": 1, "end_line": 100})
    assert pending_reads(runtime) == [
        {"path": "tests/long.py", "start_line": 101, "end_line": 150}
    ]


def test_actual_client_wrapper_restores_tools_and_never_rewrites_response(monkeypatch):
    import reviewer_investigation_phase_adapter as adapter

    original_tools = [
        {"function": {"name": name}}
        for name in ("READ_FILE", "ASSESS_CONTRACT", "REPORT")
    ]
    seen = []

    class Runtime:
        def __init__(self):
            self.staged_assessments = {}
            self.client = SimpleNamespace(
                native_tools=original_tools, complete=self.complete
            )

        def complete(self, messages):
            seen.append(copy.deepcopy(self.client.native_tools))
            assert "FEASIBLE_REVIEW_PHASE" in messages[-1]["content"]
            return "unchanged invalid model output"

        def review_obligations(self):
            return [{"id": "a"}]

        def event(self, *args):
            pass

        def run(self):
            return self.client.complete([])

    reviewer = SimpleNamespace(ReviewerRuntime=Runtime)
    monkeypatch.setattr(
        adapter, "pending_reads", lambda runtime: [{"path": "protected.py"}]
    )
    adapter.install(reviewer)
    runtime = Runtime()
    original_complete = runtime.client.complete
    assert runtime.run() == "unchanged invalid model output"
    assert seen == [[{"function": {"name": "READ_FILE"}}]]
    assert runtime.client.native_tools is original_tools
    assert runtime.client.complete == original_complete

    def raises(messages):
        raise RuntimeError("model unavailable")

    runtime.client.complete = raises
    with pytest.raises(RuntimeError, match="model unavailable"):
        runtime.run()
    assert runtime.client.native_tools is original_tools
    assert runtime.client.complete is raises
