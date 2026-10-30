"""A duplicate read must not force REPORT before its existing coverage gate."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local-agents/tests"))
import test_reviewer_runtime as H


def fixture(root, client=None):
    request = H.ReviewerRuntimeTests().make_run(root)
    extra = root / "tests/test_extra.py"
    extra.write_text("def test_extra():\n    assert True\n", encoding="utf-8")
    packet_path = root / ".agent/tasks/task-1/runs/run-1/packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["focused_tests"].append("tests/test_extra.py")
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    return H.REVIEWER.ReviewerRuntime(
        root,
        request,
        {"reviewer_require_source_and_test_reads": True},
        client or H.FakeClient([]),
    )


def test_one_source_and_one_test_cannot_force_report(tmp_path):
    runtime = fixture(tmp_path)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    assert runtime.coverage_facts()["missing"]
    assert not runtime.required_reads_complete()
    duplicate = runtime.read_file({"path": "tests/test_example.py"})
    assert duplicate["status"] == "already_read"
    assert duplicate.get("required_next_action") != "REPORT"


def test_partial_test_coverage_is_not_complete(tmp_path):
    runtime = fixture(tmp_path)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    runtime.read_file({"path": "tests/test_extra.py", "start_line": 1, "end_line": 1})
    assert not runtime.required_reads_complete()


def test_full_coverage_still_allows_report_without_claiming_semantics(tmp_path):
    runtime = fixture(tmp_path)
    for path in ("src/example.py", "tests/test_example.py", "tests/test_extra.py"):
        runtime.read_file({"path": path})
    assert runtime.required_reads_complete()
    duplicate = runtime.read_file({"path": "src/example.py"})
    assert duplicate["required_next_action"] == "REPORT"
    assert "verified_contract_ids" not in duplicate


def test_real_loop_keeps_read_tools_available_until_all_tests_displayed(tmp_path):
    class Client(H.FakeClient):
        native_tool_choice = "auto"

        def __init__(self, actions):
            super().__init__(actions)
            self.native_tools = [
                {"function": {"name": name}}
                for name in ("READ_FILE", "SEARCH", "REPORT")
            ]
            self.tool_sets = []

        def complete(self, messages):
            self.tool_sets.append(
                [tool["function"]["name"] for tool in self.native_tools]
            )
            return super().complete(messages)

    actions = [
        {"action": "READ_FILE", "arguments": {"path": path}}
        for path in (
            "src/example.py",
            "tests/test_example.py",
            "tests/test_example.py",
            "tests/test_extra.py",
        )
    ]
    actions.append(
        {
            "action": "REPORT",
            "arguments": {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
            },
        }
    )
    client = Client(actions)
    runtime = fixture(tmp_path, client)
    report = runtime.run()
    assert report["decision"] == "pass_to_primary"
    assert "READ_FILE" in client.tool_sets[3]
    assert runtime.protocol_errors == 0


def test_archived_presence_quote_is_not_implementation_evidence():
    kit = Path(__file__).resolve().parents[1]
    case = (
        kit
        / "benchmarks/work/harness-convergence/r3-serializer-20261016-1/cases/presence-candidate-1"
    )
    report = json.loads((case / "reviewer.json").read_text(encoding="utf-8"))
    binding = {
        "path": "src/evaluation_harness/scorers/deterministic.py",
        "symbol": "OutputPresentScorer.score",
    }
    source = (case / "isolated" / binding["path"]).read_text(encoding="utf-8")
    assert not H.REVIEWER.WORKER.citation_binding().covers(
        binding, source, report["contract_review"][0]["source_refs"]
    )
    assert H.REVIEWER.WORKER.citation_binding().covers(
        binding, source, [{"path": binding["path"], "start_line": 33, "end_line": 43}]
    )


def test_missing_reads_still_reject_a_pass(tmp_path):
    runtime = fixture(tmp_path)
    runtime.read_file({"path": "src/example.py"})
    runtime.read_file({"path": "tests/test_example.py"})
    with pytest.raises(H.REVIEWER.ReviewError, match="coverage"):
        runtime.validate_report(
            {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
            }
        )
