from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "explorer-runtime.py"
SPEC = importlib.util.spec_from_file_location("explorer_runtime_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


class AdaptiveExplorerClient:
    def __init__(self) -> None:
        self.step = 0
        self.messages_seen: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages_seen.append(list(messages))
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


class RepeatingClient:
    def __init__(self) -> None:
        self.step = 0

    def complete(self, _messages: list[dict[str, str]]) -> str:
        self.step += 1
        return json.dumps({"action": "SEARCH", "query": "absent-symbol", "glob": "*.py"})


class InfraFailureClient:
    last_request_stats = {"rejection_reason": "http_4xx"}

    def complete(self, _messages: list[dict[str, str]]) -> str:
        raise RUNTIME.ExplorerModelRequestError(
            "http_4xx",
            "request rejected",
            {"provider_status_code": 400, "provider_response_body": "bad request"},
        )


class FinishRepairClient:
    def __init__(self) -> None:
        self.native_tools = RUNTIME.EXPLORER_TOOLS
        self.native_tool_choice = "auto"
        self.requests: list[tuple[list[str], str, list[str]]] = []

    def complete(self, _messages: list[dict[str, str]]) -> str:
        self.requests.append(
            (
                [tool["function"]["name"] for tool in self.native_tools],
                self.native_tool_choice,
                next(
                    (
                        tool["function"]["parameters"].get("required", [])
                        for tool in self.native_tools
                        if tool["function"]["name"] == "FINISH_SUCCESS"
                    ),
                    [],
                ),
            )
        )
        step = len(self.requests)
        if step <= 2:
            return json.dumps(
                {"action": "READ_FILE", "path": ["greeting.py", "tests/test_greeting.py"][step - 1]}
            )
        report = {
            "action": "FINISH_SUCCESS",
            "relevant_files": [{"path": "greeting.py", "reason": "implementation"}],
            "call_flow": [],
            "findings": ["greeting.py line 1 defines the implementation."],
            "relevant_tests": ["tests/test_greeting.py"],
            "uncertainties": [],
        }
        if step == 3:
            report["relevant_tests"] = []
        else:
            report["citations"] = [
                {"path": "tests/test_greeting.py", "line": 1, "claim": "imports the function"}
            ]
        return json.dumps(report)


class RepeatedMalformedAfterEvidenceClient:
    def __init__(self) -> None:
        self.native_tools = RUNTIME.EXPLORER_TOOLS
        self.native_tool_choice = "auto"
        self.requests: list[tuple[list[str], list[dict[str, str]]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.requests.append(
            ([tool["function"]["name"] for tool in self.native_tools], list(messages))
        )
        step = len(self.requests)
        if step <= 2:
            path = "greeting.py" if step == 1 else "tests/test_greeting.py"
            return json.dumps({"action": "READ_FILE", "path": path})
        if step <= 4:
            return '{"action":"FINISH_SUCCESS"'
        return json.dumps(
            {
                "action": "FINISH_SUCCESS",
                "relevant_files": [{"path": "greeting.py", "reason": "implementation"}],
                "call_flow": [],
                "findings": ["greeting.py line 1 defines the function"],
                "relevant_tests": ["tests/test_greeting.py"],
                "uncertainties": [],
                "citations": [
                    {"path": "greeting.py", "line": 1, "claim": "defines the function"},
                    {"path": "tests/test_greeting.py", "line": 1, "claim": "imports it"},
                ],
            }
        )


class LocateEvidenceRepairClient:
    def __init__(self) -> None:
        self.native_tools = RUNTIME.EXPLORER_TOOLS
        self.native_tool_choice = "auto"
        self.allowed_tools: list[list[str]] = []

    def complete(self, _messages: list[dict[str, str]]) -> str:
        self.allowed_tools.append([tool["function"]["name"] for tool in self.native_tools])
        step = len(self.allowed_tools)
        if step == 1:
            return json.dumps(
                {
                    "action": "FINISH_SUCCESS",
                    "source_refs": [
                        {
                            "path": "greeting.py",
                            "start_line": 1,
                            "end_line": 1,
                            "kind": "implementation",
                        }
                    ],
                    "uncertainties": [],
                }
            )
        if step <= 3:
            return json.dumps(
                {
                    "action": "READ_FILE",
                    "path": "greeting.py" if step == 2 else "tests/test_greeting.py",
                }
            )
        return json.dumps(
            {
                "action": "FINISH_SUCCESS",
                "source_refs": [
                    {
                        "path": "greeting.py",
                        "start_line": 1,
                        "end_line": 1,
                        "kind": "implementation",
                    },
                    {
                        "path": "tests/test_greeting.py",
                        "start_line": 2,
                        "end_line": 2,
                        "kind": "test",
                    },
                ],
                "uncertainties": [],
            }
        )


class ExplorerRuntimeTests(unittest.TestCase):
    def test_globstar_does_not_hide_root_level_test_directory(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Locate.", {}, AdaptiveExplorerClient())
            result = runtime.list_files({"glob": "**/tests/test_greeting.py"})
            self.assertIn("tests/test_greeting.py", result["files"])
            result = runtime.search(
                {"glob": "**/tests/test_greeting.py", "query": "build_greeting"}
            )
            self.assertTrue(result["results"])

    def test_localization_includes_displayed_blank_lines_but_not_truncated_lines(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_text("a = 1\n\nb = 2\n" + "#" * 3000 + "\nc = 3\n")
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Locate.",
                {"explorer_mode": "locate", "max_tool_output_chars": 2048},
                AdaptiveExplorerClient(),
            )
            observation = runtime.read_file({"path": "source.py"})
            self.assertTrue(observation["truncated"])
            self.assertEqual(observation["end_line"], 3)
            args = {
                "source_refs": [
                    {"path": "source.py", "start_line": 1, "end_line": 3, "kind": "implementation"}
                ],
                "uncertainties": [],
            }
            self.assertEqual(
                runtime.finish_success(args)["source_refs"][0]["quote"], "a = 1\n\nb = 2"
            )
            args["source_refs"][0]["end_line"] = 5
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "unread"):
                runtime.finish_success(args)

    def test_localization_materializes_only_current_observed_source(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(
                root, "Locate greeting.", {"explorer_mode": "locate"}, AdaptiveExplorerClient()
            )
            runtime.read_file({"path": "greeting.py"})
            args = {
                "source_refs": [
                    {
                        "path": "greeting.py",
                        "start_line": 1,
                        "end_line": 1,
                        "kind": "implementation",
                    }
                ],
                "uncertainties": [],
            }
            result = runtime.finish_success(args)
            self.assertEqual(result["semantic_verdict"], "not_evaluated")
            self.assertEqual(
                result["source_refs"][0]["quote"],
                (root / "greeting.py").read_text().splitlines()[0],
            )
            self.assertEqual(RUNTIME.compact_explorer_report(result)["explorer_mode"], "locate")
            self.assertNotIn("quote", RUNTIME.compact_explorer_report(result)["source_refs"][0])
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "only source_refs"):
                runtime.finish_success({**args, "findings": ["The test passes"]})
            (root / "greeting.py").write_text("def changed():\n    pass\n")
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "changed since"):
                runtime.finish_success(args)

    def test_localization_rejects_unread_or_oversized_refs_and_wrong_mode(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(
                root, "Locate.", {"explorer_mode": "locate"}, AdaptiveExplorerClient()
            )
            for start, end, expected in (
                (1, 1, "unread"),
                (1, 81, "80 total"),
                (True, 2, "integer"),
            ):
                with (
                    self.subTest(start=start, end=end),
                    self.assertRaisesRegex(RUNTIME.ExplorerError, expected),
                ):
                    runtime.finish_success(
                        {
                            "source_refs": [
                                {
                                    "path": "greeting.py",
                                    "start_line": start,
                                    "end_line": end,
                                    "kind": "implementation",
                                }
                            ],
                            "uncertainties": [],
                        }
                    )
            self.assertNotEqual(runtime.cache_task, runtime.task)
            with self.assertRaises(RUNTIME.ExplorerPreflightBlocked):
                RUNTIME.ExplorerRuntime(
                    root, "Locate.", {"explorer_mode": "typo"}, AdaptiveExplorerClient()
                )

    def test_localization_unread_finish_can_read_before_terminal_retry(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "tests" / "test_greeting.py").write_text(
                "from greeting import build_greeting\nassert build_greeting() is None\n",
                encoding="utf-8",
            )
            client = LocateEvidenceRepairClient()
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Locate implementation and assertion.",
                {
                    "explorer_mode": "locate",
                    "explorer_required_citation_paths": ["tests/test_greeting.py"],
                    "explorer_require_test_assertion_citation": True,
                },
                client,
            )
            report = runtime.run()
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["budget_usage"]["protocol_errors"], 1)
            self.assertIn("READ_FILE", client.allowed_tools[1])
            self.assertFalse(runtime.finish_repair_used)

    def test_localization_requires_actual_test_assertion_citation_when_configured(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "tests" / "test_greeting.py").write_text(
                "from greeting import build_greeting\nassert build_greeting() is None\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Locate implementation and assertion.",
                {"explorer_mode": "locate", "explorer_require_test_assertion_citation": True},
                FailIfCalledClient(),
            )
            runtime.read_file({"path": "greeting.py"})
            runtime.read_file({"path": "tests/test_greeting.py"})
            refs = [
                {"path": "greeting.py", "start_line": 1, "end_line": 1, "kind": "implementation"},
                {"path": "tests/test_greeting.py", "start_line": 1, "end_line": 1, "kind": "test"},
            ]
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "test assertion line"):
                runtime.finish_success({"source_refs": refs, "uncertainties": []})
            refs[1]["start_line"] = refs[1]["end_line"] = 2
            self.assertEqual(
                runtime.finish_success({"source_refs": refs, "uncertainties": []})["status"],
                "success",
            )

    def test_citation_shape_recovery_is_one_shot_and_enforced_before_dispatch(self) -> None:
        for repair_action in ("FINISH_SUCCESS", "READ_FILE"):
            with self.subTest(repair_action=repair_action), TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_tree(root)
                client = FinishRepairClient()
                original_complete = client.complete

                def complete(messages):
                    value = json.loads(original_complete(messages))
                    if len(client.requests) == 3:
                        value["relevant_tests"] = ["tests/test_greeting.py"]
                        value["citations"] = [{"path": "greeting.py", "line": 1}]
                    elif len(client.requests) == 4:
                        value = (
                            {"action": "READ_FILE", "path": "other.py"}
                            if repair_action == "READ_FILE"
                            else value
                        )
                        if repair_action == "FINISH_SUCCESS":
                            value["citations"] = [{"path": "greeting.py", "line": 1}]
                    return json.dumps(value)

                client.complete = complete
                runtime = RUNTIME.ExplorerRuntime(root, "Inspect greeting and tests.", {}, client)
                result = runtime.run()
                self.assertEqual(result["status"], "failed")
                self.assertIn("report-only recovery exhausted", result["failure_reason"])
                self.assertEqual(len(client.requests), 4)
                self.assertEqual(client.requests[-1][0], ["FINISH_SUCCESS"])
                self.assertNotIn("other.py", runtime.read_files)

    def test_repeated_malformed_report_gets_one_evidence_backed_terminal_retry(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = RepeatedMalformedAfterEvidenceClient()
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Inspect greeting and tests.",
                {
                    "explorer_required_citation_paths": [
                        "greeting.py",
                        "tests/test_greeting.py",
                    ]
                },
                client,
            )
            result = runtime.run()
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["budget_usage"]["protocol_errors"], 2)
            self.assertEqual(client.requests[-1][0], ["FINISH_SUCCESS"])
            self.assertTrue(
                any("REPORT_ONLY_RECOVERY" in item["content"] for item in client.requests[-1][1])
            )
            self.assertEqual(client.native_tools, RUNTIME.EXPLORER_TOOLS)

    def test_invalid_finish_gets_one_report_only_retry_without_waiving_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FinishRepairClient()
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Inspect greeting and tests.",
                {"explorer_required_citation_paths": ["greeting.py", "tests/test_greeting.py"]},
                client,
            )
            result = runtime.run()
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["relevant_tests"], ["tests/test_greeting.py"])
            self.assertEqual(result["budget_usage"]["protocol_errors"], 1)
            self.assertEqual(client.requests[-1][:2], (["FINISH_SUCCESS"], "required"))
            self.assertIn("citations", client.requests[-1][2])
            self.assertEqual(client.native_tools, RUNTIME.EXPLORER_TOOLS)
            self.assertEqual(client.native_tool_choice, "auto")

    def test_invalid_finish_repair_survives_no_evidence_boundary(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FinishRepairClient()
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Inspect greeting and tests.",
                {
                    "explorer_required_citation_paths": [
                        "greeting.py",
                        "tests/test_greeting.py",
                    ],
                    "max_explorer_no_progress_streak": 1,
                },
                client,
            )
            result = runtime.run()
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["budget_usage"]["protocol_errors"], 1)
            self.assertEqual(len(client.requests), 4)

    def test_structured_citations_require_an_actually_read_line(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Inspect greeting and tests.",
                {"explorer_required_citation_paths": ["greeting.py", "tests/test_greeting.py"]},
                FailIfCalledClient(),
            )
            runtime.read_file({"path": "greeting.py"})
            runtime.read_file({"path": "tests/test_greeting.py"})
            report = {
                "relevant_files": [{"path": "greeting.py", "reason": "implementation"}],
                "call_flow": [],
                "findings": [],
                "relevant_tests": ["tests/test_greeting.py"],
                "uncertainties": [],
                "citations": [
                    {"path": "greeting.py", "line": 1, "claim": "defines the function"},
                    {"path": "tests/test_greeting.py", "line": 1, "claim": "imports it"},
                ],
            }
            self.assertEqual(runtime.finish_success(report)["status"], "success")
            report["citations"][1]["line"] = 1000
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "not an observed"):
                runtime.finish_success(report)

    def test_citation_can_use_early_line_after_prompt_replay_is_trimmed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "greeting.py").write_text(
                "def build_greeting(): pass\n"
                + "".join(f"long_line_{number} = '{'x' * 80}'\n" for number in range(2, 201)),
                encoding="utf-8",
            )
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {}, FailIfCalledClient())
            runtime.read_file({"path": "greeting.py", "start_line": 1, "end_line": 200})
            self.assertNotIn("1: def build_greeting", runtime.read_observations["greeting.py"])
            result = runtime.finish_success(
                {
                    "relevant_files": [{"path": "greeting.py", "reason": "implementation"}],
                    "call_flow": [],
                    "findings": [],
                    "relevant_tests": [],
                    "uncertainties": [],
                    "citations": [
                        {"path": "greeting.py", "line": 1, "claim": "defines the function"}
                    ],
                }
            )
            self.assertIn("greeting.py line 1", result["findings"][0])

    def test_prompt_distinguishes_test_expectations_from_source_behavior(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {}, FailIfCalledClient())
            prompt = runtime.system_prompt()
            self.assertIn("A test assertion states expected behavior", prompt)
            self.assertIn("read that definition or state uncertainty", prompt)

    def test_trim_replays_previously_read_test_lines(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {}, FailIfCalledClient())
            runtime.read_file({"path": "tests/test_greeting.py"})
            messages = [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "task"},
                *({"role": "user", "content": f"turn {number}"} for number in range(12)),
            ]
            trimmed = runtime._trim_messages(messages)
            self.assertIn("PREVIOUSLY_OBSERVED_READ_LINES", trimmed[2]["content"])
            self.assertIn("tests/test_greeting.py", trimmed[2]["content"])
            self.assertIn("1: from greeting import build_greeting", trimmed[2]["content"])
            self.assertEqual(trimmed[-1], messages[-1])

    def test_identical_read_replays_once_after_context_trim(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {}, FailIfCalledClient())
            arguments = {"path": "greeting.py"}
            runtime.execute("READ_FILE", arguments)
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "identical read"):
                runtime.execute("READ_FILE", arguments)
            runtime._trim_messages([{"role": "user", "content": str(index)} for index in range(13)])
            restored, _ = runtime.execute("READ_FILE", arguments)
            self.assertEqual(restored["status"], "replayed")
            self.assertEqual(restored["new_evidence_count"], 0)
            self.assertIn("build_greeting", restored["content"])
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "identical read"):
                runtime.execute("READ_FILE", arguments)

    def test_context_replay_rejects_changed_file(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {}, FailIfCalledClient())
            arguments = {"path": "greeting.py"}
            runtime.execute("READ_FILE", arguments)
            runtime._trim_messages([{"role": "user", "content": str(index)} for index in range(13)])
            (root / "greeting.py").write_text("changed = True\n", encoding="utf-8")
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "file changed"):
                runtime.execute("READ_FILE", arguments)

    def test_opt_in_citation_gate_requires_source_and_test_lines(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            paths = ["greeting.py", "tests/test_greeting.py"]
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Inspect greeting and tests.",
                {"explorer_required_citation_paths": paths},
                FailIfCalledClient(),
            )
            for path in paths:
                runtime.read_file({"path": path})
            report_args = {
                "relevant_files": [{"path": "greeting.py", "reason": "implementation"}],
                "call_flow": [],
                "findings": ["The implementation is tested."],
                "relevant_tests": ["tests/test_greeting.py"],
                "uncertainties": [],
            }
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "line citations") as missing:
                runtime.finish_success(report_args)
            self.assertIn("greeting.py line 1", str(missing.exception))
            self.assertIn("tests/test_greeting.py line", str(missing.exception))
            self.assertNotIn("def build_greeting", str(missing.exception))
            report_args["findings"] = [
                "greeting.py line 1 defines the function.",
                "tests/test_greeting.py line 1 imports it.",
            ]
            self.assertEqual(runtime.finish_success(report_args)["status"], "success")
            report_args["findings"] = [
                "Line\u202f1 of greeting.py defines the function.",
                "Line 1 in tests/test_greeting.py imports it.",
            ]
            self.assertEqual(runtime.finish_success(report_args)["status"], "success")
            report_args["findings"] = [
                "greeting.py defines the function. An unrelated line 1 is elsewhere.",
                "tests/test_greeting.py line 1 imports it.",
            ]
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "line citations"):
                runtime.finish_success(report_args)

    def test_compatibility_finish_can_require_regex_search(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Inspect.",
                {
                    "explorer_require_regex_search": True,
                    "explorer_require_trace_symbol": "build_greeting",
                },
                AdaptiveExplorerClient(),
            )
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "requires regex SEARCH"):
                runtime.execute(
                    "FINISH_SUCCESS",
                    {
                        "relevant_files": [],
                        "call_flow": [],
                        "findings": ["done"],
                        "relevant_tests": [],
                        "uncertainties": [],
                    },
                )
            runtime.execute("SEARCH", {"query": "build_.*", "mode": "regex", "glob": "*.py"})
            runtime.execute("READ_FILE", {"path": "greeting.py"})
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "requires TRACE"):
                runtime.execute(
                    "FINISH_SUCCESS",
                    {
                        "relevant_files": [],
                        "call_flow": [],
                        "findings": ["done"],
                        "relevant_tests": [],
                        "uncertainties": [],
                    },
                )
            runtime.execute("TRACE", {"symbol": "build_greeting"})
            _observation, report = runtime.execute(
                "FINISH_SUCCESS",
                {
                    "relevant_files": [
                        {"path": "greeting.py", "reason": "contains the implementation"}
                    ],
                    "call_flow": [],
                    "findings": ["done"],
                    "relevant_tests": [],
                    "uncertainties": [],
                },
            )
            self.assertEqual(report["status"], "success")

    def test_explorer_capability_schema_is_read_only(self) -> None:
        actions = {item["function"]["name"] for item in RUNTIME.EXPLORER_TOOLS}
        self.assertEqual(
            actions,
            {"LIST_FILES", "SEARCH", "READ_FILE", "TRACE", "FINISH_SUCCESS", "FINISH_FAILED"},
        )
        self.assertTrue(actions.isdisjoint({"SAFE_CREATE", "SAFE_REPLACE", "VALIDATE", "SHELL"}))
        search = next(
            item for item in RUNTIME.EXPLORER_TOOLS if item["function"]["name"] == "SEARCH"
        )
        self.assertEqual(
            search["function"]["parameters"]["properties"]["mode"]["enum"],
            ["literal", "regex"],
        )

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

    def test_model_request_error_is_reported_as_infrastructure_failure(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(
                root,
                "Inspect.",
                {"max_explorer_turns": 2},
                InfraFailureClient(),
            )
            report = runtime.run()
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["budget_usage"]["protocol_errors"], 0)
            self.assertEqual(report["infra_failure"]["reason_code"], "http_4xx")
            self.assertEqual(report["infra_failure"]["diagnostics"]["provider_status_code"], 400)

    def test_lmstudio_client_rejects_oversized_input_before_send(self) -> None:
        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1",
            "explorer",
            timeout=9,
            context_length=100,
            context_safety_margin=10,
        )
        with patch.object(RUNTIME.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(RUNTIME.ExplorerModelRequestError) as raised:
                client.complete([{"role": "user", "content": "TASK\n" + "x" * 400}])
        self.assertEqual(raised.exception.reason_code, "input_too_large")
        self.assertEqual(raised.exception.diagnostics["available_input_tokens"], 0)
        self.assertTrue(raised.exception.diagnostics["largest_prompt_sections"])
        urlopen.assert_not_called()

    def test_lmstudio_client_uses_configured_output_reserve(self) -> None:
        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1",
            "explorer",
            timeout=9,
            context_length=32768,
            max_output_tokens=4096,
            required_tool_max_tokens=4096,
        )
        messages = [{"role": "user", "content": "Inspect a.py"}]
        with patch.object(
            RUNTIME.urllib.request,
            "urlopen",
            return_value=io.BytesIO(b'{"choices":[]}'),
        ) as urlopen:
            client._post(messages, require_tool=True)
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(body["max_tokens"], 4096)
        self.assertEqual(client.last_request_stats["max_output_tokens"], 4096)

        with self.assertRaisesRegex(RUNTIME.ExplorerError, "must be positive"):
            RUNTIME.LMStudioClient(
                "http://localhost:1234/v1", "explorer", timeout=9, max_output_tokens=0
            )

    def test_normal_tool_schema_exposes_structured_evidence(self) -> None:
        tools = {item["function"]["name"]: item["function"] for item in RUNTIME.EXPLORER_TOOLS}
        properties = tools["FINISH_SUCCESS"]["parameters"]["properties"]
        self.assertEqual(properties["relevant_files"]["items"]["required"], ["path", "reason"])
        self.assertEqual(properties["citations"]["items"]["required"], ["path", "line", "claim"])
        self.assertIn("defect", tools["FINISH_SUCCESS"]["description"])
        self.assertIn("NOT failure", tools["FINISH_FAILED"]["description"])

    def test_response_metadata_records_actual_usage_without_raw_output(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "explorer", timeout=9)
        payload = {
            "choices": [{"finish_reason": "stop", "message": {"content": "private content"}}],
            "usage": {
                "prompt_tokens": 21,
                "completion_tokens": 5,
                "total_tokens": 26,
                "private_provider_field": "not telemetry",
            },
        }
        with patch.object(client, "_post", return_value=payload):
            self.assertEqual(client.complete([]), "private content")
        self.assertEqual(client.last_request_stats["finish_reason"], "stop")
        self.assertEqual(
            client.last_request_stats["response_usage"],
            {"prompt_tokens": 21, "completion_tokens": 5, "total_tokens": 26},
        )
        self.assertNotIn("private", json.dumps(client.last_request_stats))

    def test_truncated_response_never_returns_even_parseable_partial_action(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "explorer", timeout=9)
        for message in (
            {"content": '{"action":"READ_FILE","path":"greeting.py"}'},
            {
                "tool_calls": [
                    {"function": {"name": "READ_FILE", "arguments": {"path": "greeting.py"}}}
                ]
            },
        ):
            with (
                self.subTest(message=message),
                patch.object(
                    client,
                    "_post",
                    return_value={
                        "choices": [{"finish_reason": "length", "message": message}],
                        "usage": {"completion_tokens": 2048},
                    },
                ) as post,
            ):
                with self.assertRaises(RUNTIME.ExplorerModelRequestError) as raised:
                    client.complete([])
                self.assertEqual(raised.exception.reason_code, "output_token_limit")
                post.assert_called_once()

    def test_lmstudio_client_uses_bounded_temperature_override(self) -> None:
        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1", "explorer", timeout=9, temperature=0
        )
        with patch.object(
            RUNTIME.urllib.request,
            "urlopen",
            return_value=io.BytesIO(b'{"choices":[]}'),
        ) as urlopen:
            client._post([{"role": "user", "content": "Inspect a.py"}])
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(body["temperature"], 0)
        with self.assertRaisesRegex(RUNTIME.ExplorerPreflightBlocked, "between 0 and 2"):
            RUNTIME.LMStudioClient(
                "http://localhost:1234/v1", "explorer", timeout=9, temperature=-0.1
            )

    def test_lmstudio_client_classifies_http_500_with_response_body(self) -> None:
        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1", "explorer", timeout=9, context_length=32768
        )
        error = RUNTIME.urllib.error.HTTPError(
            client.url,
            500,
            "Server Error",
            None,
            io.BytesIO(b'{"error":"model load failed"}'),
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(RUNTIME.ExplorerModelRequestError) as raised:
                client.complete([{"role": "user", "content": "act"}])
        self.assertEqual(raised.exception.reason_code, "http_5xx")
        self.assertEqual(raised.exception.diagnostics["provider_status_code"], 500)
        self.assertIn("model load failed", raised.exception.diagnostics["provider_response_body"])

    def test_lmstudio_client_repairs_peg_native_400_with_required_tool(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "explorer", timeout=9)
        error = RUNTIME.ExplorerModelRequestError(
            "http_4xx", "HTTP 400: peg-native format", {"provider_status_code": 400}
        )
        success = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {"function": {"name": "READ_FILE", "arguments": '{"path":"a.py"}'}}
                        ]
                    }
                }
            ]
        }
        with patch.object(client, "_post", side_effect=[error, success]) as post:
            result = client.complete([{"role": "user", "content": "Inspect a.py"}])
        self.assertEqual(json.loads(result)["action"], "READ_FILE")
        self.assertEqual(post.call_args_list[1].kwargs, {"require_tool": True})
        self.assertEqual(client.last_request_stats["peg_native_retry_attempts"], 1)

    def test_lmstudio_client_merges_adjacent_roles_only_after_matching_400(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "explorer", timeout=9)
        error = RUNTIME.ExplorerModelRequestError(
            "http_4xx",
            "HTTP 400: roles must alternate user and assistant roles",
            {"provider_status_code": 400},
        )
        success = {"choices": [{"message": {"content": '{"action":"READ_FILE","path":"a.py"}'}}]}
        messages = [
            {"role": "system", "content": "Rules"},
            {"role": "user", "content": "Task"},
            {"role": "user", "content": "Hints"},
        ]
        with patch.object(client, "_post", side_effect=[error, success]) as post:
            result = client.complete(messages)
        self.assertEqual(json.loads(result)["action"], "READ_FILE")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(
            post.call_args_list[1].args[0],
            [
                {"role": "system", "content": "Rules"},
                {"role": "user", "content": "Task\n\nHints"},
            ],
        )
        self.assertEqual(client.last_request_stats["role_alternation_retry_attempts"], 1)

        with patch.object(client, "_post", side_effect=error) as post:
            with self.assertRaises(RUNTIME.ExplorerModelRequestError):
                client.complete([{"role": "user", "content": "Already alternating"}])
        self.assertEqual(post.call_count, 1)

    def test_empty_response_repair_keeps_roles_alternating_after_merge(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "explorer", timeout=9)
        error = RUNTIME.ExplorerModelRequestError(
            "http_4xx",
            "HTTP 400: roles must alternate user and assistant roles",
            {"provider_status_code": 400},
        )
        empty = {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]}
        success = {"choices": [{"message": {"content": '{"action":"READ_FILE","path":"a.py"}'}}]}
        messages = [
            {"role": "system", "content": "Rules"},
            {"role": "user", "content": "Task"},
            {"role": "user", "content": "Hints"},
        ]
        with patch.object(client, "_post", side_effect=[error, empty, success]) as post:
            result = client.complete(messages)
        self.assertEqual(json.loads(result)["action"], "READ_FILE")
        retry_messages = post.call_args_list[2].args[0]
        self.assertEqual([item["role"] for item in retry_messages], ["system", "user"])
        self.assertIn("Task\n\nHints", retry_messages[1]["content"])
        self.assertIn("previous response had no executable action", retry_messages[1]["content"])

    def test_output_length_failure_is_infrastructure_not_worker_quality(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "explorer", timeout=9)
        truncated = {
            "choices": [
                {"message": {"content": "", "reasoning": "unfinished"}, "finish_reason": "length"}
            ]
        }
        with patch.object(client, "_post", side_effect=[truncated, truncated]):
            with self.assertRaises(RUNTIME.ExplorerModelRequestError) as raised:
                client.complete([{"role": "user", "content": "Inspect a.py"}])
        self.assertEqual(raised.exception.reason_code, "output_token_limit")
        self.assertEqual(raised.exception.diagnostics["rejection_reason"], "output_token_limit")

    def test_lmstudio_client_does_not_retry_unrelated_http_400(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "explorer", timeout=9)
        error = RUNTIME.ExplorerModelRequestError(
            "http_4xx", "HTTP 400: invalid model", {"provider_status_code": 400}
        )
        with patch.object(client, "_post", side_effect=error) as post:
            with self.assertRaises(RUNTIME.ExplorerModelRequestError):
                client.complete([{"role": "user", "content": "Inspect a.py"}])
        self.assertEqual(post.call_count, 1)

    def test_lmstudio_client_classifies_transport_timeout(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "explorer", timeout=9)
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(RUNTIME.ExplorerModelRequestError) as raised:
                client.complete([{"role": "user", "content": "act"}])
        self.assertEqual(raised.exception.reason_code, "model_request_timeout")

    def test_trace_returns_definition_and_call_edges_with_line_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "flow.py").write_text(
                "def helper():\n    return 1\n\n"
                "def build_greeting():\n    return helper()\n\n"
                "def caller():\n    return build_greeting()\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.ExplorerRuntime(
                root, "Trace build_greeting.", {"max_explorer_turns": 4}, FailIfCalledClient()
            )
            result = runtime.trace({"symbol": "build_greeting"})
            self.assertEqual(result["definitions"][0]["line"], 4)
            self.assertEqual(result["outgoing"][0]["callee"], "helper")
            self.assertEqual(result["incoming"][0]["caller"], "caller")
            self.assertEqual(result["observed_files"], ["flow.py"])
            self.assertIn("flow.py", runtime.read_files)
            self.assertTrue(runtime.read_hashes["flow.py"])

    def test_successful_exploration_guides_new_question_but_stale_files_drop_out(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            first = RUNTIME.ExplorerRuntime(
                root,
                "Locate greeting.",
                {"max_explorer_turns": 8},
                AdaptiveExplorerClient(),
                "task-a",
            ).run()
            self.assertEqual(first["status"], "success")
            second_client = AdaptiveExplorerClient()
            second = RUNTIME.ExplorerRuntime(
                root, "Locate greeting tests.", {"max_explorer_turns": 8}, second_client, "task-a"
            ).run()
            self.assertEqual(second["status"], "success")
            hints = [
                message
                for message in second_client.messages_seen[0]
                if message["content"].startswith("REPOSITORY_HINTS\n")
            ]
            self.assertEqual(len(hints), 1)
            self.assertIn("greeting.py", hints[0]["content"])
            (root / "greeting.py").write_text("def build_greeting(): return 1\n", encoding="utf-8")
            memory = RUNTIME.EVIDENCE_CACHE.EvidenceCache(root).navigation_hints(task_id="task-a")
            paths = [file["path"] for item in memory for file in item["files"]]
            self.assertNotIn("greeting.py", paths)
            self.assertIn("tests/test_greeting.py", paths)

    def test_accepted_change_refreshes_path_hint_without_claiming_semantics(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            cache = RUNTIME.EVIDENCE_CACHE.EvidenceCache(root)
            self.assertTrue(cache.record_accepted_paths("task-a", "run-a", ["greeting.py"]))
            hints = cache.navigation_hints(task_id="task-a")
            self.assertEqual(hints[0]["files"][0]["path"], "greeting.py")
            self.assertIn("inspect current code", hints[0]["source_question"])
            (root / "greeting.py").write_text("VALUE = 9\n", encoding="utf-8")
            self.assertEqual(cache.navigation_hints(task_id="task-a"), [])

    def test_navigation_hints_respect_read_scope_and_forbidden_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            cache = RUNTIME.EVIDENCE_CACHE.EvidenceCache(root)
            self.assertTrue(
                cache.record_accepted_paths(
                    "task-a", "run-a", ["greeting.py", "tests/test_greeting.py"]
                )
            )
            hints = cache.navigation_hints(
                task_id="task-a", readable=["tests"], forbidden=["tests/test_greeting.py"]
            )
            self.assertEqual(hints, [])
            hints = cache.navigation_hints(task_id="task-a", readable=["tests"])
            self.assertEqual(
                [file["path"] for hint in hints for file in hint["files"]],
                ["tests/test_greeting.py"],
            )

    def test_malformed_repo_map_does_not_break_navigation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            cache = RUNTIME.EVIDENCE_CACHE.EvidenceCache(root)
            cache.path.parent.mkdir(parents=True)
            cache.path.write_text(
                json.dumps({"entries": {"bad": {"report": "not an object"}}}),
                encoding="utf-8",
            )
            self.assertEqual(cache.navigation_hints(task_id="task-a"), [])

    def test_exact_exploration_is_reused_only_while_repo_fingerprint_matches(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            task_state_path = root / ".agent" / "tasks" / "task-1" / "state.json"
            task_state_path.parent.mkdir(parents=True)
            task_state_path.write_text(
                json.dumps(
                    {
                        "task_id": "task-1",
                        "current_unit_id": "unit-1",
                        "execution_history": [],
                        "recent_attempts": [],
                        "usage": {"coder_calls": 0, "explorer_calls": 0},
                    }
                ),
                encoding="utf-8",
            )
            (root / ".agent" / "current-task.json").write_text(
                json.dumps(
                    {
                        "task_id": "task-1",
                        "unit_id": "unit-1",
                        "task_state": ".agent/tasks/task-1/state.json",
                    }
                ),
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
            self.assertEqual(
                state_after_cache["recent_attempts"][-1]["diagnostic_log"],
                first["diagnostic_log"],
            )
            self.assertTrue((root / first["diagnostic_log"]).is_file())
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

    def test_explicit_task_id_links_exploration_before_current_task_exists(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            report = RUNTIME.ExplorerRuntime(
                root,
                "Trace greeting flow.",
                {"max_explorer_turns": 8},
                AdaptiveExplorerClient(),
                "feature-1",
            ).run()
            state_path = root / ".agent" / "tasks" / "feature-1" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["usage"]["explorer_calls"], 1)
            self.assertEqual(
                state["recent_attempts"][0]["diagnostic_report"],
                report["diagnostic_report"],
            )
            archived = json.loads((root / report["diagnostic_report"]).read_text(encoding="utf-8"))
            self.assertEqual(archived["status"], "success")
            self.assertEqual(archived["task_id"], "feature-1")
            self.assertFalse((root / ".agent" / "current-task.json").exists())

    def test_explicit_task_id_rejects_path_components(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            with self.assertRaises(RUNTIME.ExplorerPreflightBlocked):
                RUNTIME.ExplorerRuntime(root, "Inspect.", {}, AdaptiveExplorerClient(), "..")
            self.assertFalse((root / ".agent").exists())

    def test_unread_file_cannot_be_cited_as_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(
                root, "Inspect.", {"max_explorer_turns": 2}, AdaptiveExplorerClient()
            )
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

    def test_repeated_empty_search_stops_before_turn_budget(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = RepeatingClient()
            report = RUNTIME.ExplorerRuntime(
                root,
                "Find absent symbol in Python files.",
                {"max_explorer_turns": 16, "max_explorer_protocol_errors": 6},
                client,
            ).run()
            self.assertEqual(report["status"], "failed")
            self.assertIn("no new evidence", report["failure_reason"])
            self.assertLess(client.step, 16)
            self.assertEqual(report["budget_usage"]["searches"], 1)

    def test_search_defaults_to_literal_and_regex_requires_explicit_mode(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "greeting.py").write_text(
                '@app.post("/v1/evaluations", status_code=202)\n', encoding="utf-8"
            )
            runtime = RUNTIME.ExplorerRuntime(root, "Find route.", {}, AdaptiveExplorerClient())
            literal = runtime.search(
                {"path": "greeting.py", "query": '@app.post("/v1/evaluations"'}
            )
            self.assertEqual(literal["mode"], "literal")
            self.assertEqual(len(literal["results"]), 1)
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "retry with mode literal"):
                runtime.search(
                    {
                        "path": "greeting.py",
                        "query": '@app.post("/v1/evaluations"',
                        "mode": "regex",
                    }
                )

    def test_explorer_rejects_repository_absence_claim_after_positive_match(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Find greeting.", {}, AdaptiveExplorerClient())
            runtime.search({"path": "greeting.py", "query": "build_greeting"})
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "conflicts with positive SEARCH"):
                runtime.execute(
                    "FINISH_FAILED",
                    {
                        "summary": ["The repository lacks this code."],
                        "reason": "Missing greeting implementation in the repository",
                        "uncertainties": [],
                    },
                )

    def test_unrelated_positive_search_does_not_block_specific_absence_claim(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Find symbol.", {}, AdaptiveExplorerClient())
            runtime.search({"path": "greeting.py", "query": "build_greeting"})
            runtime.search({"path": "greeting.py", "query": "missing_symbol"})
            _observation, final = runtime.execute(
                "FINISH_FAILED",
                {
                    "summary": ["The repository lacks missing_symbol."],
                    "reason": "No matching symbol in the scoped file.",
                    "uncertainties": ["Other paths were not inspected."],
                },
            )
            self.assertEqual(final["status"], "failed")

    def test_diagnostic_log_is_bounded_and_can_be_disabled(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            report = RUNTIME.ExplorerRuntime(
                root, "Find absent symbol.", {"max_explorer_turns": 4}, RepeatingClient()
            ).run()
            log_path = root / report["diagnostic_log"]
            records = [
                json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(records[0]["event"], "start")
            self.assertEqual(records[-1]["event"], "finish")
            self.assertEqual(len(list((root / ".agent" / "explorer-runs").iterdir())), 1)
            turns = [item for item in records if item["event"] == "turn"]
            self.assertTrue(turns)
            self.assertIn("query_sha256", turns[0]["facts"])
            self.assertNotIn("absent-symbol", log_path.read_text(encoding="utf-8"))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            report = RUNTIME.ExplorerRuntime(
                root,
                "Find absent symbol.",
                {"max_explorer_turns": 4, "diagnostic_logging": False},
                RepeatingClient(),
            ).run()
            self.assertNotIn("diagnostic_log", report)
            self.assertFalse((root / ".agent" / "explorer-runs").exists())

    def test_nonexistent_test_cannot_be_cited_in_final_report(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(root, "Inspect.", {}, AdaptiveExplorerClient())
            runtime.read_file({"path": "greeting.py"})
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "unread test file"):
                runtime.finish_success(
                    {
                        "relevant_files": ["greeting.py"],
                        "findings": ["Observed implementation."],
                        "relevant_tests": ["tests/missing.py"],
                    }
                )

    def test_requested_test_evidence_must_include_observed_test_path(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.ExplorerRuntime(
                root, "Inspect source and test lines.", {}, AdaptiveExplorerClient()
            )
            runtime.read_file({"path": "greeting.py"})
            runtime.read_file({"path": "tests/test_greeting.py"})
            with self.assertRaisesRegex(RUNTIME.ExplorerError, "relevant_tests must include"):
                runtime.finish_success(
                    {
                        "relevant_files": ["greeting.py"],
                        "call_flow": [],
                        "findings": ["greeting.py line 1 defines the behavior."],
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
            with (
                patch.object(
                    RUNTIME, "is_reparse_point", side_effect=lambda path: path.name == "linked"
                ),
                self.assertRaisesRegex(RUNTIME.ExplorerError, "reparse point"),
            ):
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
            self.assertEqual(report["interruption"]["reason_code"], "invocation_deadline_exceeded")

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
            "<|channel|>commentary to=repo_browser.list_files "
            '<|constrain|>json<|message|>{"path":"","max_results":200}'
        )
        self.assertEqual(parsed["action"], "LIST_FILES")
        self.assertEqual(parsed["arguments"]["max_results"], 200)

        code_variant = RUNTIME.parse_action(
            '<|channel|>commentary to=repo_browser.read_file code<|message|>{"path":"greeting.py"}'
        )
        self.assertEqual(code_variant["action"], "READ_FILE")

        final_variant = RUNTIME.parse_action(
            '<|channel|>final <|constrain|>JSON<|message|>{"action":"LIST_FILES","path":""}'
        )
        self.assertEqual(final_variant["action"], "LIST_FILES")

        finish_variant = RUNTIME.parse_action(
            "<|channel|>final to=repo_browser.finish_success"
            "<|channel|>commentary code<|message|>"
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
        self.assertFalse(compact["findings_truncated"])
        report["findings"] = ["x" * 801]
        truncated = RUNTIME.compact_explorer_report(report)
        self.assertTrue(truncated["findings_truncated"])
        self.assertEqual(len(truncated["findings"][0]), 800)
        self.assertNotIn("action_trace", compact)
        self.assertNotIn("protocol_error_details", compact)


if __name__ == "__main__":
    unittest.main()
