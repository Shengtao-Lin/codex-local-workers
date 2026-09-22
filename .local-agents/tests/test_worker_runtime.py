from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).parents[1] / "worker-runtime.py"
SPEC = importlib.util.spec_from_file_location("worker_runtime_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


class FakeClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = iter(json.dumps(item) for item in responses)

    def complete(self, messages: list[dict[str, str]]) -> str:
        return next(self.responses)


class AdaptiveSuccessClient:
    def __init__(self) -> None:
        self.step = 0

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.step += 1
        if self.step == 1:
            action = {"action": "READ_FILE", "arguments": {"path": "src/example.py"}}
        elif self.step == 2:
            observation = json.loads(messages[-1]["content"].split("\n", 1)[1])
            action = {"action": "SAFE_REPLACE", "arguments": {
                "path": "src/example.py",
                "expected_sha256": observation["sha256"],
                "find": "VALUE = 1\n",
                "replace": "VALUE = 2\n",
            }}
        elif self.step == 3:
            action = {"action": "VALIDATE", "arguments": {}}
        else:
            action = {"action": "FINISH_SUCCESS", "arguments": {
                "summary": ["Changed VALUE to 2."], "remaining_uncertainty": []}}
        return json.dumps(action)


def packet() -> dict:
    return {
        "schema_version": 1,
        "task_id": "test-1",
        "run_id": "test-1-a1",
        "goal": "Change the value and keep its test passing.",
        "scope": {"modify": ["src/example.py"], "create": [], "forbidden": ["src/secret.py"]},
        "required_behavior": ["VALUE is 2"],
        "acceptance_criteria": ["Focused tests pass"],
        "focused_tests": ["tests/test_example.py"],
        "limits": {"max_model_turns": 8},
    }


def packet_v2() -> dict:
    value = packet()
    value.update({
        "schema_version": 2,
        "unit_id": "step-1",
        "plan_revision": 1,
        "packet_revision": 2,
        "validation_profile": "python-focused",
    })
    value["scope"]["read"] = ["src", "tests"]
    value["required_behavior"] = [{"id": "behavior-value", "text": "VALUE is 2"}]
    value["acceptance_criteria"] = [{"id": "acceptance-tests", "text": "Focused tests pass"}]
    return value


class WorkerRuntimeTests(unittest.TestCase):
    def make_tree(self, root: Path) -> None:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "example.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "tests" / "test_example.py").write_text("def test_value(): pass\n", encoding="utf-8")

    def test_runtime_rejects_out_of_scope_edit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient([
                {"action": "SAFE_CREATE", "arguments": {"path": "src/secret.py", "content": "bad\n"}},
                {"action": "FINISH_FAILED", "arguments": {
                    "summary": ["Scope prevented the edit."], "reason": "not authorized", "remaining_uncertainty": []}},
            ])
            runtime = RUNTIME.WorkerRuntime(root, packet(), {"python": "python.exe"}, client)
            report = runtime.run()
            self.assertEqual(report["status"], "failed")
            self.assertFalse((root / "src" / "secret.py").exists())
            self.assertEqual(report["protocol_error_count"], 1)

    def test_success_is_rejected_without_validation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient([
                {"action": "FINISH_SUCCESS", "arguments": {"summary": ["Done"], "remaining_uncertainty": []}},
                {"action": "FINISH_FAILED", "arguments": {
                    "summary": ["Validation was required."], "reason": "not validated", "remaining_uncertainty": []}},
            ])
            runtime = RUNTIME.WorkerRuntime(root, packet(), {"python": "python.exe"}, client)
            report = runtime.run()
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["protocol_error_count"], 1)

    def test_authorized_edit_validation_and_success(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet(),
                {"python": sys.executable},
                AdaptiveSuccessClient(),
            )
            def fake_command(argv: list[str]) -> dict:
                for item in argv:
                    if item.startswith("--junitxml="):
                        junit = Path(item.split("=", 1)[1])
                        junit.write_text(
                            '<testsuites><testsuite tests="1" failures="0" errors="0" '
                            'skipped="0" /></testsuites>',
                            encoding="utf-8",
                        )
                return {"status": "passed", "exit_code": 0, "output": "ok", "argv": argv}

            with patch.object(runtime, "_run_command", side_effect=fake_command):
                report = runtime.run()
            self.assertEqual(report["status"], "ready_for_review")
            self.assertEqual((root / "src" / "example.py").read_text(), "VALUE = 2\n")
            self.assertEqual(report["changed_files"][0]["operation"], "modified")
            self.assertEqual(report["validation"]["status"], "passed")
            run_root = root / report["evidence_refs"]["run_archive"]
            for name in (
                "packet.json",
                "baseline.json",
                "preimages.json",
                "events.jsonl",
                "changes.json",
                "cumulative.diff",
                "reverse.diff",
                "validation.json",
                "handoff.json",
                "post-state.json",
                "completed.json",
            ):
                self.assertTrue((run_root / name).is_file(), name)
            preimages = json.loads((run_root / "preimages.json").read_text())
            source_preimage = next(
                item for item in preimages if item["path"] == "src/example.py"
            )
            self.assertEqual(
                (root / source_preimage["archive_path"]).read_text(),
                "VALUE = 1\n",
            )
            self.assertIn("-VALUE = 1", (run_root / "cumulative.diff").read_text())
            self.assertIn("+VALUE = 1", (run_root / "reverse.diff").read_text())
            task_state = json.loads(
                (root / ".agent" / "tasks" / "test-1" / "state.json").read_text()
            )
            self.assertEqual(task_state["latest_run_id"], "test-1-a1")
            self.assertEqual(task_state["recent_attempts"][-1]["result"], "ready_for_review")
            current = json.loads((root / ".agent" / "current-task.json").read_text())
            self.assertEqual(current["usage"]["coder_calls"], 1)
            self.assertEqual(current["recent_attempts"][-1]["run_id"], "test-1-a1")

    def test_flat_and_multiple_actions_are_safely_normalized(self) -> None:
        parsed = RUNTIME.parse_action(
            '{"action":"SEARCH","query":"needle"}\n'
            '{"action":"READ_FILE","path":"greeting.py"}'
        )
        self.assertEqual(parsed["action"], "SEARCH")
        self.assertEqual(parsed["arguments"], {"query": "needle"})
        self.assertEqual(len(parsed["_warnings"]), 1)

    def test_non_json_trailing_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(RUNTIME.WorkerError, "non-JSON trailing"):
            RUNTIME.parse_action('{"action":"VALIDATE"}\nthen run tests')

    def test_lmstudio_client_requests_schema_constrained_actions(self) -> None:
        captured = {}

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse(json.dumps({
                "choices": [{"message": {"content": '{"action":"VALIDATE","arguments":{}}'}}]
            }).encode("utf-8"))

        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "coder", timeout=9)
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = client.complete([{"role": "user", "content": "act"}])

        self.assertEqual(result, '{"action":"VALIDATE","arguments":{}}')
        self.assertEqual(captured["timeout"], 9)
        self.assertEqual(captured["body"]["max_tokens"], 4096)
        self.assertEqual(captured["body"]["repeat_penalty"], 1.0)
        response_format = captured["body"]["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        schema = response_format["json_schema"]["schema"]
        self.assertEqual(schema["required"], ["action", "arguments"])
        self.assertIn("SAFE_REPLACE", schema["properties"]["action"]["enum"])

    def test_lmstudio_client_can_disable_structured_output_for_compatibility(self) -> None:
        captured = {}

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse(json.dumps({
                "choices": [{"message": {"content": '{"action":"VALIDATE","arguments":{}}'}}]
            }).encode("utf-8"))

        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1", "coder", structured_output=False
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            client.complete([{"role": "user", "content": "act"}])

        self.assertNotIn("response_format", captured["body"])

    def test_compact_handoff_keeps_decision_fields_and_omits_bulk_evidence(self) -> None:
        report = {
            "schema_version": 2,
            "status": "ready_for_review",
            "identity": {"task_id": "task", "unit_id": "unit", "run_id": "run"},
            "changed_files": [{"path": "src/a.py", "operation": "modified"}],
            "worker_claims": {"summary": ["Implemented behavior."]},
            "validation": {
                "status": "passed",
                "py_compile": {"status": "passed"},
                "focused_tests": {
                    "status": "passed",
                    "inputs_unchanged": True,
                    "input_facts": {"src/a.py": {"sha256": "x" * 64}},
                    "junit": {"tests": 3, "executed": 3, "failures": 0, "errors": 0, "skipped": 0},
                },
            },
            "next_action_required": "primary_review",
            "evidence_refs": {"run_archive": ".agent/tasks/task/runs/run"},
        }
        compact = RUNTIME.compact_handoff(report)
        self.assertEqual(compact["validation_summary"]["tests"], 3)
        self.assertEqual(compact["next_action_required"], "primary_review")
        self.assertNotIn("input_facts", json.dumps(compact))

    def test_v1_packet_is_normalized_to_v2(self) -> None:
        normalized = RUNTIME.validate_packet(packet())
        self.assertEqual(normalized["schema_version"], 2)
        self.assertEqual(normalized["_source_schema_version"], 1)
        self.assertEqual(normalized["scope"]["read"], ["."])
        self.assertEqual(normalized["unit_id"], "test-1")
        self.assertEqual(normalized["acceptance_criteria"][0]["id"], "acceptance-1")
        self.assertEqual(
            normalized["acceptance_scenarios"][0]["id"],
            "scenario-acceptance-1",
        )

    def test_v2_read_scope_is_enforced(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "outside.py").write_text("SECRET = 1\n", encoding="utf-8")
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, FakeClient([]))
            with self.assertRaisesRegex(RUNTIME.WorkerError, "outside scope.read"):
                runtime.read_file({"path": "outside.py"})

    def test_packet_preserves_order_and_observable_contracts(self) -> None:
        value = packet_v2()
        value["required_order"] = ["run handler", "recheck lease", "commit"]
        value["forbidden_orderings"] = ["recheck lease before handler"]
        value["acceptance_scenarios"] = [{
            "id": "stale-lease",
            "text": "A stale lease rolls back without finalization.",
            "observables": {"rollback_calls": 1, "commit_calls": 0},
        }]
        normalized = RUNTIME.validate_packet(value)
        self.assertTrue(normalized["contract_check_required"])
        self.assertEqual(normalized["required_order"][1], "recheck lease")
        self.assertEqual(
            normalized["acceptance_scenarios"][0]["observables"]["commit_calls"],
            0,
        )

    def test_packet_supports_readonly_scope_and_two_level_risk(self) -> None:
        value = packet_v2()
        value["feature_id"] = "lease-fencing"
        value["scope"]["readonly"] = ["tests/test_example.py"]
        value["risk"] = {
            "feature": "high",
            "unit": "medium",
            "integration": "high",
            "reasons": ["Feature integration is transaction-sensitive."],
        }
        value["required_behavior"][0]["risk_floor"] = "medium"
        value["owned_contract_ids"] = ["behavior-value"]
        normalized = RUNTIME.validate_packet(value)
        self.assertEqual(normalized["risk"]["feature"], "high")
        self.assertEqual(normalized["risk"]["unit"], "medium")
        self.assertIn("tests/test_example.py", normalized["scope"]["read"])
        self.assertIn("tests/test_example.py", normalized["scope"]["readonly"])

    def test_unit_risk_cannot_be_below_owned_contract_floor(self) -> None:
        value = packet_v2()
        value["risk"] = {"feature": "high", "unit": "small", "integration": "high"}
        value["required_behavior"][0]["risk_floor"] = "high"
        with self.assertRaisesRegex(RUNTIME.WorkerError, "below owned contract risk_floor"):
            RUNTIME.validate_packet(value)

    def test_readonly_scope_cannot_overlap_writable_scope(self) -> None:
        value = packet_v2()
        value["scope"]["readonly"] = ["src"]
        with self.assertRaisesRegex(RUNTIME.WorkerError, "overlaps scope.readonly"):
            RUNTIME.validate_packet(value)

    def test_diff_quality_gate_reports_only_introduced_whitespace(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src" / "example.py"
            source.write_text("OLD = 1  \nVALUE = 1\n", encoding="utf-8")
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            source.write_text("OLD = 1  \nVALUE = 2  \n", encoding="utf-8")
            issues = runtime._introduced_text_quality_issues()
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["code"], "introduced_trailing_whitespace")
            self.assertEqual(issues[0]["line"], 2)

    def test_inherited_rework_packet_preserves_parent_contract(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parent = packet_v2()
            parent_path = (
                root / ".agent" / "tasks" / "test-1" / "runs" / "run-1" / "packet.json"
            )
            parent_path.parent.mkdir(parents=True)
            parent_path.write_text(json.dumps(parent), encoding="utf-8")
            parent_path.with_name("completed.json").write_text(
                json.dumps({"status": "ready_for_review"}), encoding="utf-8"
            )
            child = {
                "schema_version": 2,
                "task_id": "test-1",
                "unit_id": parent["unit_id"],
                "run_id": "run-2",
                "packet_revision": parent["packet_revision"] + 1,
                "parent_run_id": "run-1",
                "preserve_contract": True,
                "review_feedback": [{"finding_id": "finding-1", "text": "Fix it."}],
            }
            resolved = RUNTIME.resolve_inherited_packet(root, child)
            self.assertEqual(resolved["goal"], parent["goal"])
            self.assertEqual(resolved["scope"], parent["scope"])
            self.assertEqual(resolved["parent_run_id"], "run-1")
            self.assertIn("parent_packet_sha256", resolved["_inheritance"])

    def test_contract_check_and_changed_test_quality_gate(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["required_order"] = ["edit", "validate"]
            value["forbidden_orderings"] = ["validate before edit"]
            value["acceptance_scenarios"] = [{
                "id": "observable-test",
                "text": "The test asserts the result.",
                "observables": {"assertions": 1},
            }]
            runtime = RUNTIME.WorkerRuntime(
                root, value, {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                runtime.changed["tests/test_example.py"] = {
                    "path": "tests/test_example.py",
                    "operation": "modified",
                    "sha256": "unused",
                }
                check = {
                    "contract_check": {
                        "required_behavior_ids": ["behavior-value"],
                        "required_order_confirmed": True,
                        "forbidden_orderings_absent": True,
                        "observable_scenario_ids": ["observable-test"],
                        "unrelated_changes": [],
                    }
                }
                result = runtime.validate(check)
            finally:
                runtime.close()
            self.assertEqual(result["status"], "failed")
            diagnostic = result["validation"]["focused_tests"]["diagnostic"]
            self.assertIn("has no assert", diagnostic["excerpt"])

    def test_failed_replace_does_not_consume_repair_budget(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime.pending_failed_validation = True
                _, digest = runtime.editor.read_bytes("src/example.py")
                with self.assertRaisesRegex(RUNTIME.SafeEditError, "not found"):
                    runtime.safe_replace({
                        "path": "src/example.py",
                        "expected_sha256": digest,
                        "find": "VALUE = 999\n",
                        "replace": "VALUE = 2\n",
                    })
            finally:
                runtime.close()
            self.assertEqual(runtime.repairs, 0)
            self.assertTrue(runtime.pending_failed_validation)

    def test_first_validation_reserves_finish_turns(self) -> None:
        class LateValidationClient:
            def __init__(self) -> None:
                self.turn = 0

            def complete(self, _messages):
                self.turn += 1
                if self.turn < 4:
                    return json.dumps({
                        "action": "READ_FILE",
                        "arguments": {"path": "src/example.py"},
                    })
                if self.turn == 4:
                    return json.dumps({"action": "VALIDATE", "arguments": {}})
                return json.dumps({
                    "action": "FINISH_SUCCESS",
                    "arguments": {"summary": ["Validated."], "remaining_uncertainty": []},
                })

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["limits"] = {
                "max_model_turns": 4,
                "repair_turn_reserve": 2,
                "hard_max_model_turns": 6,
            }
            runtime = RUNTIME.WorkerRuntime(
                root, value, {"python": sys.executable}, LateValidationClient()
            )

            def fake_command(argv: list[str]) -> dict:
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0" /></testsuites>',
                            encoding="utf-8",
                        )
                return {"status": "passed", "exit_code": 0, "output": "ok", "argv": argv}

            with patch.object(runtime, "_run_command", side_effect=fake_command):
                report = runtime.run()
            self.assertEqual(report["status"], "ready_for_review")
            self.assertEqual(report["runtime_facts"]["first_validation_turn"], 4)

    def test_validation_profile_runs_trusted_configured_commands(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            config = {
                "validation_profiles": {
                    "python-focused": {
                        "python": sys.executable,
                        "compile": True,
                        "pytest_argv": ["-B", "-m", "pytest"],
                        "commands": [
                            {"id": "ruff-check", "argv": ["{python}", "-m", "ruff", "check", "src"]}
                        ],
                    }
                }
            }
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), config, FakeClient([]))
            runtime.write_lock.acquire()
            runtime._prepare_run_archive()

            def fake_command(argv: list[str]) -> dict:
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0" /></testsuites>',
                            encoding="utf-8",
                        )
                return {"status": "passed", "exit_code": 0, "output": "ok", "argv": argv}

            try:
                with patch.object(runtime, "_run_command", side_effect=fake_command):
                    result = runtime.validate({})
            finally:
                runtime.close()
            self.assertEqual(result["status"], "passed")
            self.assertEqual(
                result["validation"]["configured_checks"][0]["id"], "ruff-check"
            )

    def test_control_files_are_never_writable(self) -> None:
        value = packet_v2()
        value["scope"]["modify"] = [".local-agents/worker-runtime.py"]
        value["scope"]["read"] = ["."]
        with self.assertRaisesRegex(RUNTIME.WorkerError, "control path"):
            RUNTIME.validate_packet(value)

    def test_finish_blocked_requests_scope_without_granting_it(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient([{
                "action": "FINISH_BLOCKED",
                "reason_code": "needs_scope_expansion",
                "reason": "The implementation is owned by another module.",
                "requested_scope": {"read": ["src/other.py"], "modify": ["src/other.py"]},
                "evidence_refs": ["src/example.py:1"],
                "proposed_next_step": "Primary reviews and issues a revised packet.",
            }])
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client)
            report = runtime.run()
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["blocked"]["reason_code"], "needs_scope_expansion")
            self.assertFalse((root / "src" / "other.py").exists())

    def test_preflight_reports_missing_python_as_blocked(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {"validation_profiles": {"python-focused": {
                    "python": ".venv/missing-python.exe",
                    "compile": True,
                    "pytest_argv": ["-B", "-m", "pytest"],
                }}},
                FakeClient([]),
            )
            with self.assertRaisesRegex(RUNTIME.PreflightBlocked, "Python was not found"):
                runtime.preflight()

    def test_packet_disk_state_mismatch_is_blocked_before_model_call(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)

            missing_modify = packet_v2()
            missing_modify["scope"]["modify"] = ["src/missing.py"]
            missing_modify["scope"]["read"] = ["src", "tests"]
            with self.assertRaisesRegex(RUNTIME.PreflightBlocked, "does not exist") as modify_error:
                RUNTIME.WorkerRuntime(root, missing_modify, {"python": sys.executable}, FakeClient([]))
            self.assertEqual(modify_error.exception.reason_code, "modify_target_missing")

            existing_create = packet_v2()
            existing_create["scope"]["modify"] = []
            existing_create["scope"]["create"] = ["src/example.py"]
            with self.assertRaisesRegex(RUNTIME.PreflightBlocked, "already exists") as create_error:
                RUNTIME.WorkerRuntime(root, existing_create, {"python": sys.executable}, FakeClient([]))
            self.assertEqual(create_error.exception.reason_code, "create_target_exists")

            missing_test = packet_v2()
            missing_test["focused_tests"] = ["tests/test_missing.py"]
            with self.assertRaisesRegex(RUNTIME.PreflightBlocked, "focused test does not exist") as test_error:
                RUNTIME.WorkerRuntime(root, missing_test, {"python": sys.executable}, FakeClient([]))
            self.assertEqual(test_error.exception.reason_code, "focused_test_missing")

    def test_existing_managed_write_lock_blocks_before_model_call(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            lock = root / ".agent" / "local-worker-write.lock"
            lock.parent.mkdir()
            lock.write_text('{"pid": 999, "run_id": "other-run"}\n', encoding="utf-8")
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            report = runtime.run()
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["blocked"]["reason_code"], "write_lock_held")
            self.assertTrue(lock.exists())

    def test_invocation_deadline_interrupts_and_releases_lock(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {"python": sys.executable, "invocation_timeout_seconds": 1},
                FakeClient([]),
            )
            with patch.object(RUNTIME.time, "monotonic", side_effect=[10.0, 12.0]):
                report = runtime.run()
            self.assertEqual(report["status"], "interrupted")
            self.assertEqual(
                report["interruption"]["reason_code"], "invocation_deadline_exceeded"
            )
            self.assertFalse((root / ".agent" / "local-worker-write.lock").exists())

    def test_timed_out_validation_process_is_terminated_and_recorded(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {
                    "python": sys.executable,
                    "command_timeout_seconds": 1,
                    "invocation_timeout_seconds": 10,
                },
                FakeClient([]),
            )
            result = runtime._run_command(
                [sys.executable, "-c", "import time; time.sleep(30)"]
            )
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["timed_out"])
            self.assertEqual(result["termination"]["termination"], "confirmed")
            self.assertTrue(runtime.process_events)

    def test_duplicate_run_id_is_blocked_and_original_archive_is_preserved(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            finish_failed = [{
                "action": "FINISH_FAILED",
                "arguments": {
                    "summary": ["Stopped."],
                    "reason": "test stop",
                    "remaining_uncertainty": [],
                },
            }]
            first = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient(finish_failed)
            ).run()
            original_handoff = (
                root / first["evidence_refs"]["run_archive"] / "handoff.json"
            ).read_bytes()
            second = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            ).run()
            self.assertEqual(second["status"], "blocked")
            self.assertEqual(second["blocked"]["reason_code"], "run_id_conflict")
            self.assertEqual(
                (root / first["evidence_refs"]["run_archive"] / "handoff.json").read_bytes(),
                original_handoff,
            )

    def test_file_change_after_validation_invalidates_success(self) -> None:
        class MutatingClient(AdaptiveSuccessClient):
            def __init__(self, test_path: Path) -> None:
                super().__init__()
                self.test_path = test_path

            def complete(self, messages: list[dict[str, str]]) -> str:
                if self.step == 3:
                    self.step += 1
                    self.test_path.write_text("def test_value(): pass\n# external change\n", encoding="utf-8")
                    return json.dumps({
                        "action": "FINISH_SUCCESS",
                        "arguments": {"summary": ["Done"], "remaining_uncertainty": []},
                    })
                if self.step == 4:
                    self.step += 1
                    return json.dumps({
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Validation became stale."],
                            "reason": "external change",
                            "remaining_uncertainty": [],
                        },
                    })
                return super().complete(messages)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {"python": sys.executable},
                MutatingClient(root / "tests" / "test_example.py"),
            )

            def fake_command(argv: list[str]) -> dict:
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0" /></testsuites>',
                            encoding="utf-8",
                        )
                return {"status": "passed", "exit_code": 0, "output": "ok", "argv": argv}

            with patch.object(runtime, "_run_command", side_effect=fake_command):
                report = runtime.run()
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["failure_reason"], "external change")
            self.assertTrue(
                any("validation inputs changed" in item["error"] for item in report["protocol_error_details"])
            )
            changes = json.loads(
                (root / report["evidence_refs"]["run_archive"] / "changes.json").read_text()
            )
            self.assertEqual(
                changes["unattributed_relevant_changes"][0]["path"],
                "tests/test_example.py",
            )

    def test_all_skipped_tests_do_not_pass_quality_gate(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, AdaptiveSuccessClient()
            )

            def skipped_command(argv: list[str]) -> dict:
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="1" /></testsuites>',
                            encoding="utf-8",
                        )
                return {"status": "passed", "exit_code": 0, "output": "1 skipped", "argv": argv}

            with patch.object(runtime, "_run_command", side_effect=skipped_command):
                report = runtime.run()
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["validation"]["focused_tests"]["junit"]["executed"], 0)


if __name__ == "__main__":
    unittest.main()
