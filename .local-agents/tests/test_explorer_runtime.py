from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).parents[1] / "explorer-runtime.py"
SPEC = importlib.util.spec_from_file_location("explorer_runtime_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


class AdaptiveExplorerClient:
    def __init__(self) -> None:
        self.step = 0

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.step += 1
        actions = [
            {"action": "SEARCH", "query": "build_greeting", "glob": "*.py"},
            {"action": "READ_FILE", "path": "greeting.py"},
            {"action": "READ_FILE", "path": "tests/test_greeting.py"},
            {
                "action": "FINISH_SUCCESS",
                "relevant_files": [
                    {"path": "greeting.py", "reason": "Contains the implementation."},
                    {"path": "tests/test_greeting.py", "reason": "Defines expected behavior."},
                ],
                "call_flow": ["The test imports and calls build_greeting."],
                "findings": ["The implementation is directly exercised by the focused test."],
                "relevant_tests": ["tests/test_greeting.py"],
                "uncertainties": [],
            },
        ]
        return json.dumps(actions[self.step - 1])


class FailIfCalledClient:
    def complete(self, messages: list[dict[str, str]]) -> str:
        raise AssertionError("model should not be called on a valid evidence-cache hit")


class ExplorerRuntimeTests(unittest.TestCase):
    def make_tree(self, root: Path) -> None:
        (root / "tests").mkdir()
        (root / "greeting.py").write_text("def build_greeting(): pass\n", encoding="utf-8")
        (root / "tests" / "test_greeting.py").write_text(
            "from greeting import build_greeting\n", encoding="utf-8"
        )

    def test_read_only_exploration_returns_evidence_backed_report(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source_paths = [root / "greeting.py", root / "tests" / "test_greeting.py"]
            before = {path: path.read_bytes() for path in source_paths}
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Trace greeting behavior and tests.",
                {"max_explorer_turns": 8},
                AdaptiveExplorerClient(),
            )
            report = runtime.run()
            after = {path: path.read_bytes() for path in source_paths}
            self.assertEqual(report["status"], "success")
            self.assertEqual(before, after)
            self.assertEqual(report["budget_usage"]["unique_files_read"], 2)
            self.assertFalse(report["cache"]["hit"])

    def test_exact_exploration_is_reused_only_while_repo_fingerprint_matches(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            task_state_path = root / ".agent" / "tasks" / "task-1" / "state.json"
            task_state_path.parent.mkdir(parents=True)
            task_state_path.write_text(
                json.dumps({
                    "task_id": "task-1",
                    "current_unit_id": "unit-1",
                    "execution_history": [],
                    "recent_attempts": [],
                    "usage": {"coder_calls": 0, "explorer_calls": 0},
                }),
                encoding="utf-8",
            )
            (root / ".agent" / "current-task.json").write_text(
                json.dumps({
                    "task_id": "task-1",
                    "unit_id": "unit-1",
                    "task_state": ".agent/tasks/task-1/state.json",
                }),
                encoding="utf-8",
            )
            task = "Trace greeting behavior and tests."
            first = RUNTIME.ExplorerRuntime(
                root, task, {"max_explorer_turns": 8}, AdaptiveExplorerClient()
            ).run()
            self.assertEqual(first["status"], "success")
            cached = RUNTIME.ExplorerRuntime(root, task, {}, FailIfCalledClient()).run()
            self.assertTrue(cached["cache"]["hit"])
            state_after_cache = json.loads(task_state_path.read_text(encoding="utf-8"))
            self.assertEqual(state_after_cache["usage"]["explorer_calls"], 1)
            source = root / "greeting.py"
            metadata = source.stat()
            source.write_text("def build_greeting(): fail\n", encoding="utf-8")
            os.utime(source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            refreshed_client = AdaptiveExplorerClient()
            refreshed = RUNTIME.ExplorerRuntime(root, task, {}, refreshed_client).run()
            self.assertFalse(refreshed["cache"]["hit"])
            self.assertGreater(refreshed_client.step, 0)
            refreshed_state = json.loads(task_state_path.read_text(encoding="utf-8"))
            self.assertEqual(refreshed_state["usage"]["explorer_calls"], 2)
            self.assertEqual(refreshed_state["recent_attempts"][-1]["result"], "success")

    def test_unread_file_cannot_be_cited_as_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {"max_explorer_turns": 2}, AdaptiveExplorerClient())
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "unread file"):
                runtime.finish_success(
                    {
                        "relevant_files": ["greeting.py"],
                        "findings": ["Claim"],
                        "call_flow": [],
                        "relevant_tests": [],
                        "uncertainties": [],
                    }
                )

    def test_path_escape_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {}, AdaptiveExplorerClient())
            with self.assertRaises(RUNTIME.ExplorerError):
                runtime.read_file({"path": "../outside.py"})

    def test_reparse_component_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "linked").mkdir()
            (root / "linked" / "example.py").write_text("x = 1\n", encoding="utf-8")
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {}, AdaptiveExplorerClient())
            with patch.object(
                RUNTIME, "is_reparse_point", side_effect=lambda path: path.name == "linked"
            ):
                with self.assertRaisesRegex(RUNTIME.ExplorerError, "reparse point"):
                    runtime.read_file({"path": "linked/example.py"})

    def test_invocation_deadline_returns_interrupted(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Inspect.",
                {"explorer_invocation_timeout_seconds": 1},
                AdaptiveExplorerClient(),
            )
            with patch.object(RUNTIME.time, "monotonic", side_effect=[10.0, 12.0]):
                report = runtime.run()
            self.assertEqual(report["status"], "interrupted")
            self.assertEqual(
                report["interruption"]["reason_code"], "invocation_deadline_exceeded"
            )

    def test_path_whitespace_is_normalized_without_expanding_scope(self) -> None:
        self.assertEqual(
            RUNTIME.normalize_relative_path("  .local-agents/tests/test_worker_runtime.py  "),
            ".local-agents/tests/test_worker_runtime.py",
        )
        self.assertEqual(
            RUNTIME.normalize_relative_path("./.local-agents/worker-runtime.py"),
            ".local-agents/worker-runtime.py",
        )

    def test_gpt_oss_harmony_tool_envelope_is_normalized(self) -> None:
        parsed = RUNTIME.parse_action(
            '<|channel|>commentary to=repo_browser.list_files '
            '<|constrain|>json<|message|>{"path":"","max_results":200}'
        )
        self.assertEqual(parsed["action"], "LIST_FILES")
        self.assertEqual(parsed["arguments"]["max_results"], 200)

        code_variant = RUNTIME.parse_action(
            '<|channel|>commentary to=repo_browser.read_file '
            'code<|message|>{"path":"greeting.py"}'
        )
        self.assertEqual(code_variant["action"], "READ_FILE")

        final_variant = RUNTIME.parse_action(
            '<|channel|>final <|constrain|>JSON<|message|>'
            '{"action":"LIST_FILES","path":""}'
        )
        self.assertEqual(final_variant["action"], "LIST_FILES")

        finish_variant = RUNTIME.parse_action(
            '<|channel|>final to=repo_browser.finish_success'
            '<|channel|>commentary code<|message|>'
            '{"relevant_files":["greeting.py"],"call_flow":[],"findings":["ok"],'
            '"relevant_tests":[],"uncertainties":[]}'
        )
        self.assertEqual(finish_variant["action"], "FINISH_SUCCESS")

    def test_compact_report_omits_success_trace_but_keeps_cache_and_evidence(self) -> None:
        report = {
            "schema_version": 1,
            "status": "success",
            "task": "Inspect.",
            "relevant_files": [{"path": "greeting.py", "reason": "implementation"}],
            "findings": ["Observed behavior."],
            "relevant_tests": ["tests/test_greeting.py"],
            "uncertainties": [],
            "observed_files": ["greeting.py", "tests/test_greeting.py"],
            "action_trace": [{"action": "READ_FILE"}],
            "protocol_error_details": [{"error": "old repair"}],
            "budget_usage": {"actions": 4, "unique_files_read": 2, "protocol_errors": 1},
            "cache": {"hit": True},
        }
        compact = RUNTIME.compact_explorer_report(report)
        self.assertTrue(compact["cache"]["hit"])
        self.assertEqual(compact["evidence_summary"]["unique_files_read"], 2)
        self.assertNotIn("action_trace", compact)
        self.assertNotIn("protocol_error_details", compact)


if __name__ == "__main__":
    unittest.main()
