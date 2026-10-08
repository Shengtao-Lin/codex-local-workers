"""Truncated replies are never actions; optional recovery stays report-only."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / ".local-agents/explorer-runtime.py"
SPEC = importlib.util.spec_from_file_location("explorer_output_recovery_test", MODULE)
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


class Client:
    def __init__(self, outcome="finish", reason="output_token_limit"):
        self.messages = []
        self.outcome = outcome
        self.reason = reason
        self.native_tools = RUNTIME.EXPLORER_TOOLS
        self.native_tool_choice = "auto"
        self.final_tools = None
        self.last_request_stats = {}

    def complete(self, messages):
        self.messages.append(list(messages))
        step = len(self.messages)
        if step <= 2:
            return json.dumps(
                {
                    "action": "READ_FILE",
                    "path": ["source.py", "tests/test_source.py"][step - 1],
                }
            )
        if step == 3 or self.outcome == "truncate-again":
            self.last_request_stats = {
                "finish_reason": "length",
                "completion_tokens": 2048,
            }
            raise RUNTIME.ExplorerModelRequestError(
                self.reason, "truncated reply", self.last_request_stats
            )
        self.final_tools = (
            [tool["function"]["name"] for tool in self.native_tools],
            self.native_tool_choice,
        )
        if self.outcome == "read":
            return json.dumps({"action": "READ_FILE", "path": "unread.py"})
        return json.dumps(
            {
                "action": "FINISH_SUCCESS",
                "source_refs": [
                    {
                        "path": "source.py",
                        "start_line": 1,
                        "end_line": 1,
                        "kind": "implementation",
                    },
                    {
                        "path": "tests/test_source.py",
                        "start_line": 2,
                        "end_line": 99 if self.outcome == "unread-citation" else 2,
                        "kind": "test",
                    },
                ],
                "uncertainties": [],
            }
        )


@pytest.mark.parametrize(
    "outcome", ["finish", "read", "unread-citation", "truncate-again"]
)
def test_one_report_only_recovery_keeps_all_evidence_gates(tmp_path, outcome):
    (tmp_path / "tests").mkdir()
    (tmp_path / "source.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "tests/test_source.py").write_text(
        "def test_value():\n    assert True\n", encoding="utf-8"
    )
    (tmp_path / "unread.py").write_text("secret = 9\n", encoding="utf-8")
    client = Client(outcome)
    runtime = RUNTIME.ExplorerRuntime(
        tmp_path,
        "Locate value and assertion.",
        {
            "explorer_mode": "locate",
            "explorer_output_limit_recovery": True,
            "explorer_required_citation_paths": ["source.py", "tests/test_source.py"],
            "explorer_require_test_assertion_citation": True,
            "max_explorer_turns": 4,
        },
        client,
    )
    report = runtime.run()
    assert report["status"] == ("success" if outcome == "finish" else "failed")
    assert len(client.messages) == 4
    assert "unread.py" not in runtime.read_files
    assert len(runtime.action_trace) == (
        3 if outcome in ("finish", "unread-citation") else 2
    )
    assert any(
        "OUTPUT_LIMIT_REPORT_RECOVERY" in m["content"] for m in client.messages[-1]
    )
    assert client.native_tool_choice == "auto"
    if outcome != "truncate-again":
        assert client.final_tools == (["FINISH_SUCCESS"], "required")


@pytest.mark.parametrize(
    "config,reason",
    [
        ({}, "output_token_limit"),
        (
            {"explorer_output_limit_recovery": True, "max_explorer_turns": 3},
            "output_token_limit",
        ),
        (
            {
                "explorer_output_limit_recovery": True,
                "explorer_required_citation_paths": ["unread.py"],
            },
            "output_token_limit",
        ),
        ({"explorer_output_limit_recovery": True}, "http_4xx"),
        (
            {"explorer_output_limit_recovery": True, "explorer_mode": "investigate"},
            "output_token_limit",
        ),
    ],
)
def test_no_recovery_without_complete_evidence_budget_and_opt_in(
    tmp_path, config, reason
):
    (tmp_path / "tests").mkdir()
    (tmp_path / "source.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "tests/test_source.py").write_text(
        "def test_value():\n    assert True\n", encoding="utf-8"
    )
    client = Client(reason=reason)
    runtime = RUNTIME.ExplorerRuntime(
        tmp_path, "Locate.", {"explorer_mode": "locate", **config}, client
    )
    report = runtime.run()
    assert report["status"] == "failed"
    assert report["infra_failure"]["reason_code"] == reason
    assert len(client.messages) == 3
    assert len(runtime.action_trace) == 2


@pytest.mark.parametrize("invalid", ["true", 1, None])
def test_output_recovery_flag_rejects_non_boolean(tmp_path, invalid):
    with pytest.raises(RUNTIME.ExplorerPreflightBlocked, match="must be a boolean"):
        RUNTIME.ExplorerRuntime(
            tmp_path, "Locate.", {"explorer_output_limit_recovery": invalid}, Client()
        )


class DuplicateClient(Client):
    def complete(self, messages):
        if len(self.messages) < 2:
            return super().complete(messages)
        self.messages.append(list(messages))
        if not any(
            "REPORT_ONLY_RECOVERY" in message["content"] for message in messages
        ):
            return json.dumps({"action": "SEARCH", "query": "absent", "path": "."})
        if self.outcome == "truncate-again":
            raise RUNTIME.ExplorerModelRequestError(
                "output_token_limit", "truncated recovery", {}
            )
        self.final_tools = (
            [tool["function"]["name"] for tool in self.native_tools],
            self.native_tool_choice,
        )
        if self.outcome == "read":
            return json.dumps({"action": "READ_FILE", "path": "unread.py"})
        return json.dumps(
            {
                "action": "FINISH_SUCCESS",
                "source_refs": [
                    {
                        "path": "source.py",
                        "start_line": 1,
                        "end_line": 1,
                        "kind": "implementation",
                    },
                    {
                        "path": "tests/test_source.py",
                        "start_line": 2,
                        "end_line": 99 if self.outcome == "unread-citation" else 2,
                        "kind": "test",
                    },
                ],
                "uncertainties": [],
            }
        )


@pytest.mark.parametrize(
    "outcome", ["finish", "read", "unread-citation", "truncate-again"]
)
def test_duplicate_action_recovery_is_opt_in_report_only_and_shared(tmp_path, outcome):
    (tmp_path / "tests").mkdir()
    (tmp_path / "source.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "tests/test_source.py").write_text(
        "def test_value():\n    assert True\n", encoding="utf-8"
    )
    (tmp_path / "unread.py").write_text("secret = 9\n", encoding="utf-8")
    client = DuplicateClient(outcome)
    runtime = RUNTIME.ExplorerRuntime(
        tmp_path,
        "Locate.",
        {
            "explorer_mode": "locate",
            "explorer_output_limit_recovery": True,
            "explorer_duplicate_action_report_recovery": True,
            "explorer_required_citation_paths": ["source.py", "tests/test_source.py"],
            "explorer_require_test_assertion_citation": True,
        },
        client,
    )
    report = runtime.run()
    assert report["status"] == ("success" if outcome == "finish" else "failed")
    assert len(client.messages) == 5
    assert runtime.finish_repair_used
    assert "unread.py" not in runtime.read_files
    assert runtime.search_count == 1
    if outcome != "truncate-again":
        assert client.final_tools == (["FINISH_SUCCESS"], "required")


@pytest.mark.parametrize(
    "config",
    [
        {},
        {
            "explorer_duplicate_action_report_recovery": True,
            "explorer_required_citation_paths": ["unread.py"],
        },
    ],
)
def test_duplicate_recovery_never_grants_missing_evidence_or_default_opt_in(
    tmp_path, config
):
    (tmp_path / "tests").mkdir()
    (tmp_path / "source.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "tests/test_source.py").write_text(
        "def test_value():\n    assert True\n", encoding="utf-8"
    )
    client = DuplicateClient()
    runtime = RUNTIME.ExplorerRuntime(
        tmp_path, "Locate.", {"explorer_mode": "locate", **config}, client
    )
    report = runtime.run()
    assert report["status"] == "failed"
    assert not runtime.finish_repair_used
    assert len(client.messages) <= runtime.max_turns


@pytest.mark.parametrize("invalid", ["true", 1, None])
def test_duplicate_recovery_flag_is_strict_boolean(tmp_path, invalid):
    with pytest.raises(RUNTIME.ExplorerPreflightBlocked, match="must be a boolean"):
        RUNTIME.ExplorerRuntime(
            tmp_path,
            "Locate.",
            {"explorer_duplicate_action_report_recovery": invalid},
            DuplicateClient(),
        )
