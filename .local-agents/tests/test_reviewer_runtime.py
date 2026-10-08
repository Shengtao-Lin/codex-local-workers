from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "reviewer-runtime.py"
SPEC = importlib.util.spec_from_file_location("reviewer_runtime_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
REVIEWER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REVIEWER
SPEC.loader.exec_module(REVIEWER)


class FakeClient:
    def __init__(self, actions: list[dict]) -> None:
        self.actions = list(actions)
        self.messages_seen: list[list[dict]] = []

    def complete(self, messages):
        self.messages_seen.append(list(messages))
        return json.dumps(self.actions.pop(0))


class ReviewerRuntimeTests(unittest.TestCase):
    def test_budgeted_retention_keeps_long_read_chain_when_it_fits(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            client = FakeClient([])
            client.context_length = 24576
            client.max_tokens = 4096
            runtime = REVIEWER.ReviewerRuntime(
                root, self.make_run(root), {"reviewer_context_retention": "budgeted"}, client
            )
            messages = [
                {"role": "system", "content": "rules"},
                {"role": "user", "content": "packet"},
            ]
            for i in range(9):
                messages.extend(
                    [
                        {"role": "assistant", "content": "READ_FILE"},
                        {
                            "role": "user",
                            "content": "OBSERVATION\n"
                            + json.dumps({"path": f"src/{i}.py", "content": "1: value = 1"}),
                        },
                    ]
                )
            retained = runtime._trim_messages(messages)
            self.assertEqual(retained, messages)
            runtime._update_active_read_context(retained)
            self.assertEqual(len(runtime.active_read_lines), 9)
            runtime.context_retention = "recent"
            runtime._update_active_read_context(runtime._trim_messages(messages))
            self.assertEqual(len(runtime.active_read_lines), 5)

    def test_budgeted_retention_bounds_history_without_dropping_contract_or_recent_evidence(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            client = FakeClient([])
            client.context_length = 6000
            client.max_tokens = 2000
            runtime = REVIEWER.ReviewerRuntime(
                root, self.make_run(root), {"reviewer_context_retention": "budgeted"}, client
            )
            messages = [{"role": "user", "content": str(i) + "x" * 1000} for i in range(40)]
            retained = runtime._trim_messages(messages)
            self.assertEqual(retained[:2], messages[:2])
            self.assertEqual(retained[-10:], messages[-10:])
            self.assertLess(len(retained), len(messages))
            self.assertEqual(len(messages), 40)
            client.context_length = 1000000
            self.assertLessEqual(len(runtime._trim_messages(messages * 4)), 64)
            client.context_length = None
            with self.assertRaisesRegex(REVIEWER.ReviewError, "configured context"):
                runtime._trim_messages(messages)

    def test_evicted_read_keeps_investigation_tools_available_in_real_loop(self):
        class NativeClient(FakeClient):
            native_tools = REVIEWER.REVIEW_NATIVE_TOOLS
            native_tool_choice = "auto"

            def complete(self, messages):
                if len(self.messages_seen) == 8:
                    self.restored = json.loads(messages[-1]["content"].split("\n", 1)[1])
                    self.available = [t["function"]["name"] for t in self.native_tools]
                return super().complete(messages)

        with TemporaryDirectory() as directory:
            root = Path(directory)

            def read(path):
                return {"action": "READ_FILE", "arguments": {"path": path}}

            client = NativeClient(
                [
                    read("src/example.py"),
                    read("tests/test_example.py"),
                    *[
                        {"action": "SEARCH", "arguments": {"query": f"missing_{i}"}}
                        for i in range(5)
                    ],
                    read("src/example.py"),
                    read("tests/test_example.py"),
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "pass_to_primary",
                            "findings": [],
                            "verified_contract_ids": ["behavior-1"],
                            "verified_check_ids": [],
                            "ordering_review": [],
                            "contract_review": [],
                            "unverified_claims": [],
                        },
                    },
                ]
            )
            runtime = REVIEWER.ReviewerRuntime(
                root, self.make_run(root), {"reviewer_context_recovery": True}, client
            )
            report = runtime.run()
            self.assertEqual(report["decision"], "pass_to_primary")
            self.assertEqual(client.restored["status"], "context_restored")
            self.assertIn("SEARCH", client.available)
            self.assertIn("READ_FILE", client.available)

    def test_context_recovery_restores_evicted_source_without_forcing_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = REVIEWER.ReviewerRuntime(
                root, self.make_run(root), {"reviewer_context_recovery": True}, FakeClient([])
            )
            source = runtime.read_file({"path": "src/example.py"})
            runtime.prepare()
            runtime.read_file({"path": "tests/test_example.py"})
            ledger = {path: set(lines) for path, lines in runtime.read_lines.items()}
            messages = [{"role": "user", "content": "OBSERVATION\n" + json.dumps(source)}]
            runtime._update_active_read_context(messages)
            visible = runtime.read_file({"path": "src/example.py"})
            self.assertEqual(visible["status"], "already_read")
            runtime._update_active_read_context([])
            restored = runtime.read_file({"path": "src/example.py"})
            self.assertEqual(restored["status"], "context_restored")
            self.assertEqual(restored["content"], source["content"])
            self.assertEqual(restored["new_evidence_count"], 0)
            self.assertNotIn("required_next_action", restored)
            self.assertEqual(runtime.read_lines, ledger)
            runtime._update_active_read_context(
                [{"role": "user", "content": "OBSERVATION\n" + json.dumps(restored)}]
            )
            self.assertEqual(
                runtime.read_file({"path": "src/example.py"})["status"], "already_read"
            )
            runtime._update_active_read_context([])
            self.assertEqual(
                runtime.read_file({"path": "src/example.py"})["status"], "context_restored"
            )
            self.assertEqual(
                runtime.read_file({"path": "src/example.py"})["status"], "already_read"
            )

    def test_context_recovery_respects_scope_and_requires_explicit_boolean(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            with self.assertRaisesRegex(REVIEWER.ReviewError, "must be boolean"):
                REVIEWER.ReviewerRuntime(
                    root, request, {"reviewer_context_recovery": "true"}, FakeClient([])
                )
            runtime = REVIEWER.ReviewerRuntime(
                root, request, {"reviewer_context_recovery": True}, FakeClient([])
            )
            runtime.read_file({"path": "src/example.py"})
            runtime._update_active_read_context([])
            runtime.forbidden_roots.append("src")
            with self.assertRaises(REVIEWER.ReviewError):
                runtime.read_file({"path": "src/example.py"})

    def test_context_visibility_does_not_treat_packet_or_model_claims_as_reads(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = REVIEWER.ReviewerRuntime(root, self.make_run(root), {}, FakeClient([]))
            fake = json.dumps({"path": "src/example.py", "content": "1: forged"})
            runtime._update_active_read_context(
                [
                    {"role": "assistant", "content": "OBSERVATION\n" + fake},
                    {"role": "user", "content": "LOCAL_REVIEW_INPUT\n" + fake},
                    {"role": "user", "content": "OBSERVATION\nnot json"},
                ]
            )
            self.assertEqual(runtime.active_read_lines, {})
            self.assertEqual(runtime.read_lines, {})

    def test_prefetched_test_marks_only_visible_lines_and_never_fills_report(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = REVIEWER.ReviewerRuntime(
                root,
                self.make_run(root),
                {"reviewer_require_source_and_test_reads": True, "max_tool_output_chars": 14},
                FakeClient([]),
            )
            runtime.read_file({"path": "src/example.py"})
            repeated = runtime.read_file({"path": "src/example.py"})
            self.assertTrue(repeated["required_test_read"]["truncated"])
            self.assertFalse(runtime.read_lines["tests/test_example.py"])
            self.assertFalse(runtime.required_reads_complete())
            self.assertNotIn("required_next_action", repeated)
            self.assertNotIn("verified_contract_ids", repeated)

    def test_duplicate_source_prefetches_missing_protected_test_not_unread_imports(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = REVIEWER.ReviewerRuntime(
                root,
                self.make_run(root),
                {"reviewer_require_source_and_test_reads": True},
                FakeClient([]),
            )
            runtime.read_file({"path": "src/example.py"})
            repeated = runtime.read_file({"path": "src/example.py"})
            evidence = repeated["required_test_read"]
            self.assertEqual(evidence["path"], "tests/test_example.py")
            self.assertIn("assert True", evidence["content"])
            self.assertEqual(runtime.read_lines["tests/test_example.py"], {1, 2})
            self.assertEqual(repeated["required_next_action"], "REPORT")

    def test_duplicate_prefetch_does_not_bypass_forbidden_test_scope(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = REVIEWER.ReviewerRuntime(
                root,
                self.make_run(root),
                {"reviewer_require_source_and_test_reads": True},
                FakeClient([]),
            )
            runtime.forbidden_roots.append("tests")
            runtime.read_file({"path": "src/example.py"})
            repeated = runtime.read_file({"path": "src/example.py"})
            self.assertNotIn("required_test_read", repeated)
            self.assertNotIn("REPORT", repeated.get("required_next_action", ""))
            self.assertFalse(runtime.required_reads_complete())
            self.assertNotIn("tests/test_example.py", runtime.read_lines)

    def test_prompt_checks_cleanup_failures_without_requiring_code_shape(self) -> None:
        prompt = REVIEWER.ReviewerRuntime.system_prompt(type("Runtime", (), {"config": {}})())
        self.assertIn("cleanup operations", prompt)
        self.assertIn("which exception", prompt)
        self.assertIn("not a preferred implementation shape", prompt)
        self.assertIn("contract permits cleanup errors", prompt)

    def test_prompt_names_exact_contract_review_status_values(self) -> None:
        prompt = REVIEWER.ReviewerRuntime.system_prompt(type("Runtime", (), {"config": {}})())
        self.assertIn('"verified", "violated", or "uncertain"', prompt)
        self.assertIn('use "violated"', prompt)

    def test_prompt_distinguishes_pending_units_without_suppressing_regressions(self) -> None:
        prompt = REVIEWER.ReviewerRuntime.system_prompt(type("Runtime", (), {"config": {}})())
        self.assertIn("owned_contract_ids and required_behavior", prompt)
        self.assertIn("explicitly assigns receipt composition elsewhere", prompt)
        self.assertIn("unverified_claims", prompt)
        self.assertIn("Read-only location alone never excludes a genuine regression", prompt)
        self.assertIn("escalate with evidence", prompt)

    def test_reasoning_strength_is_optional_and_bounded(self) -> None:
        default = REVIEWER.ReviewerRuntime.system_prompt(type("Runtime", (), {"config": {}})())
        self.assertNotIn("Reasoning strength:", default)
        low = REVIEWER.ReviewerRuntime.system_prompt(
            type("Runtime", (), {"config": {"reviewer_reasoning_strength": "low"}})()
        )
        self.assertIn("Reasoning strength: low.", low)
        with self.assertRaisesRegex(REVIEWER.ReviewError, "reviewer_reasoning_strength"):
            REVIEWER.ReviewerRuntime.system_prompt(
                type("Runtime", (), {"config": {"reviewer_reasoning_strength": "invalid"}})()
            )
        with self.assertRaisesRegex(REVIEWER.ReviewError, "reviewer_reasoning_strength"):
            REVIEWER.ReviewerRuntime.system_prompt(
                type("Runtime", (), {"config": {"reviewer_reasoning_strength": []}})()
            )

    def test_native_tool_prompt_and_allowlist_are_read_only(self) -> None:
        prompt = REVIEWER.ReviewerRuntime.system_prompt(
            type("Runtime", (), {"config": {"reviewer_native_tools": True}})()
        )
        self.assertIn("exactly one provided native tool call", prompt)
        self.assertEqual(
            {item["function"]["name"] for item in REVIEWER.REVIEW_NATIVE_TOOLS},
            {"READ_FILE", "SEARCH", "RUN_APPROVED_TEST", "RUN_APPROVED_STATIC_CHECK", "REPORT"},
        )

    def test_native_report_schema_covers_template_and_ordering_evidence(self) -> None:
        report = next(
            tool["function"]
            for tool in REVIEWER.REVIEW_NATIVE_TOOLS
            if tool["function"]["name"] == "REPORT"
        )
        parameters = report["parameters"]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = REVIEWER.ReviewerRuntime(
                root, self.make_run(root, risk="high", ordering=True), {}, FakeClient([])
            )
            self.assertLessEqual(
                set(runtime.report_template()["arguments"]), set(parameters["properties"])
            )
        self.assertIn("ordering_review", parameters["required"])
        item = parameters["properties"]["ordering_review"]["items"]
        self.assertEqual(
            set(item["required"]),
            {"constraint_id", "status", "evidence_type", "path", "line", "evidence"},
        )
        self.assertIn("uncertain", item["properties"]["status"]["enum"])
        self.assertIn("null", item["properties"]["line"]["type"])
        self.assertIn("diff", item["properties"]["evidence_type"]["enum"])

    def test_compatibility_pass_can_require_search(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(
                root, request, {"reviewer_require_search": True}, FakeClient([])
            )
            runtime.prepare()
            args = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "verified_check_ids": [],
                "ordering_review": [],
                "contract_review": [],
                "unverified_claims": [],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "requires one successful SEARCH"):
                runtime.validate_report(args)
            repair = runtime.report_repair("requires one successful SEARCH", args)
            self.assertEqual(repair["required_actions"][0]["action"], "SEARCH")
            self.assertEqual(
                repair["required_actions"][0]["arguments"],
                {"query": "VALUE = 2", "path": "src/example.py"},
            )
            self.assertEqual(
                runtime.empty_search_repair()["suggested_action"],
                {
                    "action": "SEARCH",
                    "arguments": {"query": "VALUE = 2", "path": "src/example.py"},
                },
            )
            with self.assertRaisesRegex(REVIEWER.WORKER.WorkerError, "query"):
                runtime.search({"query": "", "path": "src"})
            self.assertEqual(runtime.search_count, 0)
            found = runtime.search({"query": "VALUE", "path": "src", "glob": "**/src/example.py"})
            self.assertEqual(found["results"][0]["path"], "src/example.py")
            self.assertEqual(runtime.validate_report(args)["decision"], "pass_to_primary")

    def test_reviewer_capability_schema_excludes_edits_shell_git_and_delegation(self) -> None:
        actions = set(REVIEWER.REVIEW_ACTION_SCHEMA["properties"]["action"]["enum"])
        self.assertEqual(
            actions,
            {
                "READ_FILE",
                "SEARCH",
                "RUN_APPROVED_TEST",
                "RUN_APPROVED_STATIC_CHECK",
                "REPORT",
            },
        )
        self.assertTrue(
            actions.isdisjoint({"SAFE_CREATE", "SAFE_REPLACE", "SHELL", "GIT", "DELEGATE"})
        )

    def make_run(
        self,
        root: Path,
        *,
        risk: str = "small",
        ordering: bool = False,
        configured_checks: list[dict] | None = None,
        source_content: str = "VALUE = 2\n",
        review_feedback: list[dict | str] | None = None,
    ) -> dict:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "example.py").write_text(source_content, encoding="utf-8")
        (root / "tests" / "test_example.py").write_text(
            "def test_value():\n    assert True\n", encoding="utf-8"
        )
        packet = {
            "schema_version": 2,
            "task_id": "task-1",
            "feature_id": "feature-1",
            "unit_id": "unit-1",
            "run_id": "run-1",
            "goal": "Change the value.",
            "risk": {
                "feature": "high",
                "unit": risk,
                "integration": "high",
                "reasons": ["Test risk routing."],
            },
            "scope": {
                "read": ["src", "tests"],
                "readonly": ["tests/test_example.py"],
                "modify": ["src/example.py"],
                "create": [],
                "forbidden": [],
            },
            "required_behavior": [{"id": "behavior-1", "text": "VALUE is two."}],
            "owned_contract_ids": ["behavior-1"],
            "acceptance_criteria": [{"id": "accept-1", "text": "Tests pass."}],
            "acceptance_scenarios": [{"id": "normal", "text": "Read VALUE."}],
            "focused_tests": ["tests/test_example.py"],
            "validation_profile": "python-focused",
            "review_feedback": review_feedback or [],
        }
        if ordering:
            packet["required_order"] = ["Resolve timeout inside the protected block."]
            packet["forbidden_orderings"] = ["Read timeout before entering the protected block."]
        run_root = root / ".agent" / "tasks" / "task-1" / "runs" / "run-1"
        run_root.mkdir(parents=True)
        (run_root / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
        (run_root / "handoff.json").write_text(
            json.dumps({"status": "ready_for_review", "worker_claims": {"summary": []}}),
            encoding="utf-8",
        )
        (run_root / "validation.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "focused_tests": {"status": "passed"},
                    "configured_checks": configured_checks or [],
                }
            ),
            encoding="utf-8",
        )
        (run_root / "post-state.json").write_text(
            json.dumps(
                {
                    "validation_inputs": REVIEWER.RUN_STATE.facts_for_paths(
                        root, ["src/example.py", "tests/test_example.py"]
                    )
                }
            ),
            encoding="utf-8",
        )
        (run_root / "cumulative.diff").write_text(
            "--- a/src/example.py\n+++ b/src/example.py\n@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n",
            encoding="utf-8",
        )
        (run_root / "completed.json").write_text(
            json.dumps({"status": "ready_for_review"}), encoding="utf-8"
        )
        return {
            "schema_version": 1,
            "task_id": "task-1",
            "unit_id": "unit-1",
            "run_id": "run-1",
            "review_id": "review-1",
        }

    def test_pass_routes_small_unit_to_primary_evidence_acceptance(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            client = FakeClient(
                [
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "pass_to_primary",
                            "findings": [],
                            "verified_contract_ids": ["behavior-1"],
                            "unverified_claims": [],
                        },
                    }
                ]
            )
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            self.assertEqual(report["review_route"], "primary_evidence_acceptance")
            self.assertTrue(
                (
                    root / ".agent" / "tasks" / "task-1" / "reviews" / "review-1" / "completed.json"
                ).is_file()
            )
            events = (
                root / ".agent" / "tasks" / "task-1" / "reviews" / "review-1" / "events.jsonl"
            ).read_text(encoding="utf-8")
            self.assertIn("diagnostic_action", events)
            self.assertIn("response_sha256", events)

    def test_reviewer_preloads_model_before_inference(self) -> None:
        class ReadyClient(FakeClient):
            def __init__(self, actions):
                super().__init__(actions)
                self.load_timeout = None

            def ensure_loaded(self, *, timeout_seconds):
                self.load_timeout = timeout_seconds

            def complete(self, messages):
                assert self.load_timeout == 420
                return super().complete(messages)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            client = ReadyClient(
                [
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "pass_to_primary",
                            "findings": [],
                            "verified_contract_ids": ["behavior-1"],
                            "unverified_claims": [],
                        },
                    }
                ]
            )
            report = REVIEWER.ReviewerRuntime(
                root,
                request,
                {"reviewer_preload_model": True, "reviewer_model_load_timeout_seconds": 420},
                client,
            ).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            self.assertEqual(client.load_timeout, 420)

    def test_runtime_falls_back_when_substantive_structured_output_is_rejected(self) -> None:
        class StructuredThenPlainClient(FakeClient):
            def __init__(self, actions: list[dict]) -> None:
                super().__init__(actions)
                self.structured_output = True
                self.temperature = 0.1
                self.model = "muse"
                self.protocol_fallback_model = "qwen"
                self.calls = 0

            def probe_structured_output(self) -> str:
                return "structured_supported"

            def complete(self, messages):
                self.calls += 1
                if self.calls <= 3:
                    raise REVIEWER.WORKER.WorkerError(
                        "LM Studio request failed: HTTP Error 400: Bad Request; "
                        "response: model output does not match the expected peg-native format"
                    )
                return super().complete(messages)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            client = StructuredThenPlainClient(
                [
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "pass_to_primary",
                            "findings": [],
                            "verified_contract_ids": ["behavior-1"],
                            "unverified_claims": [],
                        },
                    }
                ]
            )
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            self.assertFalse(client.structured_output)
            self.assertEqual(client.calls, 4)
            self.assertEqual(client.temperature, 0.1)
            self.assertEqual(client.model, "qwen")
            events = (
                root / ".agent" / "tasks" / "task-1" / "reviews" / "review-1" / "events.jsonl"
            ).read_text(encoding="utf-8")
            self.assertIn("unstructured_runtime_fallback", events)
            self.assertIn("deterministic_plain_json_retry", events)
            self.assertIn("protocol_fallback_model", events)

    def test_report_waiting_only_for_approved_execution_finalizes_after_last_check(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            configured = [
                {"id": "ruff-check", "status": "passed"},
            ]
            request = self.make_run(root, configured_checks=configured)
            report = {
                "action": "REPORT",
                "arguments": {
                    "decision": "pass_to_primary",
                    "findings": [],
                    "verified_contract_ids": ["behavior-1"],
                    "verified_check_ids": ["ruff-check"],
                    "unverified_claims": [],
                },
            }
            client = FakeClient(
                [
                    report,
                    {
                        "action": "RUN_APPROVED_TEST",
                        "arguments": {"test_id": "focused-tests"},
                    },
                    {
                        "action": "RUN_APPROVED_STATIC_CHECK",
                        "arguments": {"check_id": "ruff-check"},
                    },
                ]
            )
            config = {
                "reviewer_require_approved_execution": True,
                "validation_profiles": {
                    "python-focused": {
                        "python": sys.executable,
                        "pytest_argv": ["-B", "-m", "pytest", "-q"],
                        "commands": [
                            {
                                "id": "ruff-check",
                                "argv": ["{python}", "-c", "raise SystemExit(0)"],
                            }
                        ],
                    }
                },
            }
            result = REVIEWER.ReviewerRuntime(root, request, config, client).run()
            self.assertEqual(result["decision"], "pass_to_primary")
            self.assertEqual(len(client.messages_seen), 3)
            events = (
                root / ".agent" / "tasks" / "task-1" / "reviews" / "review-1" / "events.jsonl"
            ).read_text(encoding="utf-8")
            self.assertIn("deferred_report_finalized", events)

    def test_reviewer_receives_contract_and_diff_without_coder_self_assessment(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            run_root = root / ".agent" / "tasks" / "task-1" / "runs" / "run-1"
            handoff = json.loads((run_root / "handoff.json").read_text())
            handoff["worker_claims"] = {"summary": ["Trust me, the implementation is perfect."]}
            (run_root / "handoff.json").write_text(json.dumps(handoff), encoding="utf-8")
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            payload = runtime.initial_payload()
            self.assertNotIn("coder_claims", payload)
            self.assertNotIn("implementation_guidance", payload)
            self.assertNotIn("navigation_hints", payload)
            self.assertIn("cumulative_diff", payload)
            self.assertIn("runtime_validation", payload)

    def test_independent_pass_requires_changed_source_and_focused_test_reads(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(
                root, request, {"reviewer_require_source_and_test_reads": True}, FakeClient([])
            )
            report = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "changed source file"):
                runtime.validate_report(report)
            runtime.read_file({"path": "src/example.py"})
            with self.assertRaisesRegex(REVIEWER.ReviewError, "focused test file"):
                runtime.validate_report(report)
            runtime.read_file({"path": "tests/test_example.py"})
            self.assertEqual(runtime.validate_report(report)["decision"], "pass_to_primary")

    def test_pytest_node_selector_counts_as_focused_file_read(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            run = root / ".agent/tasks/task-1/runs/run-1"
            packet = json.loads((run / "packet.json").read_text(encoding="utf-8"))
            packet["focused_tests"] = ["tests/test_example.py::test_value"]
            (run / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
            runtime = REVIEWER.ReviewerRuntime(
                root,
                request,
                {"reviewer_require_source_and_test_reads": True},
                FakeClient([]),
            )
            assert runtime.focused_test_paths() == ["tests/test_example.py"]
            runtime.read_file({"path": "src/example.py"})
            runtime.read_file({"path": "tests/test_example.py"})
            assert runtime.required_reads_complete()
            assert "tests/test_example.py" in runtime.replay_read_evidence()
            report = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
            }
            self.assertEqual(runtime.validate_report(report)["decision"], "pass_to_primary")

    def test_missing_focused_test_repair_leaves_read_for_model(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            report = {
                "action": "REPORT",
                "arguments": {
                    "decision": "pass_to_primary",
                    "findings": [],
                    "verified_contract_ids": ["behavior-1"],
                    "unverified_claims": [],
                },
            }
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    report,
                    {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
                    report,
                ]
            )
            result = REVIEWER.ReviewerRuntime(
                root,
                request,
                {"reviewer_require_source_and_test_reads": True},
                client,
            ).run()
            self.assertEqual(result["decision"], "pass_to_primary")
            feedback = json.loads(client.messages_seen[2][-1]["content"].split("\n", 1)[1])
            self.assertNotIn("source_read", feedback["report_repair"])
            self.assertEqual(
                feedback["report_repair"]["suggested_action"]["arguments"]["path"],
                "tests/test_example.py",
            )

    def test_reviewer_can_raise_unlisted_test_gap_for_primary(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            runtime.read_file({"path": "tests/test_example.py"})
            report = runtime.validate_report(
                {
                    "decision": "rework",
                    "findings": [
                        {
                            "id": "missing-boundary",
                            "severity": "medium",
                            "category": "test_gap",
                            "path": "tests/test_example.py",
                            "line": 1,
                            "evidence": "Only the normal value is tested; the required boundary is untested.",
                            "contract_id": None,
                            "suggested_fix": "Add a focused boundary assertion without weakening the normal test.",
                        }
                    ],
                    "verified_contract_ids": ["behavior-1"],
                    "unverified_claims": [],
                }
            )
            self.assertEqual(report["decision"], "rework")
            self.assertIsNone(report["findings"][0]["contract_id"])

    def test_finding_cannot_cite_unread_source_line(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            finding = {
                "id": "f1",
                "severity": "medium",
                "category": "behavior",
                "path": "src/example.py",
                "line": 1,
                "evidence": "The value is not guarded.",
                "contract_id": "behavior-1",
                "suggested_fix": "Add the guard.",
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "finding source line was not read"):
                runtime.validate_report(
                    {
                        "decision": "rework",
                        "findings": [finding],
                        "verified_contract_ids": [],
                        "unverified_claims": [],
                    }
                )
            runtime.read_file({"path": "src/example.py"})
            self.assertEqual(
                runtime.validate_report(
                    {
                        "decision": "rework",
                        "findings": [finding],
                        "verified_contract_ids": [],
                        "unverified_claims": [],
                    }
                )["decision"],
                "rework",
            )

    def test_reviewer_can_escalate_contract_conflict_without_choosing_implementation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            runtime.read_file({"path": "src/example.py"})
            report = runtime.validate_report(
                {
                    "decision": "escalate",
                    "findings": [
                        {
                            "id": "contract-conflict",
                            "severity": "high",
                            "category": "contract_conflict",
                            "path": "src/example.py",
                            "line": 1,
                            "evidence": "The specified behavior conflicts with an adjacent caller assumption.",
                            "contract_id": "behavior-1",
                            "suggested_fix": "Primary should reconcile the contract with the caller before rework.",
                        }
                    ],
                    "verified_contract_ids": [],
                    "unverified_claims": ["Caller compatibility remains unresolved."],
                }
            )
            self.assertEqual(report["next_action_required"], "primary_takeover_or_replan")

    def test_reviewer_diagnostic_logging_can_be_disabled(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            client = FakeClient(
                [
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "pass_to_primary",
                            "findings": [],
                            "verified_contract_ids": ["behavior-1"],
                            "unverified_claims": [],
                        },
                    }
                ]
            )
            REVIEWER.ReviewerRuntime(root, request, {"diagnostic_logging": False}, client).run()
            events = (
                root / ".agent" / "tasks" / "task-1" / "reviews" / "review-1" / "events.jsonl"
            ).read_text(encoding="utf-8")
            self.assertNotIn("response_sha256", events)
            self.assertNotIn("diagnostic_action", events)

    def test_empty_search_gets_concrete_search_repair(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            client = FakeClient(
                [
                    {"action": "SEARCH", "arguments": {"query": ""}},
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "pass_to_primary",
                            "findings": [],
                            "verified_contract_ids": ["behavior-1"],
                            "unverified_claims": [],
                        },
                    },
                ]
            )
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            feedback = json.loads(client.messages_seen[1][-1]["content"].split("\n", 1)[1])
            self.assertEqual(
                feedback["search_repair"]["suggested_action"],
                {
                    "action": "SEARCH",
                    "arguments": {"query": "VALUE = 2", "path": "src/example.py"},
                },
            )
            self.assertEqual(report["runtime_facts"]["protocol_error_count"], 1)

    def test_invalid_report_decision_gets_exact_legal_values(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            repair = runtime.report_repair(
                "decision must be pass_to_primary, rework, or escalate",
                {"decision": "pass"},
            )
            self.assertEqual(repair["valid_decisions"], ["pass_to_primary", "rework", "escalate"])

    def test_reviewer_can_read_but_never_has_write_actions(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, risk="medium")
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "rework",
                            "findings": [
                                {
                                    "id": "finding-1",
                                    "severity": "medium",
                                    "category": "behavior",
                                    "path": "src/example.py",
                                    "line": 1,
                                    "evidence": "VALUE is two without the requested guard.",
                                    "contract_id": "behavior-1",
                                    "suggested_fix": "Add the guard.",
                                }
                            ],
                            "verified_contract_ids": [],
                            "unverified_claims": [],
                        },
                    },
                ]
            )
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "rework")
            self.assertEqual(report["review_route"], "primary_lightweight_review")
            self.assertEqual(report["runtime_facts"]["read_paths"], ["src/example.py"])
            self.assertNotIn(
                "SAFE_REPLACE", REVIEWER.REVIEW_ACTION_SCHEMA["properties"]["action"]["enum"]
            )

    def test_approved_execution_uses_only_registered_ids_and_fixed_argv(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            config = {
                "validation_profiles": {
                    "python-focused": {
                        "python": "trusted-python",
                        "pytest_argv": ["-B", "-m", "pytest"],
                        "commands": [
                            {
                                "id": "ruff-check",
                                "argv": ["{python}", "-m", "ruff", "check", "src"],
                            }
                        ],
                    }
                }
            }
            runtime = REVIEWER.ReviewerRuntime(root, request, config, FakeClient([]))
            runtime.prepare()
            catalog = runtime.approved_execution_catalog()
            self.assertEqual(catalog["tests"][0]["id"], "focused-tests")
            self.assertEqual(catalog["tests"][0]["arguments"], {"test_id": "focused-tests"})
            self.assertEqual(catalog["static_checks"][0]["id"], "ruff-check")
            self.assertEqual(catalog["static_checks"][0]["arguments"], {"check_id": "ruff-check"})
            completed = type("Completed", (), {"returncode": 0, "stdout": "ok\n", "stderr": ""})()
            with patch.object(REVIEWER.subprocess, "run", return_value=completed) as run:
                test_result = runtime.run_approved_test({"test_id": "focused-tests"})
                check_result = runtime.run_approved_static_check({"check_id": "ruff-check"})
            self.assertEqual(test_result["status"], "passed")
            self.assertEqual(check_result["status"], "passed")
            self.assertEqual(
                run.call_args_list[0].args[0],
                ["trusted-python", "-B", "-m", "pytest", "tests/test_example.py"],
            )
            self.assertEqual(
                run.call_args_list[1].args[0],
                ["trusted-python", "-m", "ruff", "check", "src"],
            )
            self.assertFalse(run.call_args_list[0].kwargs["shell"])
            with self.assertRaisesRegex(REVIEWER.ReviewError, "unregistered"):
                runtime.run_approved_static_check({"check_id": "arbitrary-shell"})
            self.assertIn(
                "RUN_APPROVED_TEST",
                REVIEWER.REVIEW_ACTION_SCHEMA["properties"]["action"]["enum"],
            )
            runtime.approved_execution.clear()
            repair = runtime.report_repair(
                "pass_to_primary requires successful approved execution ids: "
                "static_check:ruff-check, test:focused-tests",
                {},
            )
            self.assertEqual(
                repair["required_actions"],
                [
                    {
                        "action": "RUN_APPROVED_TEST",
                        "arguments": {"test_id": "focused-tests"},
                    },
                    {
                        "action": "RUN_APPROVED_STATIC_CHECK",
                        "arguments": {"check_id": "ruff-check"},
                    },
                ],
            )

    def test_none_placeholder_is_not_an_uncertainty(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            with self.assertRaisesRegex(REVIEWER.ReviewError, "must be an empty array"):
                runtime.validate_report(
                    {
                        "decision": "pass_to_primary",
                        "findings": [],
                        "verified_contract_ids": ["behavior-1"],
                        "unverified_claims": ["None"],
                    }
                )

    def test_ordering_sensitive_pass_requires_read_source_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, risk="high", ordering=True)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            base = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "ordering constraint"):
                runtime.validate_report(base)
            runtime.read_file({"path": "src/example.py"})
            base["ordering_review"] = [
                {
                    "constraint_id": "RO-1",
                    "status": "verified",
                    "evidence_type": "source",
                    "path": "src/example.py",
                    "line": 1,
                    "evidence": "Inspected source at line 1.",
                },
                {
                    "constraint_id": "FO-1",
                    "status": "verified",
                    "evidence_type": "diff",
                    "evidence": "The cumulative diff changes only src/example.py.",
                },
            ]
            with self.assertRaisesRegex(REVIEWER.ReviewError, "source-backed contract_review"):
                runtime.validate_report(base)
            base["contract_review"] = [
                {
                    "obligation_id": "behavior-1",
                    "status": "verified",
                    "path": "src/example.py",
                    "line": 1,
                    "source_quote": "VALUE = 2",
                    "evidence": "The cited assignment supplies the required value.",
                }
            ]
            report = runtime.validate_report(base)
            self.assertEqual(len(report["ordering_review"]), 2)
            self.assertEqual(report["contract_review"][0]["obligation_id"], "behavior-1")
            self.assertEqual(report["ordering_review"][1]["evidence_type"], "diff")
            self.assertEqual(runtime.initial_payload()["ordering_constraints"][0]["id"], "RO-1")

    def test_high_risk_contract_review_requires_read_source_and_exact_quote(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, risk="high")
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            runtime.packet["review_feedback"] = ["The key must use one explicit versioned payload."]
            self.assertIn("versioned payload", runtime.initial_payload()["review_feedback"][0])
            args = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
                "contract_review": [
                    {
                        "obligation_id": "behavior-1",
                        "status": "verified",
                        "path": "src/example.py",
                        "line": 1,
                        "source_quote": "VALUE = 2",
                        "evidence": "The assignment satisfies the behavior.",
                    }
                ],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "source was not read"):
                runtime.validate_report(args)
            runtime.read_file({"path": "src/example.py"})
            args["contract_review"][0]["source_quote"] = "VALUE = 3"
            with self.assertRaisesRegex(REVIEWER.ReviewError, "must match"):
                runtime.validate_report(args)
            args["contract_review"][0]["source_quote"] = "VALUE = 2"
            self.assertEqual(runtime.validate_report(args)["decision"], "pass_to_primary")

    def test_source_ref_materializes_quote_and_hash_without_model_copy(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, risk="high")
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            args = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
                "contract_review": [
                    {
                        "obligation_id": "behavior-1",
                        "status": "verified",
                        "source_ref": {
                            "path": "src/example.py",
                            "start_line": 1,
                            "end_line": 1,
                        },
                        "evidence": "The assignment supplies the required value.",
                    }
                ],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "source was not read"):
                runtime.validate_report(args)
            runtime.read_file({"path": "src/example.py"})
            reviewed = runtime.validate_report(args)["contract_review"][0]
            self.assertEqual(reviewed["canonical_quote"], "VALUE = 2")
            self.assertEqual(reviewed["source_quote"], "VALUE = 2")
            self.assertEqual(reviewed["source_ref"]["end_line"], 1)
            self.assertTrue(reviewed["source_hash"].startswith("sha256:"))
            args["contract_review"][0]["source_ref"]["end_line"] = 2
            with self.assertRaisesRegex(REVIEWER.ReviewError, "real range"):
                runtime.validate_report(args)

    def test_high_risk_focused_rework_requires_seen_line_and_anchor(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(
                root,
                risk="high",
                source_content="VALUE = 2\nother = 0\nschema_version = 1\n",
                review_feedback=[
                    {
                        "finding_id": "versioned-payload",
                        "contract_id": "behavior-1",
                        "text": "Use one schema_version=1 payload.",
                        "source_anchor": "schema_version",
                        "verify_in_review": True,
                    },
                    "Historical format note; not a new obligation.",
                ],
            )
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            self.assertEqual(
                [item["id"] for item in runtime.review_obligations()],
                ["behavior-1", "RF-versioned-payload"],
            )
            runtime.read_file({"path": "src/example.py", "start_line": 1, "end_line": 1})
            base = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
                "contract_review": [
                    {
                        "obligation_id": "behavior-1",
                        "status": "verified",
                        "path": "src/example.py",
                        "line": 1,
                        "source_quote": "VALUE = 2",
                        "evidence": "The required value is assigned.",
                    }
                ],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "RF-versioned-payload"):
                runtime.validate_report(base)
            focused = {
                "obligation_id": "RF-versioned-payload",
                "status": "verified",
                "path": "src/example.py",
                "line": 3,
                "source_quote": "schema_version = 1",
                "evidence": "The payload declares schema version one.",
            }
            base["contract_review"].append(focused)
            with self.assertRaisesRegex(REVIEWER.ReviewError, "source line was not read"):
                runtime.validate_report(base)
            runtime.read_file({"path": "src/example.py", "start_line": 3, "end_line": 3})
            focused["line"] = 2
            focused["source_quote"] = "other = 0"
            with self.assertRaisesRegex(REVIEWER.ReviewError, "source line was not read"):
                runtime.validate_report(base)
            runtime.read_file({"path": "src/example.py", "start_line": 2, "end_line": 2})
            with self.assertRaisesRegex(REVIEWER.ReviewError, "source_anchor"):
                runtime.validate_report(base)
            focused["line"] = 3
            focused["source_quote"] = "schema_version = 1"
            self.assertEqual(len(runtime.validate_report(base)["contract_review"]), 2)

    def test_truncated_read_does_not_mark_hidden_lines_as_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, source_content="VALUE = 2\nschema_version = 1\n")
            runtime = REVIEWER.ReviewerRuntime(
                root, request, {"max_tool_output_chars": 14}, FakeClient([])
            )
            observation = runtime.read_file({"path": "src/example.py"})
            self.assertTrue(observation["truncated"])
            self.assertEqual(observation["end_line"], 1)
            self.assertEqual(observation["requested_end_line"], 2)
            self.assertEqual(runtime.read_lines["src/example.py"], {1})

    def test_repeat_read_returns_navigation_and_stops_reviewer_loop(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, source_content="VALUE = 2\nOTHER = 3\n")
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            first = runtime.read_file({"path": "src/example.py", "start_line": 1, "end_line": 1})
            repeated = runtime.read_file({"path": "src/example.py", "start_line": 1, "end_line": 1})
            self.assertEqual(first["status"], "ok")
            self.assertEqual(repeated["status"], "already_read")
            self.assertEqual(repeated["suggested_action"]["arguments"]["start_line"], 2)
            self.assertIn("Do not repeat", repeated["next_step"])

        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
                    *[{"action": "READ_FILE", "arguments": {"path": "src/example.py"}}] * 8,
                ]
            )
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, client)
            with self.assertRaisesRegex(REVIEWER.ReviewError, "repeated reads"):
                runtime.run()
            self.assertEqual(len(client.messages_seen), 5)
            self.assertEqual(client.messages_seen[3][-2]["content"], "DUPLICATE_READ_REJECTED")
            self.assertEqual(len(client.messages_seen[3]), 4)
            feedback = json.loads(client.messages_seen[3][-1]["content"].split("\n", 1)[1])
            self.assertEqual(feedback["required_next_action"], "REPORT")
            self.assertIn("1: VALUE = 2", feedback["evidence_replay"])
            self.assertIn("tests/test_example.py", feedback["evidence_replay"])

    def test_duplicate_test_read_replays_changed_source_before_test(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            runtime.read_file({"path": "src/example.py"})
            runtime.read_file({"path": "tests/test_example.py"})
            repeated = runtime.read_file({"path": "tests/test_example.py"})
            replay = repeated["evidence_replay"]
            self.assertLess(replay.index("src/example.py"), replay.index("tests/test_example.py"))
            self.assertIn("1: VALUE = 2", replay)

    def test_native_reviewer_exposes_only_report_after_complete_duplicate(self) -> None:
        class NativeAwareClient(FakeClient):
            def __init__(self) -> None:
                super().__init__(
                    [
                        {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                        {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
                        {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    ]
                )
                self.native_tools = REVIEWER.REVIEW_NATIVE_TOOLS
                self.native_tool_choice = "auto"
                self.calls: list[tuple[list[str], str]] = []

            def complete(self, messages):
                self.calls.append(
                    (
                        [tool["function"]["name"] for tool in self.native_tools],
                        self.native_tool_choice,
                    )
                )
                if self.native_tool_choice == "required":
                    self.messages_seen.append(list(messages))
                    return json.dumps(
                        {
                            "action": "REPORT",
                            "arguments": {
                                "decision": "pass_to_primary",
                                "findings": [],
                                "verified_contract_ids": ["behavior-1"],
                                "verified_check_ids": [],
                                "ordering_review": [],
                                "contract_review": [],
                                "unverified_claims": [],
                            },
                        }
                    )
                return super().complete(messages)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            client = NativeAwareClient()
            runtime = REVIEWER.ReviewerRuntime(root, self.make_run(root), {}, client)
            report = runtime.run()
            self.assertEqual(report["decision"], "pass_to_primary")
            self.assertEqual(client.calls[-1], (["REPORT"], "required"))
            self.assertEqual(client.native_tools, REVIEWER.REVIEW_NATIVE_TOOLS)
            self.assertEqual(client.native_tool_choice, "auto")

    def test_tagged_rework_focus_is_required_even_for_medium_unit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(
                root,
                risk="medium",
                review_feedback=[
                    {
                        "finding_id": "value-check",
                        "contract_id": "behavior-1",
                        "text": "Confirm the assigned value.",
                        "source_anchor": "VALUE",
                        "verify_in_review": True,
                    }
                ],
            )
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            runtime.read_file({"path": "src/example.py"})
            args = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "RF-value-check"):
                runtime.validate_report(args)
            args["contract_review"] = [
                {
                    "obligation_id": "RF-value-check",
                    "status": "verified",
                    "path": "src/example.py",
                    "line": 1,
                    "source_quote": "VALUE = 2",
                    "evidence": "The assignment uses the requested value.",
                }
            ]
            self.assertEqual(runtime.validate_report(args)["decision"], "pass_to_primary")

    def test_ordering_id_must_be_exact_but_diff_evidence_needs_no_source_line(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, ordering=True)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            invalid = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "ordering_review": [
                    {
                        "constraint_id": "Do not read early.",
                        "status": "verified",
                        "evidence_type": "diff",
                        "evidence": "No unrelated changes.",
                    }
                ],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "expected: RO-1, FO-1"):
                runtime.validate_report(invalid)
            self.assertEqual(
                runtime.initial_payload()["report_template_replace_evidence_before_use"][
                    "arguments"
                ]["ordering_review"][1]["constraint_id"],
                "FO-1",
            )

    def test_ordering_evidence_rejects_template_and_nonexistent_source_line(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, ordering=True)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            runtime.read_file({"path": "src/example.py"})
            args = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "ordering_review": [
                    {
                        "constraint_id": "RO-1",
                        "status": "verified",
                        "evidence_type": "source",
                        "path": "src/example.py",
                        "line": 99,
                        "evidence": "Inspected source.",
                    },
                    {
                        "constraint_id": "FO-1",
                        "status": "verified",
                        "evidence_type": "diff",
                        "evidence": "REPLACE WITH ACTUAL EVIDENCE",
                    },
                ],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "beyond the end"):
                runtime.validate_report(args)
            args["ordering_review"][0]["line"] = 1
            with self.assertRaisesRegex(REVIEWER.ReviewError, "template evidence"):
                runtime.validate_report(args)

    def test_failed_case_with_two_forbidden_constraints_uses_diff_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, ordering=True)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            runtime.packet["forbidden_orderings"].append(
                "Do not change Worker, score interpretation, or global threshold behavior."
            )
            runtime.read_file({"path": "src/example.py"})
            report = runtime.validate_report(
                {
                    "decision": "pass_to_primary",
                    "findings": [],
                    "verified_contract_ids": ["behavior-1"],
                    "unverified_claims": [],
                    "ordering_review": [
                        {
                            "constraint_id": "RO-1",
                            "status": "verified",
                            "evidence_type": "source",
                            "path": "src/example.py",
                            "line": 1,
                            "evidence": "The required value is assigned on line 1.",
                        },
                        {
                            "constraint_id": "FO-1",
                            "status": "verified",
                            "evidence_type": "diff",
                            "evidence": "No early read appears in the diff.",
                        },
                        {
                            "constraint_id": "FO-2",
                            "status": "verified",
                            "evidence_type": "diff",
                            "evidence": "Changed paths contain only src/example.py.",
                        },
                    ],
                }
            )
            self.assertEqual(runtime.diff_paths(), ["src/example.py"])
            self.assertEqual(
                [item["constraint_id"] for item in report["ordering_review"]],
                ["RO-1", "FO-1", "FO-2"],
            )

    def test_invalid_report_receives_packet_specific_repair_template(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, ordering=True)
            valid = {
                "action": "REPORT",
                "arguments": {
                    "decision": "pass_to_primary",
                    "findings": [],
                    "verified_contract_ids": ["behavior-1"],
                    "unverified_claims": [],
                    "ordering_review": [
                        {
                            "constraint_id": "RO-1",
                            "status": "verified",
                            "evidence_type": "source",
                            "path": "src/example.py",
                            "line": 1,
                            "evidence": "Inspected source at line 1.",
                        },
                        {
                            "constraint_id": "FO-1",
                            "status": "verified",
                            "evidence_type": "diff",
                            "evidence": "Only src/example.py changed.",
                        },
                    ],
                },
            }
            client = FakeClient(
                [
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "pass_to_primary",
                            "findings": [],
                            "verified_contract_ids": ["behavior-1"],
                            "ordering_review": [
                                {
                                    "constraint_id": "bad",
                                    "status": "verified",
                                    "evidence_type": "diff",
                                    "evidence": "Wrong id.",
                                }
                            ],
                        },
                    },
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    valid,
                ]
            )
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            feedback = json.loads(client.messages_seen[1][-1]["content"].split("\n", 1)[1])
            self.assertEqual(feedback["report_repair"]["valid_constraint_ids"], ["RO-1", "FO-1"])
            self.assertEqual(feedback["report_repair"]["valid_obligation_ids"], ["behavior-1"])

    def test_report_repair_names_invalid_obligations_and_next_read(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, risk="high", ordering=True)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            ids = runtime.report_repair(
                "contract_review has unknown or duplicate obligation_id",
                {"contract_review": [{"obligation_id": "wrong"}, {"obligation_id": "wrong"}]},
            )
            self.assertEqual(ids["valid_obligation_ids"], ["behavior-1"])
            self.assertEqual(ids["unknown_obligation_ids"], ["wrong"])
            self.assertEqual(ids["duplicate_obligation_ids"], ["wrong"])
            unread = runtime.report_repair(
                "ordering_review source line was not read: src/example.py:12", {}
            )
            self.assertEqual(
                unread["suggested_action"],
                {
                    "action": "READ_FILE",
                    "arguments": {"path": "src/example.py", "start_line": 8, "end_line": 16},
                },
            )
            diff = runtime.report_repair("diff evidence must not claim a source line", {})
            self.assertIn("line to null", diff["instruction"])
            self.assertIsNone(diff["evidence_shapes"]["diff"]["line"])
            missing_path = runtime.report_repair(
                "ordering_review.path must be a non-empty string", {}
            )
            self.assertEqual(missing_path["read_changed_source_paths"], [])
            runtime.read_file({"path": "src/example.py"})
            missing_line = runtime.report_repair(
                "source evidence line must be a positive integer", {}
            )
            self.assertEqual(missing_line["read_changed_source_paths"], ["src/example.py"])
            self.assertIn("report escalate", missing_line["instruction"])
            missing = runtime.report_repair(
                "pass_to_primary requires verified evidence of an allowed type for every ordering constraint",
                {"ordering_review": [{"constraint_id": []}]},
            )
            constraints = missing["unverified_constraints"]
            self.assertEqual([item["constraint_id"] for item in constraints], ["RO-1", "FO-1"])
            self.assertEqual(constraints[0]["allowed_evidence_types"], ["source"])
            self.assertIn("diff", constraints[1]["allowed_evidence_types"])
            self.assertIn("do not manufacture verification", missing["instruction"])
            unread_contract = runtime.report_repair(
                "contract_review source was not read: src/example.py",
                {"contract_review": [{"path": "src/example.py", "line": 1}]},
            )
            self.assertEqual(
                unread_contract["suggested_action"],
                {
                    "action": "READ_FILE",
                    "arguments": {"path": "src/example.py", "start_line": 1, "end_line": 5},
                },
            )
            bad_quote = runtime.report_repair(
                "contract_review source_quote must match the cited source line",
                {
                    "contract_review": [
                        {"path": "src/example.py", "line": 1, "source_quote": "VALUE=2"}
                    ]
                },
            )
            self.assertEqual(bad_quote["source_citation"]["exact_source_quote"], "VALUE = 2")
            self.assertEqual(bad_quote["source_citation"]["line"], 1)
            runtime.read_file({"path": "src/example.py"})
            bad_range = runtime.report_repair(
                "contract_review.source_ref must name a real range of at most 20 lines", {}
            )
            self.assertEqual(
                bad_range["read_source_bounds"]["src/example.py"],
                {"first_line": 1, "last_line": 1},
            )
            bad_decision = runtime.report_repair(
                "decision must be pass_to_primary, rework, or escalate", {}
            )
            self.assertEqual(
                bad_decision["valid_decisions"], ["pass_to_primary", "rework", "escalate"]
            )

    def test_non_json_startup_gets_concrete_action_repair(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)

            class RawThenValid(FakeClient):
                def complete(self, messages):
                    if not self.messages_seen:
                        self.messages_seen.append(list(messages))
                        return "I will review the file."
                    return super().complete(messages)

            client = RawThenValid(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "REPORT",
                        "arguments": {
                            "decision": "pass_to_primary",
                            "findings": [],
                            "verified_contract_ids": ["behavior-1"],
                            "unverified_claims": [],
                        },
                    },
                ]
            )
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            feedback = json.loads(client.messages_seen[1][-1]["content"].split("\n", 1)[1])
            self.assertEqual(
                feedback["protocol_repair"]["example_action"],
                {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
            )
            self.assertEqual(client.messages_seen[1][-2]["content"], "INVALID_NON_JSON_RESPONSE")

    def test_unread_contract_source_is_shown_before_report_retry(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, risk="high")
            action = {
                "action": "REPORT",
                "arguments": {
                    "decision": "pass_to_primary",
                    "findings": [],
                    "verified_contract_ids": ["behavior-1"],
                    "unverified_claims": [],
                    "contract_review": [
                        {
                            "obligation_id": "behavior-1",
                            "status": "verified",
                            "path": "src/example.py",
                            "line": 1,
                            "source_quote": "VALUE = 2",
                            "evidence": "The assignment matches the owned behavior.",
                        }
                    ],
                },
            }
            client = FakeClient([action, action])
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            feedback = json.loads(client.messages_seen[1][-1]["content"].split("\n", 1)[1])
            self.assertEqual(feedback["report_repair"]["source_read"]["status"], "ok")
            self.assertEqual(report["runtime_facts"]["protocol_error_count"], 1)

    def test_mismatched_quote_feedback_supplies_exact_citation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, risk="high")
            base = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
                "contract_review": [
                    {
                        "obligation_id": "behavior-1",
                        "status": "verified",
                        "path": "src/example.py",
                        "line": 1,
                        "source_quote": "VALUE=2",
                        "evidence": "The assignment matches the owned behavior.",
                    }
                ],
            }
            corrected = json.loads(json.dumps(base))
            corrected["contract_review"][0]["source_quote"] = "VALUE = 2"
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {"action": "REPORT", "arguments": base},
                    {"action": "REPORT", "arguments": corrected},
                ]
            )
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            feedback = json.loads(client.messages_seen[2][-1]["content"].split("\n", 1)[1])
            self.assertEqual(
                feedback["report_repair"]["source_citation"]["exact_source_quote"],
                "VALUE = 2",
            )
            self.assertEqual(
                feedback["report_repair"]["citation_fixes"][0]["obligation_id"],
                "behavior-1",
            )
            self.assertEqual(client.messages_seen[2][-2]["content"], "INVALID_REPORT_SUBMITTED")

    def test_unread_report_line_is_shown_before_reviewer_retries(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, ordering=True)
            report_action = {
                "action": "REPORT",
                "arguments": {
                    "decision": "pass_to_primary",
                    "findings": [],
                    "verified_contract_ids": ["behavior-1"],
                    "unverified_claims": [],
                    "ordering_review": [
                        {
                            "constraint_id": "RO-1",
                            "status": "verified",
                            "evidence_type": "source",
                            "path": "src/example.py",
                            "line": 1,
                            "evidence": "The source line assigns the required value.",
                        },
                        {
                            "constraint_id": "FO-1",
                            "status": "verified",
                            "evidence_type": "diff",
                            "evidence": "The cumulative diff only changes the value.",
                        },
                    ],
                },
            }
            client = FakeClient([report_action, report_action])
            result = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(result["decision"], "pass_to_primary")
            feedback = json.loads(client.messages_seen[1][-1]["content"].split("\n", 1)[1])
            self.assertEqual(feedback["report_repair"]["source_read"]["status"], "ok")

    def test_pass_must_acknowledge_configured_check_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(
                root,
                configured_checks=[
                    {"id": "ruff-format", "status": "passed"},
                    {"id": "ruff-check", "status": "passed"},
                ],
            )
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            args = {
                "decision": "pass_to_primary",
                "findings": [],
                "verified_contract_ids": ["behavior-1"],
                "unverified_claims": [],
            }
            with self.assertRaisesRegex(REVIEWER.ReviewError, "every configured check id"):
                runtime.validate_report(args)
            args["verified_check_ids"] = ["ruff-format", "ruff-check"]
            self.assertEqual(
                runtime.validate_report(args)["verified_check_ids"],
                ["ruff-format", "ruff-check"],
            )

    def test_default_search_aggregates_declared_read_roots(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            result = runtime.search({"query": "VALUE", "glob": "*.py"})
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["results"][0]["path"], "src/example.py")

    def test_search_skips_excluded_and_reparse_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            packet_path = root / ".agent" / "tasks" / "task-1" / "runs" / "run-1" / "packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["scope"]["read"] = ["src", "tests"]
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            (root / "src" / "linked").mkdir()
            (root / "src" / "linked" / "hidden.py").write_text("TARGET = 1\n")
            excluded = root / "ui" / "node_modules" / "eslint"
            excluded.mkdir(parents=True)
            (excluded / "LICENSE").write_text("TARGET\n")
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            with patch.object(
                REVIEWER.SAFE_EDIT,
                "is_reparse_point",
                side_effect=lambda path: path.name == "linked",
            ):
                self.assertEqual(runtime.search({"query": "TARGET"})["results"], [])
            self.assertEqual(
                runtime.search({"query": "VALUE"})["results"][0]["path"], "src/example.py"
            )

    def test_reviewer_rejects_inputs_changed_after_coder_run(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            (root / "src" / "example.py").write_text("VALUE = 3\n", encoding="utf-8")
            with self.assertRaisesRegex(REVIEWER.ReviewError, "inputs changed"):
                REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))


if __name__ == "__main__":
    unittest.main()
