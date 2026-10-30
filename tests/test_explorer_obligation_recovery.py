"""Source-only obligations must not create fictitious mandatory test evidence."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "explorer_obligation_controls",
    Path(__file__).parents[1] / ".local-agents/explorer-runtime.py",
)
E = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = E
SPEC.loader.exec_module(E)


def runtime(root, config=None, task="Read source only; no code/test changes.", client=None):
    (root / "tests").mkdir(exist_ok=True)
    (root / "source.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (root / "tests/test_source.py").write_text("def test_f(): pass\n", encoding="utf-8")
    return E.ExplorerRuntime(root, task, config or {}, client or object())


def report():
    return {"relevant_files": ["source.py"], "findings": ["source.py line 1 defines f"],
            "relevant_tests": [], "uncertainties": []}


def test_source_only_override_does_not_require_incidental_test_paths(tmp_path):
    r = runtime(tmp_path, {"explorer_require_test_evidence": False})
    r.read_file({"path": "source.py"})
    r.read_file({"path": "tests/test_source.py"})
    assert r.finish_success(report())["status"] == "success"


@pytest.mark.parametrize("config,task", [({}, "Read source and test evidence"),
    ({"explorer_require_test_evidence": True}, "Read source")])
def test_positive_obligation_still_requires_read_test_in_report(tmp_path, config, task):
    r = runtime(tmp_path, config, task)
    r.read_file({"path": "source.py"})
    r.read_file({"path": "tests/test_source.py"})
    with pytest.raises(E.ExplorerError, match="relevant_tests must include"):
        r.finish_success(report())


@pytest.mark.parametrize("value", [None, "false", 0, [], {}])
def test_invalid_explicit_obligation_fails_preflight(tmp_path, value):
    with pytest.raises(E.ExplorerPreflightBlocked):
        runtime(tmp_path, {"explorer_require_test_evidence": value})


def test_obligation_is_part_of_cache_identity(tmp_path):
    explicit = runtime(tmp_path, {"explorer_require_test_evidence": False})
    legacy = runtime(tmp_path)
    assert explicit.cache_task != legacy.cache_task


def test_opt_out_never_licenses_unread_test_or_false_line(tmp_path):
    r = runtime(tmp_path, {"explorer_require_test_evidence": False})
    r.read_file({"path": "source.py", "start_line": 1, "end_line": 1})
    value = report()
    value["relevant_tests"] = ["tests/test_source.py"]
    with pytest.raises(E.ExplorerError, match="unread test file"):
        r.finish_success(value)
    value["relevant_tests"] = []
    value["citations"] = [{"path": "source.py", "line": 2, "claim": "returns 1"}]
    with pytest.raises(E.ExplorerSourceReferenceError) as caught:
        r.finish_success(value)
    assert caught.value.read_paths == ("source.py",)
    assert 2 not in r.observed_line_numbers["source.py"]


def test_initial_unread_citation_can_get_real_evidence_within_same_budget(tmp_path):
    value = report()
    value["action"] = "FINISH_SUCCESS"
    value["citations"] = [{"path": "source.py", "line": 2, "claim": "returns 1"}]
    actions = [{"action": "READ_FILE", "path": "source.py", "start_line": 1, "end_line": 1},
               value, {"action": "READ_FILE", "path": "source.py", "start_line": 2, "end_line": 2}, value]

    class Client:
        def __init__(self):
            self.messages = []

        def complete(self, messages):
            self.messages.append(list(messages))
            return json.dumps(actions[len(self.messages) - 1])

    client = Client()
    r = runtime(tmp_path, {"max_explorer_turns": 4}, task="Read return evidence", client=client)
    result = r.run()
    assert result["status"] == "success"
    assert len(client.messages) == 4
    assert "Required reads: source.py" in client.messages[2][-1]["content"]
    assert r.protocol_errors == 1


@pytest.mark.parametrize("extra,expected_recovery", [({}, True),
    ({"explorer_require_trace_symbol": "f"}, False),
    ({"explorer_required_citation_paths": ["source.py", "tests/test_source.py"]}, False),
    ({"explorer_require_test_evidence": True}, False)])
def test_source_only_report_recovery_requires_actual_current_obligations(tmp_path, extra, expected_recovery):
    final = {"action": "FINISH_SUCCESS", **report(),
             "citations": [{"path": "source.py", "line": 1, "claim": "defines f"}]}
    malformed = json.dumps(final) + "\nThis is final."

    class Client:
        native_tools = E.EXPLORER_TOOLS
        native_tool_choice = "auto"

        def __init__(self):
            self.tools_seen = []

        def complete(self, _messages):
            self.tools_seen.append([t["function"]["name"] for t in self.native_tools])
            step = len(self.tools_seen)
            if step == 1:
                return json.dumps({"action": "READ_FILE", "path": "source.py"})
            return malformed if step <= 3 else json.dumps(final)

    config = {"explorer_require_test_evidence": False, "max_explorer_turns": 4,
              "explorer_required_citation_paths": ["source.py"], **extra}
    client = Client()
    r = runtime(tmp_path, config, client=client)
    result = r.run()
    assert r.finish_repair_used == expected_recovery
    if expected_recovery:
        assert result["status"] == "success"
        assert client.tools_seen[-1] == ["FINISH_SUCCESS"]
        assert r.protocol_errors == 2
