from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "worker-runtime.py"
SPEC = importlib.util.spec_from_file_location("worker_runtime_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


class FakeClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = iter(json.dumps(item) for item in responses)
        self.messages_seen: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages_seen.append(list(messages))
        return next(self.responses)


class JUnitDisplayedBindingTests(unittest.TestCase):
    def test_bounded_actual_header_bindings_preserved_without_evaluation(self):
        root = ET.fromstring(
            '<testsuite><testcase name="invalid[True]"><failure message="Failed: DID NOT RAISE ValueError">width = True\nother = &quot;literal&quot;\n\nsource = must_not_be_captured\ntests/test_x.py:4: Failed</failure></testcase></testsuite>'
        )
        failure = RUNTIME.WorkerRuntime._junit_failures(root)[0]
        self.assertEqual(
            failure["displayed_bindings"],
            [
                {"name": "width", "representation": "True"},
                {"name": "other", "representation": '"literal"'},
            ],
        )
        oversized = "\n".join(f"arg{i} = " + "x" * 500 for i in range(8))
        node = ET.fromstring('<testsuite><testcase name="x"><failure /></testcase></testsuite>')
        node.find(".//failure").text = oversized
        bindings = RUNTIME.WorkerRuntime._junit_failures(node)[0]["displayed_bindings"]
        self.assertEqual(len(bindings), 4)
        self.assertTrue(all(len(b["representation"]) <= 120 for b in bindings))


class RawClient(FakeClient):
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.messages_seen = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages_seen.append(list(messages))
        return next(self.responses)


class InfraFailureClient:
    last_request_stats = {"rejection_reason": "input_too_large"}

    def complete(self, _messages: list[dict[str, str]]) -> str:
        raise RUNTIME.ModelRequestError(
            "input_too_large",
            "request exceeds context",
            {"estimated_input_tokens": 100, "context_length": 80},
        )


class AdaptiveSuccessClient:
    def __init__(self) -> None:
        self.step = 0

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.step += 1
        if self.step == 1:
            action = {"action": "READ_FILE", "arguments": {"path": "src/example.py"}}
        elif self.step == 2:
            observation = json.loads(messages[-1]["content"].split("\n", 1)[1])
            action = {
                "action": "SAFE_REPLACE",
                "arguments": {
                    "path": "src/example.py",
                    "expected_sha256": observation["sha256"],
                    "find": "VALUE = 1\n",
                    "replace": "VALUE = 2\n",
                },
            }
        elif self.step == 3:
            action = {"action": "VALIDATE", "arguments": {}}
        else:
            action = {
                "action": "FINISH_SUCCESS",
                "arguments": {"summary": ["Changed VALUE to 2."], "remaining_uncertainty": []},
            }
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
    value.update(
        {
            "schema_version": 2,
            "unit_id": "step-1",
            "plan_revision": 1,
            "packet_revision": 2,
            "validation_profile": "python-focused",
        }
    )
    value["scope"]["read"] = ["src", "tests"]
    value["required_behavior"] = [{"id": "behavior-value", "text": "VALUE is 2"}]
    value["acceptance_criteria"] = [{"id": "acceptance-tests", "text": "Focused tests pass"}]
    return value


class WorkerRuntimeTests(unittest.TestCase):
    def test_guarded_search_and_prefetch_preserve_repository_read_root(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src/secret.py").write_text("VALUE = 'private'\n", encoding="utf-8")
            (root / ".agent").mkdir()
            (root / ".agent/secret.py").write_text("VALUE = 'excluded'\n", encoding="utf-8")
            value = packet_v2()
            value["scope"]["read"] = ["."]
            runtime = RUNTIME.WorkerRuntime(root, value, {}, FakeClient([]))
            self.assertEqual(
                [
                    x["path"]
                    for x in runtime.search({"query": "VALUE", "case_sensitive": True})["results"]
                ],
                ["src/example.py"],
            )
            self.assertEqual(
                [
                    x["path"]
                    for x in runtime._compact_repair_payload({"symbol": "VALUE"})["symbol_evidence"]
                ],
                ["src/example.py"],
            )

    def test_search_and_repair_scan_skip_reparse_files_and_directories(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src/link.py").write_text("SCAN_TOKEN = 'linked-file'\n", encoding="utf-8")
            (root / "src/junction").mkdir()
            (root / "src/junction/other.py").write_text(
                "SCAN_TOKEN = 'linked-dir'\n", encoding="utf-8"
            )
            (root / "src/example.py").write_text("SCAN_TOKEN = 'allowed'\n", encoding="utf-8")
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {}, FakeClient([]))
            original = RUNTIME.SAFE_EDIT.is_reparse_point

            def reparse(path):
                return path.name in {"link.py", "junction"} or original(path)

            with patch.object(RUNTIME.SAFE_EDIT, "is_reparse_point", side_effect=reparse):
                search = runtime.search({"query": "SCAN_TOKEN"})
                repair = runtime._compact_repair_payload({"symbol": "SCAN_TOKEN"})
            self.assertEqual([p["path"] for p in search["results"]], ["src/example.py"])
            self.assertEqual([p["path"] for p in repair["symbol_evidence"]], ["src/example.py"])

    def test_repair_prefetch_never_reads_forbidden_source_or_symbol_evidence(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src/secret.py").write_text(
                "PRIVATE_TOKEN = 'do-not-disclose'\n", encoding="utf-8"
            )
            (root / "src/example.py").write_text("PUBLIC_TOKEN = 2\n", encoding="utf-8")
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {}, FakeClient([]))
            original_guard = runtime._assert_read_allowed
            seen = []

            def guard(path):
                seen.append(path)
                return original_guard(path)

            with patch.object(runtime, "_assert_read_allowed", side_effect=guard):
                result = runtime._compact_repair_payload(
                    {"symbol": "PRIVATE_TOKEN", "candidate_edit_paths": ["src/example.py"]}
                )
            self.assertNotIn("do-not-disclose", json.dumps(result))
            self.assertEqual(result["symbol_evidence"], [])
            self.assertIn("src/secret.py", seen)
            allowed = runtime._compact_repair_payload({"symbol": "PUBLIC_TOKEN"})
            self.assertEqual(allowed["symbol_evidence"][0]["path"], "src/example.py")

    def test_repair_prefetch_test_evidence_honors_scope_read_guard(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {}, FakeClient([]))
            runtime.validation = RUNTIME.ValidationResult(
                "failed",
                {},
                {
                    "diagnostic": {
                        "failures": [
                            {
                                "test": "test_example",
                                "location": "tests/test_example.py:1",
                                "message": "failed",
                            }
                        ]
                    }
                },
                None,
            )
            with patch.object(
                runtime, "_assert_read_allowed", side_effect=RUNTIME.WorkerError("blocked read")
            ):
                payload = runtime._compact_repair_payload(
                    {"candidate_edit_paths": ["src/example.py"]}
                )
            self.assertEqual(payload["source_excerpts"], [])
            self.assertEqual(payload["test_evidence"], [])

    def test_prompt_examples_match_canonical_action_schema_with_legacy_parsing_preserved(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {}, FakeClient([]))
            prompt = runtime.system_prompt()
            self.assertNotIn("flat JSON object", prompt)
            examples = []
            for line in prompt.splitlines():
                candidate = line.strip().removeprefix("Example: ").removesuffix(".")
                if candidate.startswith('{"action":'):
                    example = json.loads(candidate)
                    self.assertEqual(set(example), {"action", "arguments"})
                    self.assertIsInstance(example["arguments"], dict)
                    self.assertIn(
                        example["action"],
                        RUNTIME.CODER_ACTION_SCHEMA["properties"]["action"]["enum"],
                    )
                    canonical = RUNTIME.parse_action(json.dumps(example))
                    legacy = RUNTIME.parse_action(
                        json.dumps({"action": example["action"], **example["arguments"]})
                    )
                    self.assertEqual(canonical["action"], legacy["action"])
                    self.assertEqual(canonical["arguments"], legacy["arguments"])
                    examples.append(example)
            self.assertEqual(len(examples), 2)

    def test_real_focused_timeout_is_archived_once_and_not_reexecuted(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "tests/test_example.py").write_text(
                "import time\nfrom pathlib import Path\nPath('started.flag').write_text('yes')\ntime.sleep(4)\ndef test_wait():\n    assert True\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {
                    "python": sys.executable,
                    "command_timeout_seconds": 2,
                    "invocation_timeout_seconds": 30,
                },
                FakeClient([]),
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                result = runtime.validate({})
                self.assertEqual(result["status"], "failed")
                self.assertTrue(runtime.validation.focused_tests["timed_out"])
                self.assertTrue((root / "started.flag").exists())
                self.assertEqual(len(runtime.validation_refs), 1)
                previous = runtime.validation_refs[0]
                with patch.object(runtime, "_run_command") as command:
                    with self.assertRaisesRegex(
                        RUNTIME.WorkerError, "previous focused tests timed out"
                    ):
                        runtime.validate({})
                    command.assert_not_called()
                self.assertEqual(runtime.validation_refs, [previous])
                self.assertEqual(runtime.validation.status, "failed")
            finally:
                runtime.close()

    def test_unchanged_timed_out_validation_refused_before_command(self):
        for phase in ("check", "final"):
            with self.subTest(phase=phase), TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_tree(root)
                runtime = RUNTIME.WorkerRuntime(
                    root, packet_v2(), {"python": sys.executable}, FakeClient([])
                )
                runtime.write_lock.acquire()
                try:
                    runtime._prepare_run_archive()
                    runtime.validation = RUNTIME.ValidationResult(
                        "failed",
                        {"status": "passed"},
                        {
                            "status": "failed",
                            "timed_out": True,
                            "inputs_unchanged": True,
                            "input_facts": runtime._validation_facts(),
                        },
                        None,
                    )
                    before = runtime.validation_count
                    with patch.object(runtime, "_run_command") as command:
                        with self.assertRaisesRegex(
                            RUNTIME.WorkerError, "previous focused tests timed out"
                        ):
                            runtime.validate({"phase": phase})
                        command.assert_not_called()
                    self.assertEqual(runtime.validation_count, before)
                    self.assertEqual(runtime.validation_refs, [])
                    observation = runtime._validation_observation(runtime.validation)
                    self.assertTrue(observation["focused_tests"]["timed_out"])
                    self.assertIn("unchanged", observation["retry_constraint"])
                finally:
                    runtime.close()

    def test_timeout_retry_allowed_after_changed_inputs_or_for_other_failure(self):
        for change in ("source", "test", "not_timeout", "inputs_changed_during_validation"):
            with self.subTest(change=change), TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_tree(root)
                runtime = RUNTIME.WorkerRuntime(
                    root, packet_v2(), {"python": sys.executable}, FakeClient([])
                )
                runtime.write_lock.acquire()
                try:
                    runtime._prepare_run_archive()
                    runtime.validation = RUNTIME.ValidationResult(
                        "failed",
                        {"status": "passed"},
                        {
                            "status": "failed",
                            "timed_out": True,
                            "inputs_unchanged": True,
                            "input_facts": runtime._validation_facts(),
                        },
                        None,
                    )
                    if change == "source":
                        (root / "src/example.py").write_text("VALUE = 2\n", encoding="utf-8")
                    elif change == "test":
                        path = root / "tests/test_example.py"
                        path.write_text(
                            path.read_text(encoding="utf-8")
                            + "\n# Primary revised diagnostic fixture\n",
                            encoding="utf-8",
                        )
                    elif change == "not_timeout":
                        runtime.validation.focused_tests["timed_out"] = False
                    else:
                        runtime.validation.focused_tests["inputs_unchanged"] = False
                    with patch.object(
                        runtime, "_run_command", side_effect=RuntimeError("command reached")
                    ):
                        with self.assertRaisesRegex(RuntimeError, "command reached"):
                            runtime.validate({})
                finally:
                    runtime.close()

    def test_v13_truthful_diagnostic_is_not_submission(self) -> None:
        for acknowledgement in (False, None):
            with self.subTest(acknowledgement=acknowledgement), TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_tree(root)
                value = packet_v2()
                value["contract_check_required"] = True
                value["required_order"] = ["read before write"]
                value["forbidden_orderings"] = ["write before read"]
                runtime = RUNTIME.WorkerRuntime(
                    root, value, {"python": sys.executable}, FakeClient([])
                )
                runtime.write_lock.acquire()
                try:
                    runtime._prepare_run_archive()
                    check = runtime.contract_check_template()
                    check["required_order_confirmed"] = acknowledgement
                    check["forbidden_orderings_absent"] = acknowledgement
                    result = runtime.validate({"phase": "check", "contract_check": check})
                    self.assertEqual(result["status"], "passed")
                    self.assertIs(
                        runtime.validation.contract_check["required_order_confirmed"],
                        acknowledgement,
                    )
                    self.assertFalse(runtime._validated_terminal_state())
                    with self.assertRaises(RUNTIME.WorkerError):
                        runtime.execute(
                            {"action": "FINISH_SUCCESS", "arguments": {"summary": ["done"]}}
                        )
                    with self.assertRaises(RUNTIME.WorkerError):
                        runtime.validate({"phase": "final", "contract_check": check})
                    self.assertEqual(runtime.validation_count, 1)
                finally:
                    runtime.close()

    def test_v13_green_original_cannot_finish_an_unimplemented_goal(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                self.assertEqual(runtime.validate({"phase": "final"})["status"], "passed")
                self.assertFalse(runtime._validated_terminal_state())
                with self.assertRaises(RUNTIME.WorkerError):
                    runtime.execute(
                        {"action": "FINISH_SUCCESS", "arguments": {"summary": ["done"]}}
                    )
            finally:
                runtime.close()

    def test_v13_baseline_does_not_spend_two_post_implementation_repairs(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "tests/test_example.py").write_text(
                "from src.example import VALUE\ndef test_value():\n    assert VALUE == 2\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                self.assertEqual(runtime.validate({})["status"], "failed")
                self.assertEqual(runtime.validate({})["status"], "failed")

                def edit(old: int, new: int) -> dict:
                    observed = runtime.read_file({"path": "src/example.py"})
                    return runtime.safe_replace(
                        {
                            "path": "src/example.py",
                            "expected_sha256": observed["sha256"],
                            "find": f"VALUE = {old}",
                            "replace": f"VALUE = {new}",
                        }
                    )

                self.assertFalse(edit(1, 3)["repair_edit"])
                self.assertEqual(runtime.repairs, 0)
                self.assertFalse(runtime.pending_failed_validation)
                self.assertEqual(runtime.validate({})["status"], "failed")
                self.assertTrue(edit(3, 4)["repair_edit"])
                self.assertFalse(edit(4, 5)["repair_edit"])
                self.assertEqual(runtime.repairs, 1)
                self.assertEqual(runtime.validate({})["status"], "failed")
                self.assertTrue(edit(5, 6)["repair_edit"])
                self.assertEqual(runtime.repairs, 2)
                self.assertEqual(runtime.validate({})["status"], "failed")
                with self.assertRaisesRegex(RUNTIME.WorkerError, "budget is exhausted"):
                    edit(6, 7)
                self.assertEqual((root / "src/example.py").read_text(), "VALUE = 6\n")
                self.assertEqual(len(runtime.validation_refs), 5)
            finally:
                runtime.close()

    def test_v13_inherited_run_cannot_claim_fresh_baseline_budget(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["parent_run_id"] = "previous-draft"
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, FakeClient([]))
            runtime.write_lock.acquire()
            try:
                runtime.pending_failed_validation = True
                observed = runtime.read_file({"path": "src/example.py"})
                result = runtime.safe_replace(
                    {
                        "path": "src/example.py",
                        "expected_sha256": observed["sha256"],
                        "find": "VALUE = 1",
                        "replace": "VALUE = 2",
                    }
                )
                self.assertTrue(result["repair_edit"])
                self.assertEqual(runtime.repairs, 1)
            finally:
                runtime.close()

    def test_green_baseline_allows_edit_and_legacy_finish_requires_current_check(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "tests/test_example.py").write_text(
                "from src.example import VALUE\n\ndef test_value():\n    assert VALUE in (1, 2)\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                observed = runtime.read_file({"path": "src/example.py"})
                result = runtime.validate({})
                self.assertEqual(result["status"], "passed", result)
                baseline_archive = json.loads(
                    (runtime.archive.run_root / "validation-attempt-1.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(baseline_archive["phase"], "check")
                self.assertFalse(runtime._validated_terminal_state())
                runtime.safe_replace(
                    {
                        "path": "src/example.py",
                        "expected_sha256": observed["sha256"],
                        "find": "VALUE = 1",
                        "replace": "VALUE = 2",
                    }
                )
                with self.assertRaises(RUNTIME.WorkerError):
                    runtime.execute(
                        {"action": "FINISH_SUCCESS", "arguments": {"summary": ["done"]}}
                    )
                self.assertEqual(runtime.validate({})["status"], "passed")
                _, report = runtime.execute(
                    {"action": "FINISH_SUCCESS", "arguments": {"summary": ["done"]}}
                )
                self.assertEqual(report["status"], "ready_for_review")
                (root / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
                self.assertFalse(runtime._validated_terminal_state())
                with self.assertRaises(RUNTIME.WorkerError):
                    runtime.execute(
                        {"action": "FINISH_SUCCESS", "arguments": {"summary": ["done"]}}
                    )
            finally:
                runtime.close()

    def test_final_validation_archive_records_final_only_after_passing(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "tests/test_example.py").write_text(
                "from src.example import VALUE\n\ndef test_value():\n    assert VALUE == 2\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                self.assertEqual(runtime.validate({"phase": "final"})["status"], "failed")
                observed = runtime.read_file({"path": "src/example.py"})
                runtime.safe_replace(
                    {
                        "path": "src/example.py",
                        "expected_sha256": observed["sha256"],
                        "find": "VALUE = 1",
                        "replace": "VALUE = 2",
                    }
                )
                self.assertEqual(runtime.validate({"phase": "final"})["status"], "passed")
                self.assertTrue(runtime._validated_terminal_state())
                phases = [
                    json.loads(
                        (runtime.archive.run_root / f"validation-attempt-{number}.json").read_text(
                            encoding="utf-8"
                        )
                    )["phase"]
                    for number in (1, 2)
                ]
                self.assertEqual(phases, ["check", "final"])
            finally:
                runtime.close()

    def test_invalid_final_phase_does_not_promote_old_success(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            for phase in ([], True, "unknown"):
                with self.assertRaises(RUNTIME.WorkerError):
                    runtime.validate({"phase": phase})
            self.assertFalse(runtime._validated_terminal_state())
            self.assertEqual(runtime.validation_count, 0)

    def test_multiline_line_edit_hint_is_observed_version_bound_and_never_executes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                observed = runtime.read_file({"path": "src/example.py"})
                args = {
                    "path": "src/example.py",
                    "line": 1,
                    "expected_sha256": observed["sha256"],
                    "replacement": "VALUE = 2\nOTHER = 3",
                }
                with self.assertRaises(RUNTIME.SafeEditError) as caught:
                    runtime.safe_replace_line(args)
                hint = caught.exception.details["edit_format_repair"]
                self.assertEqual(hint["action"], "SAFE_REPLACE")
                self.assertEqual(hint["arguments"]["find"], "VALUE = 1")
                self.assertNotIn("replace", hint["arguments"])
                self.assertEqual((root / "src/example.py").read_text(), "VALUE = 1\n")
                self.assertEqual(runtime.edit_revision, 0)
                runtime.safe_replace({**hint["arguments"], "replace": args["replacement"]})
                self.assertEqual((root / "src/example.py").read_text(), "VALUE = 2\nOTHER = 3\n")
                # The old observed hash must not reveal a new target after a change.
                with self.assertRaises(RUNTIME.SafeEditError) as stale:
                    runtime.safe_replace_line(args)
                self.assertEqual(stale.exception.details, {})
                with self.assertRaisesRegex(RUNTIME.WorkerError, "observed"):
                    runtime.safe_replace_line({**args, "line": 9})
            finally:
                runtime.close()

    def test_safe_replace_line_requires_observed_current_line(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                observed = runtime.read_file({"path": "src/example.py"})
                with self.assertRaisesRegex(RUNTIME.WorkerError, "observed"):
                    runtime.safe_replace_line(
                        {
                            "path": "src/example.py",
                            "expected_sha256": observed["sha256"],
                            "line": 2,
                            "replacement": "VALUE = 2",
                        }
                    )
                result = runtime.safe_replace_line(
                    {
                        "path": "src/example.py",
                        "expected_sha256": observed["sha256"],
                        "line_number": "1",
                        "replacement": "VALUE = 2",
                    }
                )
                self.assertEqual(result["status"], "ok")
                self.assertEqual((root / "src/example.py").read_text(), "VALUE = 2\n")
            finally:
                runtime.close()

    def test_prompt_distinguishes_fresh_prevalidation_from_inherited_rework(self) -> None:
        prompt = RUNTIME.WorkerRuntime.system_prompt(None)
        self.assertIn("For a fresh unit", prompt)
        self.assertIn("observed failure, not the expected outcome", prompt)
        self.assertIn("protected test assertion and packet contract", prompt)
        self.assertIn("validated input\nhashes still match", prompt)
        self.assertIn("If the parent edited after its\nlast failed validation", prompt)
        self.assertIn("then edit before\nanother VALIDATE", prompt)

    def test_coder_capability_schema_excludes_shell_git_and_delegation(self) -> None:
        actions = set(RUNTIME.CODER_ACTION_SCHEMA["properties"]["action"]["enum"])
        self.assertTrue(
            {"READ_FILE", "SEARCH", "SAFE_CREATE", "SAFE_REPLACE", "VALIDATE"}.issubset(actions)
        )
        self.assertTrue(actions.isdisjoint({"SHELL", "GIT", "TRACE", "DELEGATE", "RUN_WORKER"}))

    def test_model_request_error_is_reported_as_infrastructure_failure(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet(), {"python": sys.executable}, InfraFailureClient()
            )
            report = runtime.run()
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["protocol_error_count"], 0)
            self.assertEqual(report["infra_failure"]["reason_code"], "input_too_large")
            self.assertEqual(report["infra_failure"]["diagnostics"]["estimated_input_tokens"], 100)

    def test_failed_tests_group_shared_placeholder_as_repair_focus(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": "python.exe"}, FakeClient([])
            )
            validation = RUNTIME.ValidationResult(
                "failed",
                {"status": "passed"},
                {
                    "status": "failed",
                    "diagnostic": {
                        "failures": [
                            {
                                "test": test,
                                "message": "NotImplementedError: SQL query not yet implemented",
                                "location": "src\\example.py:37: NotImplementedError",
                            }
                            for test in ("test_one", "test_two")
                        ]
                    },
                },
            )
            observation = runtime._validation_observation(validation)
            focus = observation["repair_focus"]
            self.assertEqual(len(focus), 1)
            self.assertEqual(focus[0]["test_count"], 2)
            self.assertEqual(focus[0]["tests"], ["test_one", "test_two"])
            self.assertEqual((focus[0]["path"], focus[0]["line"]), ("src/example.py", 37))
            self.assertIn("placeholder", focus[0]["instruction"])
            self.assertLess(
                json.dumps(observation).index('"repair_focus"'),
                json.dumps(observation).index('"focused_tests"'),
            )

    def test_grouped_failure_examples_keep_bindings_in_compact_evidence(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            failures = [
                {
                    "test": f"test_invalid[{value}]",
                    "message": "Failed: DID NOT RAISE ValueError",
                    "location": "tests/test_example.py:1: Failed",
                    "displayed_bindings": [{"name": "width", "representation": value}],
                }
                for value in ("True", "False")
            ]
            focused = {"diagnostic": {"failures": failures}}
            runtime.validation = RUNTIME.ValidationResult("failed", {"status": "passed"}, focused)
            focus = runtime._failed_test_repair_focus(focused)[0]
            self.assertEqual(focus["test_count"], 2)
            self.assertEqual(
                [e["displayed_bindings"][0]["representation"] for e in focus["failure_examples"]],
                ["True", "False"],
            )
            payload = runtime._compact_repair_payload(focus)
            self.assertEqual(len(payload["test_evidence"]), 2)
            self.assertEqual(
                payload["test_evidence"][0]["displayed_bindings"], failures[0]["displayed_bindings"]
            )

    def test_name_error_focus_identifies_verified_type_checking_import(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src" / "example.py"
            source.write_text(
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    from collections import Counter\n"
                "VALUE = Counter()\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": "python.exe"}, FakeClient([])
            )
            runtime.changed["src/example.py"] = {"path": "src/example.py", "operation": "modify"}
            focused = {
                "diagnostic": {
                    "failures": [
                        {
                            "test": "test_one",
                            "message": "NameError: name 'Counter' is not defined",
                            "location": "src\\example.py:4: NameError",
                        },
                        {
                            "test": "test_two",
                            "message": "NameError: name 'Counter' is not defined",
                            "location": "src\\example.py:4: NameError",
                        },
                    ]
                }
            }
            focus = runtime._failed_test_repair_focus(focused)
            self.assertEqual(len(focus), 1)
            self.assertEqual(focus[0]["diagnosis"], "name_imported_only_under_TYPE_CHECKING")
            self.assertIn("Move this runtime dependency", focus[0]["instruction"])
            source.write_text("VALUE = Counter()\n", encoding="utf-8")
            unguarded = runtime._failed_test_repair_focus(focused)[0]
            self.assertEqual(unguarded["diagnosis"], "undefined_name_introduced_in_changed_source")
            self.assertEqual(unguarded["symbol"], "Counter")
            self.assertEqual(unguarded["required_path"], "src/example.py")
            self.assertEqual(unguarded["required_next_action"], "SAFE_REPLACE")
            self.assertIn("Do not rename", unguarded["instruction"])

    def test_unbound_local_focus_identifies_introduced_name_shadowing(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src" / "example.py"
            source.write_text(
                "def value():\n"
                "    result = canonical_json({})\n"
                "    canonical_json = 'shadowed'\n"
                "    return result\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": "python.exe"}, FakeClient([])
            )
            runtime.changed["src/example.py"] = {
                "path": "src/example.py",
                "operation": "modify",
                "sha256": "a" * 64,
            }
            focused = {
                "diagnostic": {
                    "failures": [
                        {
                            "test": "test_value",
                            "message": (
                                "UnboundLocalError: cannot access local variable "
                                "'canonical_json' where it is not associated with a value"
                            ),
                            "location": "src\\example.py:2: UnboundLocalError",
                        }
                    ]
                }
            }
            focus = runtime._failed_test_repair_focus(focused)[0]
            self.assertEqual(focus["diagnosis"], "introduced_local_name_shadowing")
            self.assertEqual(focus["symbol"], "canonical_json")
            self.assertEqual(focus["required_path"], "src/example.py")
            self.assertEqual(focus["expected_sha256"], "a" * 64)
            self.assertEqual(focus["candidate_edit_paths"], ["src/example.py"])
            self.assertEqual(focus["expected_sha256_by_path"], {"src/example.py": "a" * 64})
            self.assertIn("local shadowing", focus["instruction"])

    def test_external_attribute_error_points_to_new_in_scope_access(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src/example.py"
            before = source.read_bytes()
            source.write_text(
                "def value(sample):\n    return sample.unverified_field\n", encoding="utf-8"
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            runtime.preimages["src/example.py"] = before
            runtime.changed["src/example.py"] = {
                "path": "src/example.py",
                "operation": "modify",
                "sha256": RUNTIME.SAFE_EDIT.sha256_bytes(source.read_bytes()),
            }
            focused = {
                "diagnostic": {
                    "failures": [
                        {
                            "test": "tests.test_example::test_value",
                            "message": (
                                "AttributeError: 'Sample' object has no attribute "
                                "'unverified_field'"
                            ),
                            "location": "..\\site-packages\\library.py:1042: AttributeError",
                        }
                    ]
                }
            }
            focus = runtime._failed_test_repair_focus(focused)[0]
            self.assertEqual(focus["diagnosis"], "missing_attribute_introduced_in_changed_source")
            self.assertEqual(focus["required_path"], "src/example.py")
            self.assertEqual(focus["line"], 2)
            self.assertEqual(focus["required_next_action"], "SAFE_REPLACE")
            self.assertIn("third-party location is not the edit target", focus["instruction"])

            source.write_bytes(before)
            unchanged = runtime._failed_test_repair_focus(focused)[0]
            self.assertNotIn("diagnosis", unchanged)

    def test_repair_validation_inherits_prior_required_behavior_ids(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            first = runtime._contract_check(
                {
                    "contract_check": {
                        "required_behavior_ids": ["behavior-value"],
                        "required_order_confirmed": True,
                        "forbidden_orderings_absent": True,
                        "observable_scenario_ids": [],
                        "unrelated_changes": [],
                    }
                }
            )
            inherited = runtime._contract_check(
                {
                    "contract_check": {
                        "required_behavior_ids": [],
                        "required_order_confirmed": True,
                        "forbidden_orderings_absent": True,
                        "observable_scenario_ids": [],
                        "unrelated_changes": [],
                    }
                }
            )
            self.assertEqual(first["required_behavior_ids"], ["behavior-value"])
            self.assertEqual(inherited["required_behavior_ids"], ["behavior-value"])

    def test_compact_name_error_repair_includes_symbol_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src" / "constants.py").write_text("EXPECTED_VALUE = 2\n", encoding="utf-8")
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": "python.exe"}, FakeClient([])
            )
            payload = runtime._compact_repair_payload(
                {
                    "required_next_action": "SAFE_REPLACE",
                    "path": "src/example.py",
                    "candidate_edit_paths": ["src/example.py"],
                    "symbol": "EXPECTED_VALUE",
                }
            )
            self.assertEqual(
                payload["symbol_evidence"][0],
                {
                    "path": "src/constants.py",
                    "line": 1,
                    "quote": "EXPECTED_VALUE = 2",
                },
            )

    def test_assertion_in_protected_test_points_repair_at_changed_source(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": "python.exe"}, FakeClient([])
            )
            runtime.changed["src/example.py"] = {
                "path": "src/example.py",
                "operation": "modified",
                "sha256": "a" * 64,
            }
            focused = {
                "diagnostic": {
                    "failures": [
                        {
                            "test": "test_value",
                            "message": "AssertionError: assert 1 == 2",
                            "location": "tests\\test_example.py:4: AssertionError",
                        }
                    ]
                }
            }
            focus = runtime._failed_test_repair_focus(focused)[0]
            self.assertEqual(focus["test_path"], "tests/test_example.py")
            self.assertEqual(focus["test_line"], 4)
            self.assertEqual(focus["path"], "src/example.py")
            self.assertEqual(focus["candidate_edit_paths"], ["src/example.py"])
            self.assertEqual(focus["required_next_action"], "SAFE_REPLACE")
            self.assertEqual(focus["expected_sha256"], "a" * 64)
            self.assertEqual(focus["expected_sha256_by_path"], {"src/example.py": "a" * 64})
            self.assertIn("protected focused test", focus["instruction"])

            runtime.validation = RUNTIME.ValidationResult("failed", {"status": "passed"}, focused)
            runtime.pending_failed_validation = True
            self.assertEqual(
                runtime._required_repair_focus()["required_next_action"], "SAFE_REPLACE"
            )

            runtime.changed.clear()
            runtime.observed_hashes["src/example.py"] = "b" * 64
            pre_edit_focus = runtime._failed_test_repair_focus(focused)[0]
            self.assertEqual(pre_edit_focus["path"], "src/example.py")
            self.assertEqual(pre_edit_focus["required_next_action"], "SAFE_REPLACE")
            self.assertEqual(pre_edit_focus["expected_sha256"], "b" * 64)
            payload = runtime._compact_repair_payload(pre_edit_focus)
            self.assertEqual(payload["required_next_action"], "SAFE_REPLACE")
            self.assertEqual(payload["source_excerpts"][0]["path"], "src/example.py")
            self.assertIn("VALUE = 1", payload["source_excerpts"][0]["content"])

    def test_exception_message_mismatch_has_bounded_source_backed_focus(self) -> None:
        for source, expected_line in (
            ('raise TypeError("wrong message")\n', 1),
            ('raise TypeError("wrong message")\nraise TypeError("wrong message")\n', None),
            ("raise TypeError(message)\n", None),
        ):
            with self.subTest(source=source), TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_tree(root)
                (root / "src/example.py").write_text(source, encoding="utf-8")
                runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {}, FakeClient([]))
                runtime.changed["src/example.py"] = {"sha256": "a" * 64}
                focused = {
                    "diagnostic": {
                        "failures": [
                            {
                                "test": "test_error",
                                "location": "tests/test_example.py:4: AssertionError",
                                "message": "AssertionError: Regex pattern did not match.\n"
                                "  Expected regex: 'message.*sequence'\n  Actual message: 'wrong message'",
                            }
                        ]
                    }
                }
                focus = runtime._failed_test_repair_focus(focused)[0]
                self.assertEqual(focus["diagnosis"], "exception_message_regex_mismatch")
                self.assertEqual(focus["expected_regex"], "message.*sequence")
                self.assertEqual(focus["actual_message"], "wrong message")
                self.assertEqual(focus.get("line"), expected_line)
                self.assertIn("exception type", focus["instruction"])
                payload = runtime._compact_repair_payload(focus)
                self.assertEqual(payload["repair_focus"]["expected_regex"], "message.*sequence")
                if expected_line:
                    self.assertEqual(
                        focus["expected_sha256"], runtime.editor.read_bytes("src/example.py")[1]
                    )
                elif source.count('"wrong message"') == 2:
                    self.assertEqual(focus["message_source_candidate_count"], 2)
                    self.assertNotIn("required_path", focus)
                    self.assertEqual(
                        [
                            c["candidate_raise_line"]
                            for c in payload["repair_focus"]["message_source_candidates"]
                        ],
                        [1, 2],
                    )
                    self.assertTrue(
                        all(
                            c["sha256"] == runtime.editor.read_bytes("src/example.py")[1]
                            for c in focus["message_source_candidates"]
                        )
                    )

    def test_message_mismatch_does_not_interpret_truncated_or_executable_values(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {}, FakeClient([]))
            for message in (
                "AssertionError: Regex pattern did not match.\n  Expected regex: 'x'",
                "AssertionError: Regex pattern did not match.\n  Expected regex: eval('x')\n  Actual message: 'y'",
                "AssertionError: DID NOT RAISE <class 'TypeError'>",
            ):
                focused = {
                    "diagnostic": {
                        "failures": [
                            {
                                "message": message,
                                "location": "tests/test_example.py:4: AssertionError",
                            }
                        ]
                    }
                }
                focus = runtime._failed_test_repair_focus(focused)[0]
                self.assertNotIn("expected_regex", focus)
                self.assertNotIn("diagnosis", focus)

    def test_post_edit_failure_keeps_unchanged_multi_file_candidates(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            second = root / "src" / "second.py"
            second.write_text("OTHER = 1\n", encoding="utf-8")
            packet = packet_v2()
            packet["scope"]["modify"].append("src/second.py")
            packet.setdefault("edit_targets", []).append(
                {"path": "src/second.py", "anchor": "OTHER"}
            )
            runtime = RUNTIME.WorkerRuntime(root, packet, {"python": "python.exe"}, FakeClient([]))
            runtime.changed["src/example.py"] = {
                "path": "src/example.py",
                "operation": "modified",
                "sha256": "a" * 64,
            }
            runtime.observed_hashes["src/second.py"] = "b" * 64
            runtime.validation_failure_delta = {
                "resolved_failures": ["tests/test_example.py::test_old"],
                "remaining_failures": ["tests/test_example.py::test_value"],
                "new_failures": ["tests/test_example.py::test_value"],
            }
            focused = {
                "diagnostic": {
                    "failures": [
                        {
                            "test": "test_value",
                            "message": "AssertionError: assert 1 == 2",
                            "location": "tests\\test_example.py:4: AssertionError",
                        }
                    ]
                }
            }
            focus = runtime._failed_test_repair_focus(focused)[0]
            self.assertEqual(
                set(focus["candidate_edit_paths"]), {"src/example.py", "src/second.py"}
            )
            self.assertNotIn("required_path", focus)
            self.assertEqual(focus["suggested_path"], "src/second.py")
            self.assertTrue(focus["suggestion_is_advisory"])
            self.assertEqual(focus["expected_sha256_by_path"]["src/example.py"], "a" * 64)

    def test_failed_test_symbol_selects_matching_edit_target_and_narrow_excerpt(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            second = root / "src" / "second.py"
            second.write_text(
                "def unrelated():\n    return 0\n\ndef score_reuse_key():\n    return 1\n",
                encoding="utf-8",
            )
            packet = packet_v2()
            packet["scope"]["modify"].append("src/second.py")
            packet["edit_targets"] = [
                {"path": "src/example.py", "anchor": "VALUE"},
                {"path": "src/second.py", "anchor": "def score_reuse_key"},
            ]
            runtime = RUNTIME.WorkerRuntime(root, packet, {"python": "python.exe"}, FakeClient([]))
            runtime.observed_hashes["src/second.py"] = "b" * 64
            focused = {
                "diagnostic": {
                    "failures": [
                        {
                            "test": "tests.test_example::test_score_reuse_key_is_stable",
                            "message": "AssertionError",
                            "location": "tests\\test_example.py:4: AssertionError",
                        }
                    ]
                }
            }
            focus = runtime._failed_test_repair_focus(focused)[0]
            self.assertEqual(focus["candidate_edit_paths"], ["src/second.py"])
            self.assertEqual(focus["candidate_reason"], "failed_test_matches_edit_target_anchor")
            self.assertEqual(focus["required_path"], "src/second.py")
            payload = runtime._compact_repair_payload(focus)
            excerpt = payload["source_excerpts"][0]
            self.assertEqual(excerpt["path"], "src/second.py")
            self.assertEqual(excerpt["start_line"], 2)

    def test_safe_replace_rejects_noop_without_spending_repair(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": "python.exe"}, FakeClient([])
            )
            runtime.pending_failed_validation = True
            runtime.validation = RUNTIME.ValidationResult(
                "failed", {"status": "passed"}, {"status": "failed"}
            )
            with self.assertRaisesRegex(RUNTIME.WorkerError, "identical"):
                runtime.safe_replace(
                    {
                        "path": "src/example.py",
                        "expected_sha256": runtime.initial_hashes["src/example.py"],
                        "find": "VALUE = 1",
                        "replace": "VALUE = 1",
                    }
                )
            self.assertEqual(runtime.repairs, 0)

    def test_failed_validation_edit_shape_and_noop_reach_current_validation(self) -> None:
        class RepairReplayClient:
            def __init__(self) -> None:
                self.step = 0
                self.source_hash = ""

            def complete(self, messages: list[dict[str, str]]) -> str:
                self.step += 1
                observations = [
                    json.loads(item["content"].split("\n", 1)[1])
                    for item in messages
                    if item["role"] == "user" and item["content"].startswith("OBSERVATION\n")
                ]
                if self.step == 1:
                    action = {"action": "READ_FILE", "arguments": {"path": "src/example.py"}}
                elif self.step == 2:
                    self.source_hash = observations[-1]["sha256"]
                    action = {"action": "VALIDATE", "arguments": {}}
                elif self.step == 3:
                    action = {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": self.source_hash,
                            "find": "VALUE = 1\n",
                            "replace": "VALUE = 2  \n",
                        },
                    }
                elif self.step == 4:
                    action = {"action": "READ_FILE", "arguments": {"path": "src/example.py"}}
                elif self.step == 5:
                    self.source_hash = observations[-1]["sha256"]
                    action = {
                        "action": "SAFE_REPLACE_LINE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": self.source_hash,
                            "line": 1,
                            "replacement": "VALUE = 2\nOTHER = 3",
                        },
                    }
                elif self.step == 6:
                    action = {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": self.source_hash,
                            "find": "VALUE = 2  ",
                            "replace": "VALUE = 2",
                        },
                    }
                elif self.step == 7:
                    action = {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": self.source_hash,
                            "find": "VALUE = 2",
                            "replace": "VALUE = 2",
                        },
                    }
                elif self.step == 8:
                    self.assertion = observations[-1]["required_next_action"]
                    action = {"action": "VALIDATE", "arguments": {}}
                else:
                    action = {
                        "action": "FINISH_SUCCESS",
                        "arguments": {
                            "summary": ["Validated current draft."],
                            "remaining_uncertainty": [],
                        },
                    }
                return json.dumps(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "tests" / "test_example.py").write_text(
                "import runpy\n\ndef test_value():\n    assert runpy.run_path('src/example.py')['VALUE'] == 2\n",
                encoding="utf-8",
            )
            value = packet_v2()
            value["limits"] = {"max_model_turns": 14}
            client = RepairReplayClient()
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, client)
            report = runtime.run()
            self.assertEqual(report["status"], "ready_for_review")
            self.assertEqual(client.assertion, "VALIDATE")
            self.assertEqual(runtime.protocol_errors, 0)
            self.assertEqual(runtime.validation_count, 2)
            self.assertFalse(runtime.noop_validation_pending)
            self.assertEqual((root / "src/example.py").read_text(), "VALUE = 2\n")

    def test_placeholder_warning_only_for_new_executable_raise(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src" / "example.py"
            before = source.read_bytes()
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": "python.exe"}, FakeClient([])
            )
            runtime.preimages["src/example.py"] = before
            source.write_text(
                "VALUE = 1\n# TODO: document this\nraise NotImplementedError('draft')\n",
                encoding="utf-8",
            )
            warning = runtime._introduced_placeholders()
            self.assertEqual(
                [(item["path"], item["line"]) for item in warning], [("src/example.py", 3)]
            )
            source.write_text("VALUE = 1\n# TODO: document this\n", encoding="utf-8")
            self.assertEqual(runtime._introduced_placeholders(), [])
            runtime.preimages["src/example.py"] = b"raise NotImplementedError('draft')\n"
            source.write_text("raise NotImplementedError('draft')\n", encoding="utf-8")
            self.assertEqual(runtime._introduced_placeholders(), [])

    def test_failed_validation_no_evidence_guard_preserves_repair_focus(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["limits"] = {"max_model_turns": 12, "max_failed_validation_no_evidence_streak": 4}
            client = FakeClient(
                [{"action": "VALIDATE", "arguments": {}}]
                + [
                    {"action": "SEARCH", "arguments": {"path": "src/example.py", "query": "absent"}}
                    for _ in range(4)
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, client)
            validation = RUNTIME.ValidationResult(
                "failed",
                {"status": "passed"},
                {
                    "status": "failed",
                    "diagnostic": {
                        "failures": [
                            {
                                "test": "test_one",
                                "message": "NotImplementedError: draft",
                                "location": "src\\example.py:2: NotImplementedError",
                            }
                        ]
                    },
                },
            )
            original_execute = runtime.execute

            def execute(action: dict) -> tuple[dict, dict | None]:
                if action["action"] == "VALIDATE":
                    runtime.validation = validation
                    runtime.pending_failed_validation = True
                    return {
                        "status": "failed",
                        "validation": runtime._validation_observation(validation),
                    }, None
                return original_execute(action)

            with patch.object(runtime, "execute", side_effect=execute):
                report = runtime.run()
            self.assertEqual(report["failure_reason"], "no_new_evidence_after_failed_validation")
            self.assertEqual(report["runtime_facts"]["failed_validation_no_evidence_streak"], 4)
            self.assertIn("src/example.py", report["worker_claims"]["remaining_uncertainty"][0])

    def test_failed_validation_prefetches_editable_repair_context(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {"action": "VALIDATE", "arguments": {}},
                    {
                        "action": "FINISH_BLOCKED",
                        "arguments": {
                            "reason_code": "no_progress",
                            "reason": "Stopping without an edit.",
                        },
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client)
            validation = RUNTIME.ValidationResult(
                "failed",
                {"status": "passed"},
                {
                    "status": "failed",
                    "diagnostic": {
                        "failures": [
                            {
                                "test": "tests.test_example::test_value",
                                "message": "AssertionError: assert 1 == 2",
                                "location": "tests\\test_example.py:2: AssertionError",
                            }
                        ]
                    },
                },
            )
            original_execute = runtime.execute

            def execute(action: dict) -> tuple[dict, dict | None]:
                if action["action"] == "VALIDATE":
                    runtime.validation = validation
                    runtime.pending_failed_validation = True
                    return {"status": "failed"}, None
                return original_execute(action)

            with patch.object(runtime, "execute", side_effect=execute):
                runtime.run()
            repair_messages = client.messages_seen[2]
            repair_message = repair_messages[-1]["content"]
            self.assertTrue(repair_message.startswith("REPAIR_REQUIRED\n"))
            self.assertTrue(
                any(message["content"].startswith("OBSERVATION\n") for message in repair_messages)
            )
            payload = json.loads(repair_message.split("\n", 1)[1])
            self.assertEqual(payload["source_excerpts"][0]["path"], "src/example.py")
            self.assertIn("AssertionError", payload["repair_focus"]["message"])
            events = (root / ".agent/tasks/test-1/runs/test-1-a1/events.jsonl").read_text()
            self.assertIn("repair_context_prefetched", events)

    def test_repeated_positive_search_is_not_new_repair_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            query = {"path": "src/example.py", "query": "VALUE"}
            first = runtime.search(query)
            repeated = runtime.search(query)
            self.assertEqual(len(first["results"]), 1)
            self.assertEqual(first["new_evidence_count"], 1)
            self.assertEqual(len(repeated["results"]), 1)
            self.assertEqual(repeated["new_evidence_count"], 0)

    def test_repeated_positive_search_triggers_repair_nudge(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient(
                [
                    {"action": "VALIDATE", "arguments": {}},
                    {"action": "SEARCH", "arguments": {"path": "src/example.py", "query": "VALUE"}},
                    {"action": "SEARCH", "arguments": {"path": "src/example.py", "query": "VALUE"}},
                    {
                        "action": "FINISH_BLOCKED",
                        "arguments": {
                            "summary": ["Unable to repair."],
                            "reason_code": "no_progress",
                            "reason": "Stopping",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client)
            original_execute = runtime.execute

            def execute(action: dict) -> tuple[dict, dict | None]:
                if action["action"] == "VALIDATE":
                    runtime.pending_failed_validation = True
                    return {"status": "failed", "validation": {"status": "failed"}}, None
                return original_execute(action)

            focus = {"required_next_action": "SAFE_REPLACE", "required_path": "src/example.py"}
            with (
                patch.object(runtime, "execute", side_effect=execute),
                patch.object(
                    runtime,
                    "_required_repair_focus",
                    side_effect=lambda: focus if runtime.pending_failed_validation else None,
                ),
            ):
                runtime.run()
            self.assertEqual(runtime.repair_supervision_states, {(0, 0)})

    def test_new_evidence_cannot_extend_one_repair_version_indefinitely(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src" / "example.py").write_text(
                "".join(f"TOKEN_{number} = {number}\n" for number in range(5)),
                encoding="utf-8",
            )
            actions = [{"action": "VALIDATE", "arguments": {}}]
            actions.extend(
                {
                    "action": "SEARCH",
                    "arguments": {"path": "src/example.py", "query": f"TOKEN_{number}"},
                }
                for number in range(5)
            )
            actions.append(
                {
                    "action": "FINISH_BLOCKED",
                    "arguments": {
                        "reason_code": "no_progress",
                        "reason": "Stopping",
                    },
                }
            )
            client = FakeClient(actions)
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client)
            original_execute = runtime.execute

            def execute(action: dict) -> tuple[dict, dict | None]:
                if action["action"] == "VALIDATE":
                    runtime.pending_failed_validation = True
                    return {"status": "failed", "validation": {"status": "failed"}}, None
                return original_execute(action)

            focus = {"required_next_action": "SAFE_REPLACE", "required_path": "src/example.py"}
            with (
                patch.object(runtime, "execute", side_effect=execute),
                patch.object(
                    runtime,
                    "_required_repair_focus",
                    side_effect=lambda: focus if runtime.pending_failed_validation else None,
                ),
            ):
                runtime.run()
            self.assertEqual(runtime.repair_evidence_action_counts[(0, 0)], 5)
            self.assertEqual(runtime.repair_supervision_states, {(0, 0)})

    def test_post_edit_reads_must_yield_to_an_edit_or_validation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src" / "example.py"
            source.write_text(
                "VALUE = 1\n" + "".join(f"TOKEN_{number} = {number}\n" for number in range(4)),
                encoding="utf-8",
            )
            digest = RUNTIME.SAFE_EDIT.sha256_bytes(source.read_bytes())
            actions = [
                {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                {
                    "action": "SAFE_REPLACE",
                    "arguments": {
                        "path": "src/example.py",
                        "expected_sha256": digest,
                        "find": "VALUE = 1\n",
                        "replace": "VALUE = 2\n",
                    },
                },
            ]
            actions.extend(
                {
                    "action": "SEARCH",
                    "arguments": {"path": "src/example.py", "query": f"TOKEN_{number}"},
                }
                for number in range(4)
            )
            actions.extend(
                [
                    {
                        "action": "SEARCH",
                        "arguments": {"path": "src/example.py", "query": "TOKEN_0"},
                    },
                    {
                        "action": "FINISH_BLOCKED",
                        "arguments": {
                            "reason_code": "no_progress",
                            "reason": "Stopping",
                        },
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient(actions)
            )
            runtime.run()
            self.assertEqual(runtime.post_edit_evidence_counts[1], 4)
            self.assertEqual(runtime.post_edit_progress_nudges, {1})

    def test_post_edit_progress_schema_allows_validation_and_edits(self) -> None:
        schema = RUNTIME.post_edit_progress_schema(RUNTIME.CODER_ACTION_SCHEMA)
        self.assertEqual(
            schema["properties"]["action"]["enum"],
            [
                "SAFE_REPLACE",
                "SAFE_REPLACE_LINE",
                "SAFE_CREATE",
                "VALIDATE",
                "FINISH_BLOCKED",
                "REQUEST_CONTRACT_REVISION",
            ],
        )
        self.assertIn("READ_FILE", RUNTIME.CODER_ACTION_SCHEMA["properties"]["action"]["enum"])

    def make_tree(self, root: Path) -> None:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "example.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "tests" / "test_example.py").write_text(
            "def test_value(): pass\n", encoding="utf-8"
        )

    def test_runtime_rejects_out_of_scope_edit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient(
                [
                    {
                        "action": "SAFE_CREATE",
                        "arguments": {"path": "src/secret.py", "content": "bad\n"},
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Scope prevented the edit."],
                            "reason": "not authorized",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, packet(), {"python": "python.exe"}, client)
            report = runtime.run()
            self.assertEqual(report["status"], "failed")
            self.assertFalse((root / "src" / "secret.py").exists())
            self.assertEqual(report["protocol_error_count"], 1)

    def test_diagnostic_events_exclude_edit_content_and_can_be_disabled(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            secret = "PRIVATE_REPLACEMENT_TEXT"
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": "wrong",
                            "find": "VALUE = 1\n",
                            "replace": secret,
                        },
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Stopped."],
                            "reason": "No edit",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            report = RUNTIME.WorkerRuntime(root, packet(), {"python": sys.executable}, client).run()
            events = (
                root / ".agent" / "tasks" / "test-1" / "runs" / "test-1-a1" / "events.jsonl"
            ).read_text(encoding="utf-8")
            self.assertEqual(report["status"], "failed")
            self.assertNotIn(secret, events)
            self.assertIn("replace_sha256", events)
            self.assertIn("response_chars", events)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            report = RUNTIME.WorkerRuntime(
                root,
                packet(),
                {"python": sys.executable, "diagnostic_logging": False},
                FakeClient(
                    [
                        {
                            "action": "FINISH_FAILED",
                            "arguments": {
                                "summary": ["Stopped."],
                                "reason": "No edit",
                                "remaining_uncertainty": [],
                            },
                        }
                    ]
                ),
            ).run()
            events = (
                root / ".agent" / "tasks" / "test-1" / "runs" / "test-1-a1" / "events.jsonl"
            ).read_text(encoding="utf-8")
            self.assertEqual(report["status"], "failed")
            self.assertNotIn("response_sha256", events)

    def test_junit_failure_summary_keeps_each_failed_assertion(self) -> None:
        root = ET.fromstring(
            '<testsuite tests="2" failures="2">'
            '<testcase classname="tests.test_runner" name="test_rationale">'
            '<failure message="ValidationError: rationale required">runner.py:87: ValidationError</failure>'
            "</testcase>"
            '<testcase classname="tests.test_runner" name="test_invalid_count">'
            '<failure message="Failed: DID NOT RAISE ValueError">test_runner.py:112: Failed</failure>'
            "</testcase></testsuite>"
        )
        failures = RUNTIME.WorkerRuntime._junit_failures(root)
        self.assertEqual(len(failures), 2)
        self.assertIn("rationale", failures[0]["message"])
        self.assertIn("DID NOT RAISE", failures[1]["message"])

    def test_junit_passed_test_ids_excludes_failed_and_skipped_cases(self) -> None:
        root = ET.fromstring(
            '<testsuite tests="3" failures="1" skipped="1">'
            '<testcase classname="tests.test_identity" name="test_preserves_source_metadata" />'
            '<testcase classname="tests.test_identity" name="test_ignores_row_identity">'
            '<failure message="failed">test_identity.py:10</failure></testcase>'
            '<testcase classname="tests.test_identity" name="test_optional"><skipped /></testcase>'
            "</testsuite>"
        )
        self.assertEqual(
            RUNTIME.WorkerRuntime._junit_passed_test_ids(root),
            ["tests.test_identity::test_preserves_source_metadata"],
        )

    def test_ruff_unused_variable_hint_points_to_local_line(self) -> None:
        hint = RUNTIME.WorkerRuntime._configured_check_repair_hint(
            [
                {
                    "id": "ruff-check",
                    "status": "failed",
                    "output": (
                        "F841 Local variable `config_json` is assigned to but never used\n"
                        "  --> src\\evaluations\\dedup.py:28:9\n"
                        "help: Remove assignment to unused variable `config_json`\n"
                    ),
                }
            ]
        )
        self.assertEqual(hint["rule"], "F841")
        self.assertEqual(hint["path"], "src/evaluations/dedup.py")
        self.assertEqual(hint["line"], 28)
        self.assertIn("preserving", hint["instruction"])
        self.assertIn('replace ""', hint["instruction"])
        self.assertIn("keep neighboring statements unchanged", hint["instruction"])

    def test_ruff_f821_becomes_early_repair_focus_when_tests_pass(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            check = {
                "id": "ruff-check",
                "status": "failed",
                "output": "F821 Undefined name `AsyncSession`\n  --> src\\example.py:17:14\nFound 1 error.\n",
            }
            validation = RUNTIME.ValidationResult(
                "failed",
                {"status": "passed"},
                {"status": "passed", "diagnostic": {"failures": []}},
                configured_checks=[check],
            )
            observation = runtime._validation_observation(validation)
            focus = observation["repair_focus"]
            self.assertEqual(len(focus), 1)
            self.assertEqual(
                (focus[0]["rule"], focus[0]["symbol"], focus[0]["path"], focus[0]["line"]),
                ("F821", "AsyncSession", "src/example.py", 17),
            )
            self.assertIn("one narrow edit", focus[0]["instruction"])
            encoded = json.dumps(observation)
            self.assertLess(encoded.index('"repair_focus"'), encoded.index('"configured_checks"'))

    def test_coder_search_is_literal_by_default_and_regex_is_explicit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            source = root / "src" / "example.py"
            source.write_text("def target_endpoint(value):\n    return value\n", encoding="utf-8")
            literal = runtime.search({"path": "src/example.py", "query": "target_endpoint("})
            self.assertEqual(literal["results"][0]["line"], 1)
            regex = runtime.search(
                {"path": "src/example.py", "query": r"target_\w+", "mode": "regex"}
            )
            self.assertEqual(regex["results"][0]["line"], 1)
            globstar = runtime.search(
                {"path": "src", "glob": "**/src/example.py", "query": "target_endpoint"}
            )
            self.assertEqual(globstar["results"][0]["path"], "src/example.py")
            with self.assertRaisesRegex(RUNTIME.WorkerError, "invalid SEARCH regex"):
                runtime.search({"path": "src/example.py", "query": "(", "mode": "regex"})

    def test_repeated_same_test_failures_stop_and_keep_each_validation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient([{"action": "VALIDATE", "arguments": {}} for _ in range(3)])
            value = packet_v2()
            value["scope"]["readonly"] = ["tests/test_example.py"]
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, client)

            def failed_pytest(argv):
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuite tests="1" failures="1">'
                            '<testcase classname="tests.test_example" name="test_value">'
                            '<failure message="AssertionError: expected value">'
                            "src/example.py:1: AssertionError"
                            "</failure></testcase></testsuite>",
                            encoding="utf-8",
                        )
                return {
                    "status": "failed",
                    "exit_code": 1,
                    "output": "FAILED tests/test_example.py::test_value - AssertionError: expected value",
                    "argv": argv,
                }

            with patch.object(runtime, "_run_command", side_effect=failed_pytest):
                report = runtime.run()
            self.assertEqual(report["failure_reason"], "unchanged_validation_failures")
            self.assertEqual(len(report["evidence_refs"]["validation_attempts"]), 2)
            for ref in report["evidence_refs"]["validation_attempts"]:
                self.assertTrue((root / ref).is_file())
            self.assertEqual(report["runtime_facts"]["same_test_failure_streak"], 2)
            self.assertEqual(report["runtime_facts"]["unchanged_test_failure_streak"], 2)
            self.assertIn("Do not assume the test is stale", report["remaining_uncertainty"][0])

    def test_same_failure_after_an_edit_gets_repair_chance(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            digest = RUNTIME.SAFE_EDIT.sha256_bytes((root / "src" / "example.py").read_bytes())
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {"action": "VALIDATE", "arguments": {}},
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": digest,
                            "find": "VALUE = 1\n",
                            "replace": "VALUE = 2\n",
                        },
                    },
                    {"action": "VALIDATE", "arguments": {}},
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Need a further repair."],
                            "reason": "needs_rework",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client)

            def failed_pytest(argv):
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuite tests="1" failures="1">'
                            '<testcase classname="tests.test_example" name="test_value">'
                            '<failure message="AssertionError: expected value">'
                            "tests/test_example.py:1: AssertionError"
                            "</failure></testcase></testsuite>",
                            encoding="utf-8",
                        )
                return {
                    "status": "failed",
                    "exit_code": 1,
                    "output": "FAILED tests/test_example.py::test_value - AssertionError: expected value",
                    "argv": argv,
                }

            with patch.object(runtime, "_run_command", side_effect=failed_pytest):
                report = runtime.run()
            self.assertEqual(report["failure_reason"], "needs_rework")
            self.assertEqual(len(report["evidence_refs"]["validation_attempts"]), 2)
            self.assertEqual(report["runtime_facts"]["unchanged_test_failure_streak"], 1)

    def test_failed_validation_snapshot_survives_later_edit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            digest = RUNTIME.SAFE_EDIT.sha256_bytes((root / "src" / "example.py").read_bytes())
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {"action": "VALIDATE", "arguments": {}},
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": digest,
                            "find": "VALUE = 1\n",
                            "replace": "VALUE = 2\n",
                        },
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Needs another validation."],
                            "reason": "Stopped",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client)

            def failed_pytest(argv):
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuite tests="1" failures="1">'
                            '<testcase classname="tests.test_example" name="test_value">'
                            '<failure message="AssertionError">failed</failure>'
                            "</testcase></testsuite>",
                            encoding="utf-8",
                        )
                return {
                    "status": "failed",
                    "exit_code": 1,
                    "output": "FAILED tests/test_example.py::test_value",
                    "argv": argv,
                }

            with patch.object(runtime, "_run_command", side_effect=failed_pytest):
                report = runtime.run()
            archive = root / report["evidence_refs"]["run_archive"]
            self.assertEqual(
                json.loads((archive / "validation.json").read_text(encoding="utf-8")), None
            )
            self.assertEqual(len(report["evidence_refs"]["validation_attempts"]), 1)
            snapshot = json.loads(
                (root / report["evidence_refs"]["validation_attempts"][0]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(snapshot["validation"]["status"], "failed")

    def test_invalid_validation_does_not_release_draft_gate(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["contract_check_required"] = True
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, FakeClient([]))
            try:
                runtime.noop_validation_pending = True
                with self.assertRaisesRegex(RUNTIME.WorkerError, "contract_check"):
                    runtime.validate({})
                self.assertTrue(runtime.noop_validation_pending)
                self.assertEqual(runtime.validation_count, 0)
            finally:
                runtime.close()

    def test_mismatch_after_edit_requires_current_draft_validation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "tests/test_example.py").write_text(
                "import runpy\n\ndef test_value():\n    assert runpy.run_path('src/example.py')['VALUE'] == 2\n",
                encoding="utf-8",
            )
            original_bytes = (root / "src/example.py").read_bytes()
            before = RUNTIME.SAFE_EDIT.sha256_bytes(original_bytes)
            after = RUNTIME.SAFE_EDIT.sha256_bytes(
                original_bytes.replace(b"VALUE = 1", b"VALUE = 2")
            )
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": before,
                            "find": "VALUE = 1",
                            "replace": "VALUE = 2",
                        },
                    },
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": after,
                            "find": "VALUE = 999",
                            "replace": "VALUE = 3",
                        },
                    },
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": after,
                            "find": "VALUE = 2",
                            "replace": "VALUE = 3",
                        },
                    },
                    {"action": "VALIDATE", "arguments": {}},
                    {
                        "action": "FINISH_SUCCESS",
                        "arguments": {"summary": ["Validated."], "remaining_uncertainty": []},
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, packet(), {"python": sys.executable}, client)
            report = runtime.run()
            self.assertEqual(report["status"], "ready_for_review", json.dumps(report))
            self.assertEqual(runtime.validation_count, 1)
            self.assertEqual((root / "src/example.py").read_text(), "VALUE = 2\n")
            mismatch_observation = json.loads(
                client.messages_seen[3][-1]["content"].split("\n", 1)[1]
            )
            self.assertEqual(mismatch_observation["required_next_action"], "VALIDATE")
            self.assertTrue(
                mismatch_observation["edit_repair"]["current_lines_are_navigation_only"]
            )
            self.assertEqual(
                mismatch_observation["edit_repair"]["suggested_action"]["action"], "READ_FILE"
            )

    def test_replace_mismatch_rejects_large_retry_and_reports_quality_lines(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            digest = RUNTIME.SAFE_EDIT.sha256_bytes((root / "src" / "example.py").read_bytes())
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": digest,
                            "find": "MISSING\n",
                            "replace": "VALUE = 2\n",
                        },
                    },
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": digest,
                            "find": "X" * 1001,
                            "replace": "VALUE = 2\n",
                        },
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Stopped."],
                            "reason": "No edit",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            report = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, client
            ).run()
            self.assertEqual(
                report["protocol_error_details"][-1]["error_code"],
                "oversized_replace_after_mismatch",
            )
            self.assertNotIn("response", report["protocol_error_details"][-1])
            self.assertEqual(
                (root / "src" / "example.py").read_text(encoding="utf-8"), "VALUE = 1\n"
            )

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                observed = runtime.read_file({"path": "src/example.py"})
                result = runtime.safe_replace(
                    {
                        "path": "src/example.py",
                        "expected_sha256": observed["sha256"],
                        "find": "VALUE = 1\n",
                        "replace": "VALUE = 2  \n",
                    }
                )
            finally:
                runtime.close()
            self.assertEqual(
                (root / "src" / "example.py").read_text(encoding="utf-8"), "VALUE = 2  \n"
            )
            self.assertTrue(runtime._introduced_text_quality_issues())
            self.assertEqual(result["diff_quality_warnings"][0]["line"], 1)

    def test_coder_blocks_duplicate_read_until_file_content_changes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            first = runtime.read_file({"path": "src/example.py"})
            duplicate = runtime.read_file(
                {
                    "path": "src/example.py",
                    "start_line": 1,
                    "end_line": 1,
                }
            )
            self.assertEqual(duplicate["status"], "already_read")
            self.assertEqual(duplicate["sha256"], first["sha256"])
            self.assertNotIn("content", duplicate)
            runtime.write_lock.acquire()
            try:
                runtime.safe_replace(
                    {
                        "path": "src/example.py",
                        "expected_sha256": first["sha256"],
                        "find": "VALUE = 1\n",
                        "replace": "VALUE = 2\n",
                    }
                )
            finally:
                runtime.close()
            refreshed = runtime.read_file({"path": "src/example.py"})
            self.assertNotEqual(first["sha256"], refreshed["sha256"])

    def test_duplicate_read_does_not_consume_protocol_budget(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Stopped after duplicate read."],
                            "reason": "No further edit required",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            report = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, client
            ).run()
            self.assertEqual(report["protocol_error_count"], 0)
            self.assertEqual(report["runtime_facts"]["duplicate_read_count"], 1)

    def test_narrow_range_from_broad_read_is_replayed_once(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src" / "example.py").write_text(
                "\n".join(f"VALUE_{line} = {line}" for line in range(1, 101)) + "\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            runtime.read_file({"path": "src/example.py", "start_line": 1, "end_line": 100})
            replay = runtime.read_file(
                {
                    "path": "src/example.py",
                    "start_line": 50,
                    "end_line": 55,
                }
            )
            self.assertEqual(replay["status"], "replayed")
            self.assertIn("VALUE_50", replay["content"])
            duplicate = runtime.read_file(
                {
                    "path": "src/example.py",
                    "start_line": 50,
                    "end_line": 55,
                }
            )
            self.assertEqual(duplicate["status"], "already_read")
            self.assertEqual(runtime.read_counts[("src/example.py", replay["sha256"])], 1)

    def test_edit_target_coverage_is_required_only_when_configured(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            runtime = RUNTIME.WorkerRuntime(
                root,
                value,
                {"python": sys.executable, "require_edit_targets": True},
                FakeClient([]),
            )
            with self.assertRaisesRegex(RUNTIME.PreflightBlocked, "stable symbol/anchor"):
                runtime.preflight()
            value["edit_targets"] = [
                {
                    "path": "src/example.py",
                    "anchor": "VALUE",
                    "line_hint": 1,
                }
            ]
            normalized = RUNTIME.validate_packet(value)
            self.assertEqual(normalized["edit_targets"][0]["anchor"], "VALUE")
            value["edit_targets"][0]["line_hint"] = 0
            with self.assertRaisesRegex(RUNTIME.WorkerError, "positive integer"):
                RUNTIME.validate_packet(value)
            value["edit_targets"][0]["line_hint"] = 1
            value["edit_targets"][0]["anchor"] = "missing_function_name"
            stale = RUNTIME.WorkerRuntime(
                root,
                value,
                {"python": sys.executable, "require_edit_targets": True},
                FakeClient([]),
            )
            with self.assertRaisesRegex(RUNTIME.PreflightBlocked, "anchor is absent"):
                stale.preflight()

    def test_repeated_duplicate_reads_stop_as_no_progress(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    *[
                        {"action": "READ_FILE", "arguments": {"path": "src/example.py"}}
                        for _ in range(3)
                    ],
                ]
            )
            report = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, client
            ).run()
            self.assertEqual(report["failure_reason"], "repeated_duplicate_reads")
            self.assertEqual(report["protocol_error_count"], 0)
            self.assertEqual(report["runtime_facts"]["duplicate_read_count"], 3)

    def test_large_file_read_points_to_symbol_search_and_later_range(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src" / "example.py").write_text(
                "\n".join(["# context"] * 300 + ["def target_endpoint(): pass"]) + "\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            first = runtime.read_file({"path": "src/example.py"})
            self.assertEqual(first["end_line"], 200)
            self.assertEqual(first["total_lines"], 301)
            self.assertEqual(first["unread_line_range"]["start_line"], 201)
            self.assertIn("SEARCH", first["navigation_hint"])
            result = runtime.search({"path": "src/example.py", "query": "target_endpoint"})
            self.assertEqual(result["results"][0]["line"], 301)
            later = runtime.read_file(
                {
                    "path": "src/example.py",
                    "start_line": 298,
                    "end_line": 301,
                }
            )
            self.assertIn("target_endpoint", later["content"])

    def test_replace_miss_returns_search_and_narrow_read_repair(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            digest = RUNTIME.SAFE_EDIT.sha256_bytes((root / "src" / "example.py").read_bytes())
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": digest,
                            "find": "def missing_target():\n",
                            "replace": "def fixed():\n",
                        },
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["No edit."],
                            "reason": "No replacement made",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            report = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, client
            ).run()
            feedback = json.loads(client.messages_seen[2][-1]["content"].split("\n", 1)[1])
            self.assertEqual(feedback["error_code"], "safe_replace_target_missing")
            self.assertEqual(feedback["edit_repair"]["suggested_action"]["action"], "SEARCH")
            search_args = feedback["edit_repair"]["suggested_action"]["arguments"]
            self.assertEqual(search_args["query"], "def missing_target():")
            self.assertEqual(search_args["mode"], "literal")
            self.assertIn("READ_FILE", feedback["edit_repair"]["instruction"])
            self.assertEqual(report["runtime_facts"]["duplicate_read_count"], 0)

    def test_replace_miss_shows_bounded_current_source_line(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            digest = RUNTIME.SAFE_EDIT.sha256_bytes((root / "src" / "example.py").read_bytes())
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": digest,
                            "find": "VALUE = 3\n",
                            "replace": "VALUE = 2\n",
                        },
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["No edit."],
                            "reason": "No replacement made",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client).run()
            feedback = json.loads(client.messages_seen[2][-1]["content"].split("\n", 1)[1])
            self.assertEqual(
                feedback["edit_repair"]["current_source_lines"],
                [{"line": 1, "text": "VALUE = 1"}],
            )
            self.assertEqual(feedback["edit_repair"]["max_find_chars_after_mismatch"], 300)

    def test_absent_function_claim_requires_symbol_search(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src" / "example.py").write_text(
                "\n".join(["# context"] * 300 + ["def target_endpoint(): pass"]) + "\n",
                encoding="utf-8",
            )
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Unable to locate target_endpoint endpoint."],
                            "reason": "Function not found in file",
                            "remaining_uncertainty": [],
                        },
                    },
                    {
                        "action": "SEARCH",
                        "arguments": {
                            "path": "src/example.py",
                            "query": "target_endpoint",
                        },
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Stopping for another reason."],
                            "reason": "No edit planned",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            report = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, client
            ).run()
            feedback = json.loads(client.messages_seen[2][-1]["content"].split("\n", 1)[1])
            self.assertIn("SEARCH", feedback["error"])
            found = json.loads(client.messages_seen[3][-1]["content"].split("\n", 1)[1])
            self.assertEqual(found["results"][0]["line"], 301)
            self.assertEqual(report["protocol_error_count"], 1)

    def test_truncated_json_gets_compact_retry_instruction(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = RawClient(
                [
                    '{"action":"SAFE_REPLACE","arguments":{"path":"src/example.py","find":"broken',
                    json.dumps(
                        {
                            "action": "FINISH_FAILED",
                            "arguments": {
                                "summary": ["Stopped."],
                                "reason": "No edit",
                                "remaining_uncertainty": [],
                            },
                        }
                    ),
                ]
            )
            report = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, client
            ).run()
            feedback = json.loads(client.messages_seen[1][-1]["content"].split("\n", 1)[1])
            self.assertEqual(feedback["error_code"], "malformed_model_json")
            self.assertIn("one short JSON action", feedback["json_repair"])
            self.assertEqual(report["protocol_error_count"], 1)

    def test_validate_type_error_returns_packet_specific_repair_shape(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["forbidden_orderings"] = ["Do not change unrelated behavior."]
            client = FakeClient(
                [
                    {
                        "action": "VALIDATE",
                        "arguments": {
                            "contract_check": {
                                "required_behavior_ids": ["behavior-value"],
                                "forbidden_orderings_absent": ["Do not change unrelated behavior."],
                            }
                        },
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Stopped for repair."],
                            "reason": "Needs implementation",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            report = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, client).run()
            self.assertEqual(report["protocol_error_count"], 1)
            feedback = json.loads(client.messages_seen[1][-1]["content"].split("\n", 1)[1])
            self.assertIn("must be boolean or null", feedback["error"])
            template = feedback["validate_repair"]["example"]["arguments"]["contract_check"]
            self.assertIs(template["forbidden_orderings_absent"], True)
            self.assertEqual(template["required_behavior_ids"], ["behavior-value"])

    def test_missing_observable_ids_get_one_shape_repair_without_validation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["limits"]["max_protocol_errors"] = 1
            value["acceptance_scenarios"] = [
                {
                    "id": "scenario-1",
                    "text": "The focused test asserts the result.",
                    "observables": {"protected_test_assertion": True},
                }
            ]
            client = FakeClient(
                [
                    {
                        "action": "VALIDATE",
                        "arguments": {
                            "contract_check": {
                                "required_behavior_ids": ["behavior-value"],
                                "observable_scenario_ids": [],
                                "unrelated_changes": [],
                            }
                        },
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Stopped for repair."],
                            "reason": "Needs implementation",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            report = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, client).run()
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["protocol_error_count"], 0)
            self.assertEqual(report["evidence_refs"]["validation_attempts"], [])
            feedback = json.loads(client.messages_seen[1][-1]["content"].split("\n", 1)[1])
            self.assertEqual(
                feedback["validate_repair"]["example"]["arguments"]["contract_check"][
                    "observable_scenario_ids"
                ],
                ["scenario-1"],
            )
            self.assertIn("No validation ran", feedback["one_shot_shape_repair"])

    def test_coder_allows_new_ranges_but_caps_reads_per_file_version(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            (root / "src" / "example.py").write_text(
                "\n".join(f"LINE_{index} = {index}" for index in range(1, 5)) + "\n",
                encoding="utf-8",
            )
            value = packet_v2()
            value["limits"]["max_reads_per_file_version"] = 2
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, FakeClient([]))
            runtime.read_file({"path": "src/example.py", "start_line": 1, "end_line": 1})
            runtime.read_file({"path": "src/example.py", "start_line": 2, "end_line": 2})
            with self.assertRaisesRegex(RUNTIME.WorkerError, "per-file-version limit"):
                runtime.read_file({"path": "src/example.py", "start_line": 3, "end_line": 3})

    def test_success_is_rejected_without_validation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient(
                [
                    {
                        "action": "FINISH_SUCCESS",
                        "arguments": {"summary": ["Done"], "remaining_uncertainty": []},
                    },
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {
                            "summary": ["Validation was required."],
                            "reason": "not validated",
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
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
            self.assertEqual(report["status"], "ready_for_review", report)
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
            source_preimage = next(item for item in preimages if item["path"] == "src/example.py")
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

    def test_validated_terminal_gate_rejects_then_finalizes(self) -> None:
        class TerminalDriftClient(AdaptiveSuccessClient):
            def complete(self, messages: list[dict[str, str]]) -> str:
                if self.step == 2:
                    self.step += 1
                    return json.dumps({"action": "VALIDATE", "arguments": {"phase": "final"}})
                if self.step == 3:
                    self.step += 1
                    return json.dumps(
                        {
                            "action": "SEARCH",
                            "arguments": {"path": "src/example.py", "query": "VALUE"},
                        }
                    )
                if self.step == 4:
                    self.step += 1
                    return json.dumps(
                        {
                            "action": "SAFE_REPLACE",
                            "arguments": {
                                "path": "src/example.py",
                                "expected_sha256": "0" * 64,
                                "find": "VALUE = 2\n",
                                "replace": "VALUE = 3\n",
                            },
                        }
                    )
                return super().complete(messages)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet(), {"python": sys.executable}, TerminalDriftClient()
            )

            def fake_command(argv: list[str]) -> dict:
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuites><testsuite tests="1" failures="0" errors="0" '
                            'skipped="0" /></testsuites>',
                            encoding="utf-8",
                        )
                return {"status": "passed", "exit_code": 0, "output": "ok", "argv": argv}

            with patch.object(runtime, "_run_command", side_effect=fake_command):
                report = runtime.run()
            self.assertEqual(report["status"], "ready_for_review", report)
            self.assertEqual((root / "src" / "example.py").read_text(), "VALUE = 2\n")
            events = (root / report["evidence_refs"]["run_archive"] / "events.jsonl").read_text(
                encoding="utf-8"
            )
            self.assertIn("validated_terminal_nudge_issued", events)
            self.assertIn("validated_terminal_runtime_finalized", events)

    def test_flat_and_multiple_actions_are_safely_normalized(self) -> None:
        parsed = RUNTIME.parse_action(
            '{"action":"SEARCH","query":"needle"}\n{"action":"READ_FILE","path":"greeting.py"}'
        )
        self.assertEqual(parsed["action"], "SEARCH")
        self.assertEqual(parsed["arguments"], {"query": "needle"})
        self.assertEqual(len(parsed["_warnings"]), 1)

    def test_non_json_trailing_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(RUNTIME.WorkerError, "non-JSON trailing"):
            RUNTIME.parse_action('{"action":"VALIDATE"}\nthen run tests')

    def test_lmstudio_client_explicitly_loads_missing_model_with_role_context(self) -> None:
        requests = []

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def fake_urlopen(request, timeout):
            requests.append((request.full_url, request.get_method(), timeout))
            if request.get_method() == "POST":
                self.assertEqual(
                    json.loads(request.data),
                    {"model": "meta/muse-glimmer", "context_length": 24576},
                )
                return FakeResponse(b'{"status":"loaded"}')
            loaded = len(requests) > 2
            instances = (
                [{"id": "meta/muse-glimmer", "config": {"context_length": 24576}}] if loaded else []
            )
            return FakeResponse(
                json.dumps(
                    {"models": [{"key": "meta/muse-glimmer", "loaded_instances": instances}]}
                ).encode()
            )

        client = RUNTIME.LMStudioClient(
            "http://localhost:12345/v1", "meta/muse-glimmer", context_length=24576
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            self.assertEqual(client.ensure_loaded()["status"], "loaded")
            self.assertEqual(client.ensure_loaded()["status"], "already_loaded")
        self.assertEqual([method for _, method, _ in requests], ["GET", "POST", "GET", "GET"])
        self.assertEqual(requests[1][2], 360)

    def test_lmstudio_client_model_readiness_failure_is_infrastructure(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:12345/v1", "meta/muse-glimmer")
        with patch.object(
            RUNTIME.urllib.request,
            "urlopen",
            side_effect=RUNTIME.urllib.error.URLError("unavailable"),
        ):
            with self.assertRaises(RUNTIME.PreflightBlocked) as raised:
                client.ensure_loaded()
        self.assertEqual(raised.exception.reason_code, "model_load_failed")

    def test_lmstudio_readiness_reuses_loaded_instance_with_distinct_id(self) -> None:
        """The native model key and loaded instance id are distinct fields."""

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        client = RUNTIME.LMStudioClient(
            "http://localhost:12345/v1", "meta/muse-glimmer", context_length=24576
        )
        calls = []
        inventory = {
            "models": [
                {
                    "key": client.model,
                    "loaded_instances": [
                        {"id": "muse-loaded-instance", "config": {"context_length": 24576}}
                    ],
                }
            ]
        }

        def urlopen(request, timeout):
            calls.append(request.get_method())
            if request.get_method() != "GET":
                raise AssertionError("already resident role must not be loaded again")
            return FakeResponse(json.dumps(inventory).encode())

        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=urlopen):
            self.assertEqual(client.ensure_loaded()["status"], "already_loaded")
        self.assertEqual(calls, ["GET"])

    def test_lmstudio_distinct_instance_id_keeps_context_floor(self) -> None:
        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        client = RUNTIME.LMStudioClient(
            "http://localhost:12345/v1", "meta/muse-glimmer", context_length=24576
        )
        inventory = {
            "models": [
                {
                    "key": client.model,
                    "loaded_instances": [
                        {"id": "muse-loaded-instance", "config": {"context_length": 8192}}
                    ],
                }
            ]
        }

        def urlopen(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            return FakeResponse(json.dumps(inventory).encode())

        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=urlopen):
            with self.assertRaises(RUNTIME.PreflightBlocked) as raised:
                client.ensure_loaded()
        self.assertEqual(raised.exception.reason_code, "model_context_too_small")

    def test_role_lease_then_readiness_does_not_reload_alias_instance(self) -> None:
        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        client = RUNTIME.LMStudioClient(
            "http://localhost:12345/v1", "meta/muse-glimmer", context_length=24576
        )
        config = {
            "single_model_residency": True,
            "explorer_model": "openai/gpt-oss-20b",
            "coder_model": "qwen/qwen3-coder-30b",
            "reviewer_model": client.model,
        }
        inventory = {
            "models": [
                {
                    "key": model,
                    "loaded_instances": [
                        {"id": "muse-loaded-instance", "config": {"context_length": 24576}}
                    ]
                    if model == client.model
                    else [],
                }
                for model in (config["explorer_model"], config["coder_model"], client.model)
            ]
        }
        calls = []

        def urlopen(request, timeout):
            method = request.get_method() if hasattr(request, "get_method") else "GET"
            calls.append(method)
            self.assertEqual(method, "GET")
            return FakeResponse(json.dumps(inventory).encode())

        with TemporaryDirectory() as directory:
            with patch.object(
                RUNTIME.MODEL_RESIDENCY.tempfile, "gettempdir", return_value=directory
            ):
                with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=urlopen):
                    with RUNTIME.MODEL_RESIDENCY.role_model_lease(client, config):
                        self.assertEqual(client.ensure_loaded()["status"], "already_loaded")
                self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(calls, ["GET", "GET", "GET", "GET"])

    def test_lmstudio_client_rejects_loaded_context_below_role_contract(self) -> None:
        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        client = RUNTIME.LMStudioClient(
            "http://localhost:12345/v1", "meta/muse-glimmer", context_length=24576
        )
        inventory = {
            "models": [
                {
                    "key": "meta/muse-glimmer",
                    "loaded_instances": [
                        {"id": "meta/muse-glimmer", "config": {"context_length": 8192}}
                    ],
                }
            ]
        }
        with patch.object(
            RUNTIME.urllib.request,
            "urlopen",
            return_value=FakeResponse(json.dumps(inventory).encode()),
        ):
            with self.assertRaises(RUNTIME.PreflightBlocked) as raised:
                client.ensure_loaded()
        self.assertEqual(raised.exception.reason_code, "model_context_too_small")

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
            return FakeResponse(
                json.dumps(
                    {
                        "choices": [
                            {"message": {"content": '{"action":"VALIDATE","arguments":{}}'}}
                        ],
                        "usage": {"prompt_tokens": 123},
                    }
                ).encode("utf-8")
            )

        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1", "coder", timeout=9, context_length=24576
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = client.complete([{"role": "user", "content": "act"}])

        self.assertEqual(result, '{"action":"VALIDATE","arguments":{}}')
        self.assertEqual(captured["timeout"], 9)
        self.assertEqual(captured["body"]["max_tokens"], 4096)
        self.assertEqual(captured["body"]["repeat_penalty"], 1.0)
        self.assertEqual(client.last_request_stats["reported_input_tokens"], 123)
        self.assertEqual(client.last_request_stats["context_length"], 24576)
        self.assertEqual(client.last_request_stats["reported_remaining_tokens"], 24576 - 123 - 4096)
        response_format = captured["body"]["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        schema = response_format["json_schema"]["schema"]
        self.assertEqual(schema["required"], ["action", "arguments"])
        self.assertIn("SAFE_REPLACE", schema["properties"]["action"]["enum"])
        client.action_schema = RUNTIME.repair_only_action_schema(
            client.action_schema, "SAFE_REPLACE"
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            client.complete([{"role": "user", "content": "repair now"}])
        narrowed = captured["body"]["response_format"]["json_schema"]["schema"]
        self.assertEqual(
            narrowed["properties"]["action"]["enum"],
            ["SAFE_REPLACE", "SAFE_REPLACE_LINE", "FINISH_BLOCKED", "REQUEST_CONTRACT_REVISION"],
        )
        self.assertIn("READ_FILE", RUNTIME.CODER_ACTION_SCHEMA["properties"]["action"]["enum"])
        with self.assertRaisesRegex(RUNTIME.WorkerError, "unsupported required repair"):
            RUNTIME.repair_only_action_schema(RUNTIME.CODER_ACTION_SCHEMA, "VALIDATE")

    def test_lmstudio_client_can_disable_structured_output_for_compatibility(self) -> None:
        captured = {}

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse(
                json.dumps(
                    {"choices": [{"message": {"content": '{"action":"VALIDATE","arguments":{}}'}}]}
                ).encode("utf-8")
            )

        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1", "coder", structured_output=False
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            client.complete([{"role": "user", "content": "act"}])

        self.assertNotIn("response_format", captured["body"])

    def test_lmstudio_client_normalizes_one_native_tool_call(self) -> None:
        captured = {}

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse(
                json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": "",
                                    "tool_calls": [
                                        {
                                            "type": "function",
                                            "function": {
                                                "name": "READ_FILE",
                                                "arguments": '{"path":"src/example.py"}',
                                            },
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                ).encode("utf-8")
            )

        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1",
            "reviewer",
            structured_output=False,
            native_tools=[{"type": "function", "function": {"name": "READ_FILE"}}],
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            action = client.complete([{"role": "user", "content": "act"}])
        self.assertEqual(
            json.loads(action),
            {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
        )
        self.assertNotIn("response_format", captured["body"])
        self.assertEqual(captured["body"]["tool_choice"], "auto")
        self.assertIs(captured["body"]["parallel_tool_calls"], False)
        self.assertEqual(client.last_request_stats["native_tool_call"], "READ_FILE")
        client.native_tool_choice = "required"
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            client.complete([{"role": "user", "content": "report now"}])
        self.assertEqual(captured["body"]["tool_choice"], "required")

    def test_native_schema_cost_blocks_oversized_request_before_http(self) -> None:
        tools = [{"type": "function", "function": {"name": "READ_FILE", "description": "x" * 5000}}]
        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1",
            "reviewer",
            native_tools=tools,
            context_length=1200,
            max_tokens=100,
            context_safety_margin=100,
        )
        with patch.object(RUNTIME.urllib.request, "urlopen") as send:
            with self.assertRaises(RUNTIME.ModelRequestError) as caught:
                client.complete([{"role": "user", "content": "small"}])
        send.assert_not_called()
        self.assertEqual(caught.exception.reason_code, "input_too_large")
        self.assertGreater(client.last_request_stats["native_schema_chars"], 5000)
        self.assertGreater(client.last_request_stats["estimated_input_tokens"], 1200)

    def test_native_parallel_response_still_fails_closed(self) -> None:
        call = {"type": "function", "function": {"name": "READ_FILE", "arguments": "{}"}}
        payload = {"choices": [{"message": {"tool_calls": [call, call]}}]}
        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1",
            "reviewer",
            native_tools=[call],
        )
        with patch.object(
            RUNTIME.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())
        ):
            with self.assertRaisesRegex(RUNTIME.WorkerError, "exactly one"):
                client.complete([{"role": "user", "content": "act"}])
        self.assertNotIn("native_tool_call", client.last_request_stats)

    def test_lmstudio_client_preserves_bounded_http_error_body(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "reviewer")
        error = RUNTIME.urllib.error.HTTPError(
            client.url,
            400,
            "Bad Request",
            None,
            io.BytesIO(b'{"error":"schema rejected"}'),
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=error):
            with self.assertRaisesRegex(
                RUNTIME.ModelRequestError,
                r'HTTP Error 400: Bad Request; response: \{"error":"schema rejected"\}',
            ) as raised:
                client.complete([{"role": "user", "content": "act"}])
        self.assertEqual(raised.exception.reason_code, "http_4xx")
        self.assertEqual(client.last_request_stats["provider_status_code"], 400)
        self.assertEqual(
            client.last_request_stats["provider_response_body"], '{"error":"schema rejected"}'
        )

    def test_lmstudio_client_retries_role_alternation_400_with_merged_user_turn(self) -> None:
        captured: list[dict] = []

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def fake_urlopen(request, timeout):
            captured.append(json.loads(request.data.decode("utf-8")))
            if len(captured) == 1:
                raise RUNTIME.urllib.error.HTTPError(
                    request.full_url,
                    400,
                    "Bad Request",
                    None,
                    io.BytesIO(b"conversation roles must alternate user and assistant roles"),
                )
            return FakeResponse(
                json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": '{"action":"READ_FILE","arguments":{"path":"src/example.py"}}'
                                }
                            }
                        ]
                    }
                ).encode("utf-8")
            )

        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "candidate")
        messages = [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "IMPLEMENTATION_PACKET\ncontract"},
            {"role": "user", "content": "REPOSITORY_HINTS\npaths"},
        ]
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = client.complete(messages)
        self.assertIn('"action":"READ_FILE"', result)
        self.assertEqual([item["role"] for item in captured[1]["messages"]], ["system", "user"])
        self.assertIn("IMPLEMENTATION_PACKET\ncontract", captured[1]["messages"][1]["content"])
        self.assertIn("REPOSITORY_HINTS\npaths", captured[1]["messages"][1]["content"])
        self.assertEqual(client.last_request_stats["role_alternation_retry"]["result"], "succeeded")

    def test_lmstudio_client_rejects_oversized_input_before_send(self) -> None:
        client = RUNTIME.LMStudioClient(
            "http://localhost:1234/v1",
            "coder",
            max_tokens=20,
            context_length=100,
            context_safety_margin=10,
        )
        with patch.object(RUNTIME.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(RUNTIME.ModelRequestError) as raised:
                client.complete(
                    [
                        {"role": "system", "content": "SYSTEM\n" + "x" * 160},
                        {"role": "user", "content": "IMPLEMENTATION_PACKET\n" + "y" * 160},
                    ]
                )
        self.assertEqual(raised.exception.reason_code, "input_too_large")
        urlopen.assert_not_called()
        stats = raised.exception.diagnostics
        self.assertEqual(stats["available_input_tokens"], 70)
        self.assertEqual(stats["rejection_reason"], "input_too_large")
        self.assertEqual(len(stats["largest_prompt_sections"]), 2)

    def test_lmstudio_client_classifies_transport_timeout(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "reviewer")
        with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(RUNTIME.ModelRequestError) as raised:
                client.complete([{"role": "user", "content": "act"}])
        self.assertEqual(raised.exception.reason_code, "model_request_timeout")

    def test_lmstudio_client_rejects_nonempty_truncated_actions(self) -> None:
        for message in (
            {"content": '{"action":"FINISH_SUCCESS","arguments":{}}'},
            {
                "tool_calls": [
                    {
                        "function": {
                            "name": "SAFE_CREATE",
                            "arguments": {"path": "x.py", "content": "pass"},
                        }
                    }
                ]
            },
        ):
            client = RUNTIME.LMStudioClient(
                "http://localhost:1234/v1",
                "coder",
                native_tools=[{"type": "function", "function": {"name": "SAFE_CREATE"}}],
            )
            response = io.BytesIO(
                json.dumps(
                    {
                        "choices": [{"finish_reason": "length", "message": message}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 2048},
                    }
                ).encode()
            )
            with (
                self.subTest(message=message),
                patch.object(RUNTIME.urllib.request, "urlopen", return_value=response),
            ):
                with self.assertRaises(RUNTIME.ModelRequestError) as raised:
                    client.complete([{"role": "user", "content": "task"}])
                self.assertEqual(raised.exception.reason_code, "output_token_limit")
                self.assertEqual(client.last_request_stats["finish_reason"], "length")
                self.assertEqual(
                    client.last_request_stats["response_usage"]["completion_tokens"], 2048
                )
                self.assertNotIn("native_tool_call", client.last_request_stats)

    def test_lmstudio_client_classifies_output_token_limit(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "coder")
        response = io.BytesIO(
            json.dumps(
                {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}
            ).encode("utf-8")
        )
        with patch.object(RUNTIME.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(RUNTIME.ModelRequestError) as raised:
                client.complete([{"role": "user", "content": "act"}])
        self.assertEqual(raised.exception.reason_code, "output_token_limit")
        self.assertEqual(raised.exception.diagnostics["provider_finish_reason"], "length")

    def test_structured_probe_uses_verified_plain_json_fallback_on_http_400(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "reviewer")
        with patch.object(
            client, "complete", side_effect=[RUNTIME.WorkerError("HTTP Error 400"), "{}"]
        ) as complete:
            mode = client.probe_structured_output()
        self.assertEqual(mode, "unstructured_fallback")
        self.assertFalse(client.structured_output)
        self.assertEqual(complete.call_count, 2)

    def test_structured_probe_uses_plain_json_fallback_on_empty_response(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "reviewer")
        with patch.object(
            client,
            "complete",
            side_effect=[
                RUNTIME.WorkerError("LM Studio returned an empty assistant message"),
                "{}",
            ],
        ) as complete:
            mode = client.probe_structured_output()
        self.assertEqual(mode, "unstructured_fallback")
        self.assertFalse(client.structured_output)
        self.assertEqual(complete.call_count, 2)

    def test_structured_probe_fails_closed_if_plain_json_also_rejected(self) -> None:
        client = RUNTIME.LMStudioClient("http://localhost:1234/v1", "reviewer")
        with patch.object(
            client,
            "complete",
            side_effect=[
                RUNTIME.WorkerError("HTTP Error 400"),
                RUNTIME.WorkerError("HTTP Error 400"),
            ],
        ):
            with self.assertRaisesRegex(RUNTIME.PreflightBlocked, "failed both"):
                client.probe_structured_output()
        self.assertTrue(client.structured_output)

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
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            with self.assertRaisesRegex(RUNTIME.WorkerError, "outside scope.read"):
                runtime.read_file({"path": "outside.py"})

    def test_packet_preflight_names_exact_duplicate_and_missing_read_scope(self) -> None:
        duplicate = packet_v2()
        duplicate["edit_targets"] = [
            {"path": "src/example.py", "anchor": "VALUE"},
            {"path": "src/example.py", "anchor": "VALUE ="},
        ]
        with self.assertRaisesRegex(RUNTIME.WorkerError, "edit_targets\\[2\\].*duplicates"):
            RUNTIME.validate_packet(duplicate)
        missing = packet_v2()
        missing["scope"]["read"] = ["src"]
        with self.assertRaisesRegex(
            RUNTIME.WorkerError, "add this exact file to scope.read or scope.readonly"
        ):
            RUNTIME.validate_packet(missing)

    def test_prevalidation_search_read_loop_stops_without_new_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["limits"] = {
                "max_model_turns": 20,
                "max_prevalidation_no_evidence_streak": 5,
            }
            client = FakeClient(
                [{"action": "READ_FILE", "arguments": {"path": "src/example.py"}}]
                + [
                    {
                        "action": "SEARCH",
                        "arguments": {"path": "src/example.py", "query": "VALUE"},
                    }
                    for _ in range(12)
                ]
            )
            report = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, client).run()
            self.assertEqual(report["failure_reason"], "no_new_evidence_before_edit")
            self.assertEqual(report["runtime_facts"]["prevalidation_no_evidence_streak"], 5)

    def test_packet_preserves_order_and_observable_contracts(self) -> None:
        value = packet_v2()
        value["required_order"] = ["run handler", "recheck lease", "commit"]
        value["forbidden_orderings"] = ["recheck lease before handler"]
        value["acceptance_scenarios"] = [
            {
                "id": "stale-lease",
                "text": "A stale lease rolls back without finalization.",
                "observables": {"rollback_calls": 1, "commit_calls": 0},
            }
        ]
        normalized = RUNTIME.validate_packet(value)
        self.assertTrue(normalized["contract_check_required"])
        self.assertEqual(normalized["required_order"][1], "recheck lease")
        self.assertEqual(
            normalized["acceptance_scenarios"][0]["observables"]["commit_calls"],
            0,
        )

    def test_coder_gets_scoped_navigation_not_stale_source(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src" / "example.py"
            digest = RUNTIME.SAFE_EDIT.sha256_bytes(source.read_bytes())
            cache = RUNTIME.EVIDENCE_CACHE.EvidenceCache(root)
            cache.store(
                "Locate value.",
                RUNTIME.EVIDENCE_CACHE.repository_fingerprint(root),
                {
                    "status": "success",
                    "task_id": "test-1",
                    "task": "Locate value.",
                    "relevant_files": [{"path": "src/example.py", "reason": "Defines VALUE."}],
                    "observed_hashes": {"src/example.py": digest},
                },
            )
            client = FakeClient(
                [
                    {
                        "action": "FINISH_FAILED",
                        "arguments": {"reason": "No edit requested", "summary": []},
                    }
                ]
            )
            RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client).run()
            self.assertTrue(
                any(
                    message["content"].startswith("REPOSITORY_HINTS\n")
                    for message in client.messages_seen[0]
                )
            )
            source.write_text("VALUE = 9\n", encoding="utf-8")
            self.assertEqual(cache.navigation_hints(readable=["src"], forbidden=[]), [])

    def test_supplemental_tests_must_be_writable_and_focused(self) -> None:
        value = packet_v2()
        value["supplemental_tests"] = ["tests/test_example.py"]
        with self.assertRaisesRegex(RUNTIME.WorkerError, "not writable"):
            RUNTIME.validate_packet(value)
        value["scope"]["modify"].append("tests/test_example.py")
        normalized = RUNTIME.validate_packet(value)
        self.assertEqual(normalized["supplemental_tests"], ["tests/test_example.py"])
        value["focused_tests"] = ["tests/test_other.py"]
        with self.assertRaisesRegex(RUNTIME.WorkerError, "absent from focused_tests"):
            RUNTIME.validate_packet(value)

    def test_example_packet_models_multifile_unit_and_protected_tests(self) -> None:
        example = json.loads((MODULE_PATH.parent / "example-packet.json").read_text())
        normalized = RUNTIME.validate_packet(example)
        self.assertEqual(len(normalized["scope"]["modify"]), 2)
        self.assertEqual(normalized["supplemental_tests"], ["tests/test_example_supplement.py"])
        self.assertIn("tests/test_example.py", normalized["scope"]["readonly"])

    def test_one_unit_can_edit_two_sources_and_supplemental_test(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "__init__.py").write_text("", encoding="utf-8")
            source = {
                "src/logic.py": "def increment(value):\n    return value\n",
                "src/api.py": "from src.logic import increment\n\ndef next_value(value):\n    return value\n",
            }
            changed = {
                "src/logic.py": "def increment(value):\n    return value + 1\n",
                "src/api.py": "from src.logic import increment\n\ndef next_value(value):\n    return increment(value)\n",
                "tests/test_supplement.py": (
                    "from src.api import next_value\n\n"
                    "def test_negative_boundary():\n    assert next_value(-1) == 0\n"
                ),
            }
            for path, content in source.items():
                (root / path).write_text(content, encoding="utf-8")
            (root / "tests" / "test_contract.py").write_text(
                "from src.api import next_value\n\n"
                "def test_public_result():\n    assert next_value(2) == 3\n",
                encoding="utf-8",
            )
            value = packet_v2()
            value["scope"] = {
                "read": ["src", "tests"],
                "readonly": ["tests/test_contract.py"],
                "modify": list(source),
                "create": ["tests/test_supplement.py"],
                "forbidden": [],
            }
            value["focused_tests"] = ["tests/test_contract.py", "tests/test_supplement.py"]
            value["supplemental_tests"] = ["tests/test_supplement.py"]
            value["implementation_guidance"] = [
                "Prefer a shared helper, but another correct approach is allowed."
            ]
            value["edit_targets"] = [
                {"path": path, "anchor": source[path].splitlines()[0]} for path in source
            ]
            value["limits"] = {"max_model_turns": 12}
            actions = (
                [
                    {
                        "action": "SAFE_CREATE",
                        "arguments": {
                            "path": "tests/test_supplement.py",
                            "content": changed["tests/test_supplement.py"],
                        },
                    },
                    {"action": "VALIDATE", "arguments": {}},
                ]
                + [{"action": "READ_FILE", "arguments": {"path": path}} for path in source]
                + [
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": path,
                            "expected_sha256": RUNTIME.SAFE_EDIT.sha256_bytes(
                                (root / path).read_bytes()
                            ),
                            "find": source[path],
                            "replace": changed[path],
                        },
                    }
                    for path in source
                ]
                + [
                    {"action": "VALIDATE", "arguments": {}},
                    {
                        "action": "FINISH_SUCCESS",
                        "arguments": {
                            "summary": ["Implemented and tested the unit."],
                            "remaining_uncertainty": [],
                        },
                    },
                ]
            )
            report = RUNTIME.WorkerRuntime(
                root,
                value,
                {"python": sys.executable, "require_edit_targets": True},
                FakeClient(actions),
            ).run()
            self.assertEqual(report["status"], "ready_for_review", report)
            self.assertEqual(report["repair_count"], 1)
            self.assertEqual(len(report["evidence_refs"]["validation_attempts"]), 2)
            self.assertEqual(report["validation"]["focused_tests"]["junit"]["executed"], 2)
            self.assertEqual(
                {item["path"] for item in report["changed_files"]},
                {*source, "tests/test_supplement.py"},
            )
            self.assertIn(
                "assert next_value(2) == 3", (root / "tests/test_contract.py").read_text()
            )

    def test_contract_revision_requires_real_evidence_and_routes_to_primary(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["required_behavior"].append(
                {"id": "behavior-preserve", "text": "VALUE remains 1"}
            )
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, FakeClient([]))
            action = {
                "action": "REQUEST_CONTRACT_REVISION",
                "arguments": {
                    "issue_type": "contract_conflict",
                    "reason": "The two required values contradict each other.",
                    "contract_ids": ["behavior-value", "behavior-preserve"],
                    "source_evidence": [
                        {"path": "src/example.py", "line": 1, "quote": "VALUE = 1"}
                    ],
                    "proposed_next_step": "Primary must choose the intended value.",
                },
            }
            with self.assertRaisesRegex(RUNTIME.WorkerError, "line was not read"):
                runtime.execute(action)
            runtime.read_file({"path": "src/example.py"})
            _observation, report = runtime.execute(action)
            assert report is not None
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["blocked"]["reason_code"], "contract_revision_requested")
            self.assertEqual(report["next_action_required"], "primary_contract_decision")
            self.assertEqual(report["blocked"]["source_evidence"][0]["line"], 1)
            action["arguments"]["source_evidence"][0]["quote"] = "VALUE = 2"
            with self.assertRaisesRegex(RUNTIME.WorkerError, "quote does not match"):
                runtime.execute(action)
            with self.assertRaisesRegex(RUNTIME.WorkerError, "Use REQUEST_CONTRACT_REVISION"):
                runtime.execute(
                    {
                        "action": "FINISH_BLOCKED",
                        "arguments": {
                            "reason_code": "contract_conflict",
                            "reason": "Bypass attempt",
                        },
                    }
                )

    def test_contract_revision_needs_validation_or_scope_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            base = {
                "reason": "The observed test conflicts with the intended result.",
                "proposed_next_step": "Primary should inspect the test assertion.",
            }
            with self.assertRaisesRegex(RUNTIME.WorkerError, "requires validation evidence"):
                runtime.contract_revision_report({**base, "issue_type": "stale_test_suspected"})
            with self.assertRaisesRegex(RUNTIME.WorkerError, "requires requested_scope"):
                runtime.contract_revision_report({**base, "issue_type": "scope_gap"})
            report = runtime.contract_revision_report(
                {
                    **base,
                    "issue_type": "scope_gap",
                    "requested_scope": {"read": ["src/needed.py"]},
                }
            )
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["blocked"]["requested_scope"]["read"], ["src/needed.py"])

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

    def test_diff_whitespace_preparation_is_opt_in_and_requires_trusted_profile(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {}, FakeClient([]))
            runtime.changed["src/example.py"] = {"operation": "modified"}
            issue = {"code": "introduced_trailing_whitespace", "path": "src/example.py"}
            command = {
                "id": "ruff-format",
                "argv": ["{python}", "-m", "ruff", "format", "--check", "src"],
            }
            profile = {"commands": [command]}

            def eligible(issues, selected):
                return runtime._diff_whitespace_autoformat_eligible(
                    issues, selected, Path(sys.executable)
                )

            self.assertFalse(eligible([issue], profile))
            runtime.config["autoformat_on_diff_whitespace"] = "true"
            self.assertFalse(eligible([issue], profile))
            runtime.config["autoformat_on_diff_whitespace"] = True
            self.assertTrue(eligible([issue], profile))
            self.assertFalse(eligible([], profile))
            self.assertFalse(eligible([issue], {"commands": []}))
            self.assertFalse(eligible([issue], {"commands": [{**command, "id": "custom"}]}))
            self.assertFalse(eligible([issue], {"commands": [{**command, "argv": ["ruff"]}]}))
            self.assertFalse(eligible([{**issue, "path": "tests/test_example.py"}], profile))
            self.assertFalse(
                eligible([{**issue, "code": "introduced_unreachable_duplicate_raise"}], profile)
            )
            runtime.autoformat_used = True
            self.assertFalse(eligible([issue], profile))

    def test_diff_whitespace_preparation_revalidates_and_never_hides_failed_tests(self):
        for outcome in ("pass", "fail", "no-change", "unexpected-change"):
            with self.subTest(outcome=outcome), TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_tree(root)
                config = {
                    "autoformat_on_diff_whitespace": True,
                    "validation_profiles": {
                        "python-focused": {
                            "python": sys.executable,
                            "commands": [
                                {
                                    "id": "ruff-format",
                                    "argv": [
                                        "{python}",
                                        "-m",
                                        "ruff",
                                        "format",
                                        "--check",
                                        "src",
                                        "tests",
                                    ],
                                }
                            ],
                        }
                    },
                }
                runtime = RUNTIME.WorkerRuntime(root, packet_v2(), config, FakeClient([]))
                runtime.write_lock.acquire()
                target = root / "src/example.py"
                protected = root / "tests/test_example.py"
                before = protected.read_bytes()
                calls = []

                def command(argv):
                    calls.append(argv)
                    if argv[1:4] == ["-m", "ruff", "format"] and "--check" not in argv:
                        self.assertEqual(argv[4:], ["src/example.py"])
                        if outcome != "no-change":
                            target.write_text("VALUE = 2\n", encoding="utf-8")
                        if outcome == "unexpected-change":
                            protected.write_text("# changed protected input\n", encoding="utf-8")
                    junit = next((a for a in argv if a.startswith("--junitxml=")), None)
                    failed = outcome == "fail" and junit is not None
                    if junit:
                        Path(junit.split("=", 1)[1]).write_text(
                            '<testsuites><testsuite tests="1" failures="'
                            + str(int(failed))
                            + '" errors="0" skipped="0"><testcase name="boundary">'
                            + ('<failure message="semantic mismatch"/>' if failed else "")
                            + "</testcase></testsuite></testsuites>",
                            encoding="utf-8",
                        )
                    return {
                        "status": "failed" if failed else "passed",
                        "exit_code": int(failed),
                        "output": "semantic mismatch" if failed else "ok",
                        "argv": argv,
                    }

                try:
                    runtime._prepare_run_archive()
                    observed = runtime.read_file({"path": "src/example.py"})
                    edit = runtime.safe_replace(
                        {
                            "path": "src/example.py",
                            "expected_sha256": observed["sha256"],
                            "find": "VALUE = 1\n",
                            "replace": "VALUE = 2  \n",
                        }
                    )
                    self.assertIn("VALIDATE", edit["next_step"])
                    with patch.object(runtime, "_run_command", side_effect=command):
                        if outcome == "unexpected-change":
                            with self.assertRaises(RUNTIME.PolicyViolation):
                                runtime.validate({"phase": "final"})
                            self.assertFalse(runtime._validated_terminal_state())
                            continue
                        result = runtime.validate({"phase": "final"})
                    self.assertEqual(result["status"], "passed" if outcome == "pass" else "failed")
                    self.assertEqual(runtime._validated_terminal_state(), outcome == "pass")
                    first = json.loads((root / runtime.validation_refs[0]).read_text())
                    self.assertEqual(first["validation"]["quality_gate"]["stage"], "diff_quality")
                    self.assertEqual(first["phase"], "check")
                    self.assertEqual(
                        len(runtime.validation_refs), 1 if outcome == "no-change" else 2
                    )
                    self.assertEqual(protected.read_bytes(), before)
                    self.assertEqual(
                        sum(
                            a[1:4] == ["-m", "ruff", "format"] and "--check" not in a for a in calls
                        ),
                        1,
                    )
                    if outcome != "no-change":
                        self.assertTrue(
                            any(any(a.startswith("--junitxml=") for a in argv) for argv in calls)
                        )
                        self.assertEqual(runtime.edit_revision, 2)
                finally:
                    runtime.close()

    def test_real_formatter_preserves_significant_string_whitespace_and_gate(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {
                    "autoformat_on_diff_whitespace": True,
                    "validation_profiles": {
                        "python-focused": {
                            "python": sys.executable,
                            "commands": [
                                {
                                    "id": "ruff-format",
                                    "argv": ["{python}", "-m", "ruff", "format", "--check", "src"],
                                }
                            ],
                        }
                    },
                },
                FakeClient([]),
            )
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                observed = runtime.read_file({"path": "src/example.py"})
                runtime.safe_replace(
                    {
                        "path": "src/example.py",
                        "expected_sha256": observed["sha256"],
                        "find": "VALUE = 1\n",
                        "replace": 'VALUE = """first  \nsecond"""\n',
                    }
                )
                result = runtime.validate({})
                self.assertEqual(result["status"], "failed")
                self.assertIn("first  \nsecond", (root / "src/example.py").read_text())
                self.assertTrue(runtime.autoformat_used)
                self.assertFalse(runtime._validated_terminal_state())
            finally:
                runtime.close()

    def test_diff_quality_gate_blocks_new_duplicate_unreachable_raise(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src" / "example.py"
            source.write_text(
                "def check():\n    raise ValueError('bad')\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            source.write_text(
                "def check():\n    raise ValueError('bad')\n    raise ValueError('bad')\n",
                encoding="utf-8",
            )
            issues = runtime._introduced_text_quality_issues()
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["code"], "introduced_unreachable_duplicate_raise")
            self.assertEqual(issues[0]["line"], 3)

    def test_diff_quality_gate_preserves_preexisting_duplicate_raise(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            source = root / "src" / "example.py"
            source.write_text(
                "def check():\n    raise ValueError('bad')\n    raise ValueError('bad')\n",
                encoding="utf-8",
            )
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            source.write_text(
                "VALUE = 2\ndef check():\n    raise ValueError('bad')\n    raise ValueError('bad')\n",
                encoding="utf-8",
            )
            self.assertEqual(runtime._introduced_text_quality_issues(), [])

    def test_inherited_rework_packet_preserves_parent_contract(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parent = packet_v2()
            parent_path = root / ".agent" / "tasks" / "test-1" / "runs" / "run-1" / "packet.json"
            parent_path.parent.mkdir(parents=True)
            parent_path.write_text(json.dumps(parent), encoding="utf-8")
            parent_path.with_name("completed.json").write_text(
                json.dumps({"status": "ready_for_review"}), encoding="utf-8"
            )
            parent_path.with_name("handoff.json").write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "failure_reason": "Focused test failed.",
                        "failure_signature": "coder|failed|validation_failed",
                        "changed_files": [{"path": "src/example.py"}],
                        "protocol_error_details": [{"error_code": "safe_replace_target_missing"}],
                    }
                ),
                encoding="utf-8",
            )
            parent_path.with_name("validation.json").write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "focused_tests": {
                            "status": "failed",
                            "diagnostic": {
                                "failed_test_ids": ["tests/test_example.py::test_value"],
                            },
                        },
                        "configured_checks": [],
                    }
                ),
                encoding="utf-8",
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
            trace = resolved["_inheritance"]["rework_traceback"]
            self.assertEqual(trace["changed_paths"], ["src/example.py"])
            self.assertEqual(trace["failed_test_ids"], ["tests/test_example.py::test_value"])
            self.assertEqual(trace["last_protocol_error"], "safe_replace_target_missing")
            self.assertEqual(resolved["_inheritance"]["parent_input_state"]["status"], "unknown")
            self.make_tree(root)
            RUNTIME.RUN_STATE.write_json_once(
                parent_path.with_name("post-state.json"),
                {"validation_inputs": RUNTIME.RUN_STATE.facts_for_paths(root, ["src/example.py"])},
            )
            unchanged = RUNTIME.resolve_inherited_packet(root, child)
            self.assertEqual(unchanged["_inheritance"]["parent_input_state"]["status"], "unchanged")
            (root / "src/example.py").write_text("VALUE = 9\n", encoding="utf-8")
            drifted = RUNTIME.resolve_inherited_packet(root, child)
            self.assertEqual(
                drifted["_inheritance"]["parent_input_state"]["drifted_paths"], ["src/example.py"]
            )
            self.assertFalse(drifted["_inheritance"]["parent_input_state"]["validation_reusable"])

    def test_contract_check_and_changed_test_quality_gate(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["required_order"] = ["edit", "validate"]
            value["forbidden_orderings"] = ["validate before edit"]
            value["acceptance_scenarios"] = [
                {
                    "id": "observable-test",
                    "text": "The test asserts the result.",
                    "observables": {"assertions": 1},
                }
            ]
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, FakeClient([]))
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
                    runtime.safe_replace(
                        {
                            "path": "src/example.py",
                            "expected_sha256": digest,
                            "find": "VALUE = 999\n",
                            "replace": "VALUE = 2\n",
                        }
                    )
            finally:
                runtime.close()
            self.assertEqual(runtime.repairs, 0)
            self.assertTrue(runtime.pending_failed_validation)

    def test_successful_repair_edit_is_marked_for_turn_reserve(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            runtime.write_lock.acquire()
            try:
                runtime.edit_revision = 1
                runtime.pending_failed_validation = True
                _, digest = runtime.editor.read_bytes("src/example.py")
                observation = runtime.safe_replace(
                    {
                        "path": "src/example.py",
                        "expected_sha256": digest,
                        "find": "VALUE = 1\n",
                        "replace": "VALUE = 2\n",
                    }
                )
            finally:
                runtime.close()
            self.assertTrue(observation["repair_edit"])
            self.assertEqual(runtime.repairs, 1)
            self.assertFalse(runtime.pending_failed_validation)

    def test_terminal_state_requires_current_successful_validation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            self.assertFalse(runtime._validated_terminal_state())
            runtime.validation = RUNTIME.ValidationResult(
                "passed", {"status": "passed"}, {"status": "passed"}
            )
            runtime.edit_revision = 2
            runtime.validated_revision = 2
            runtime.validated_input_facts = runtime._validation_facts()
            self.assertFalse(runtime._validated_terminal_state())
            runtime.validation_phase = "final"
            self.assertTrue(runtime._validated_terminal_state())
            runtime.edit_revision = 3
            self.assertFalse(runtime._validated_terminal_state())

    def test_compact_repair_payload_exposes_contract_and_noop_warning(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            runtime.noop_repair_attempts = 1
            payload = runtime._compact_repair_payload(
                {
                    "required_next_action": "SAFE_REPLACE",
                    "candidate_edit_paths": ["src/example.py"],
                }
            )
            self.assertEqual(payload["previous_noop_repair_attempts"], 1)
            self.assertEqual(payload["required_behavior"][0]["id"], "behavior-value")
            self.assertIn("must differ", payload["prohibited_attempts"][1])

    def test_compact_repair_retains_bounded_observed_failure_not_inferred_answer(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            message = "AssertionError: observed 7 != expected 2 " + "x" * 3000
            runtime.validation = RUNTIME.ValidationResult(
                "failed",
                {},
                {
                    "diagnostic": {
                        "failures": [
                            {
                                "test": "test_example",
                                "message": message,
                                "location": "tests/test_example.py:1: AssertionError",
                            },
                            {
                                "test": "outside",
                                "message": "must not leak",
                                "location": "outside.py:1: AssertionError",
                            },
                        ]
                    }
                },
            )
            payload = runtime._compact_repair_payload(
                {"required_next_action": "SAFE_REPLACE", "candidate_edit_paths": ["src/example.py"]}
            )
            self.assertEqual(len(payload["test_evidence"]), 1)
            evidence = payload["test_evidence"][0]
            self.assertEqual(evidence["failure_message"], message[:2000])
            self.assertNotIn("expected", {key for key in evidence if key != "failure_message"})
            self.assertIn("observed validation failure", payload["instruction"])
            runtime.close()

    def test_compact_repair_test_evidence_accepts_node_ids_without_scope_expansion(self) -> None:
        selectors = (
            "tests/test_example.py",
            "tests/test_example.py::test_value",
            "tests/test_example.py::TestValue::test_value[param::value]",
            "tests\\test_example.py::test_value[param]",
        )
        for selector in selectors:
            with self.subTest(selector=selector), TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_tree(root)
                packet = packet_v2()
                packet["focused_tests"] = [selector]
                runtime = RUNTIME.WorkerRuntime(
                    root, packet, {"python": sys.executable}, FakeClient([])
                )
                before = (root / "tests/test_example.py").read_bytes()
                runtime.validation = RUNTIME.ValidationResult(
                    "failed",
                    {},
                    {
                        "diagnostic": {
                            "failures": [
                                {
                                    "test": "test_value",
                                    "message": "AssertionError: observed mismatch",
                                    "location": "tests\\test_example.py:1: AssertionError",
                                },
                                {
                                    "test": "unfocused",
                                    "message": "must not leak",
                                    "location": "outside.py:1: AssertionError",
                                },
                            ]
                        }
                    },
                )
                payload = runtime._compact_repair_payload(
                    {
                        "required_next_action": "SAFE_REPLACE",
                        "candidate_edit_paths": ["src/example.py"],
                    }
                )
                self.assertEqual(len(payload["test_evidence"]), 1)
                evidence = payload["test_evidence"][0]
                self.assertEqual(evidence["path"], "tests/test_example.py")
                self.assertIn("1:", evidence["content"])
                self.assertEqual((root / "tests/test_example.py").read_bytes(), before)
                with patch.object(
                    runtime,
                    "_assert_read_allowed",
                    side_effect=RUNTIME.WorkerError("blocked read"),
                ):
                    blocked = runtime._compact_repair_payload(
                        {
                            "candidate_edit_paths": ["src/example.py"],
                        }
                    )
                self.assertEqual(blocked["test_evidence"], [])
                runtime.close()

    def test_repair_context_restores_only_unchanged_previously_read_lines(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            first = runtime.read_file({"path": "src/example.py"})
            duplicate = runtime.read_file({"path": "src/example.py"})
            self.assertEqual(duplicate["status"], "already_read")
            restored = runtime._restore_observed_read(duplicate)
            self.assertEqual(restored["path"], "src/example.py")
            self.assertIn("VALUE = 1", restored["content"])
            self.assertEqual(restored["new_evidence_count"], 0)

            source = root / "src" / "example.py"
            source.write_text("VALUE = 2\n", encoding="utf-8")
            self.assertIsNone(runtime._restore_observed_read(duplicate))
            self.assertIsNone(runtime._restore_observed_read(first))

    def test_identical_read_replays_once_after_context_trim(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            arguments = {"path": "src/example.py"}
            runtime.read_file(arguments)
            self.assertEqual(runtime.read_file(arguments)["status"], "already_read")
            runtime._trim_messages([{"role": "user", "content": str(index)} for index in range(13)])
            restored = runtime.read_file(arguments)
            self.assertEqual(restored["status"], "replayed")
            self.assertEqual(restored["new_evidence_count"], 0)
            self.assertIn("VALUE = 1", restored["content"])
            self.assertEqual(runtime.read_file(arguments)["status"], "already_read")

    def test_budgeted_history_retains_early_evidence_until_input_budget(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient([])
            client.context_length = 24576
            client.max_tokens = 2048
            client.context_safety_margin = 1024
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {"python": sys.executable, "coder_context_retention": "budgeted"},
                client,
            )
            messages = [{"role": "user", "content": str(index)} for index in range(22)]
            self.assertEqual(runtime._trim_messages(messages), messages)
            self.assertFalse(runtime.context_trimmed)
            large = [{"role": "user", "content": str(index) + "x" * 12000} for index in range(22)]
            trimmed = runtime._trim_messages(large)
            self.assertEqual(trimmed[:2], large[:2])
            self.assertEqual(trimmed[-10:], large[-10:])
            self.assertTrue(runtime.context_trimmed)
            self.assertEqual(len(large), 22)
            self.assertLess(len(trimmed), len(large))
            many = messages * 4
            capped = runtime._trim_messages(many)
            self.assertLessEqual(len(capped), 64)
            self.assertEqual(capped[:2], many[:2])
            self.assertEqual(capped[-10:], many[-10:])

    def test_latest_repair_focus_preserves_source_observations_and_packet(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient([])
            client.context_length = 24576
            client.max_tokens = 4096
            client.context_safety_margin = 1024
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {
                    "python": sys.executable,
                    "coder_context_retention": "budgeted",
                    "coder_repair_focus_retention": "latest",
                },
                client,
            )
            messages = [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "packet"},
                {"role": "assistant", "content": "READ_FILE tests"},
                {"role": "user", "content": "OBSERVATION protected assertions"},
                {
                    "role": "assistant",
                    "content": json.dumps({"action": "VALIDATE", "arguments": {}}),
                },
                {"role": "user", "content": "REPAIR_REQUIRED\nold"},
                {"role": "assistant", "content": "SAFE_REPLACE"},
                {"role": "user", "content": "OBSERVATION current hash"},
                {
                    "role": "assistant",
                    "content": json.dumps({"action": "VALIDATE", "arguments": {}}),
                },
                {"role": "user", "content": "REPAIR_REQUIRED\nnew"},
            ]
            retained = runtime._trim_messages(messages)
            self.assertEqual(retained, messages[:4] + messages[6:])
            self.assertEqual(len(messages), 10)
            self.assertTrue(runtime.context_trimmed)
            alternate = list(messages)
            alternate[4] = {
                "role": "assistant",
                "content": json.dumps(
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}}
                ),
            }
            self.assertIn(alternate[4], runtime._trim_messages(alternate))
            runtime.repair_focus_retention = "all"
            self.assertEqual(runtime._trim_messages(messages), messages)

    def test_budgeted_history_requires_known_context_and_valid_mode(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            with self.assertRaisesRegex(RUNTIME.WorkerError, "recent or budgeted"):
                RUNTIME.WorkerRuntime(
                    root, packet_v2(), {"coder_context_retention": []}, FakeClient([])
                )
            runtime = RUNTIME.WorkerRuntime(
                root,
                packet_v2(),
                {"python": sys.executable, "coder_context_retention": "budgeted"},
                FakeClient([]),
            )
            with self.assertRaisesRegex(RUNTIME.WorkerError, "configured context length"):
                runtime._trim_messages([{"role": "user", "content": "packet"}])

    def test_missing_supplemental_test_has_scoped_create_feedback(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet()
            value["scope"]["create"] = ["tests/test_supplement.py"]
            value["focused_tests"].append("tests/test_supplement.py")
            value["supplemental_tests"] = ["tests/test_supplement.py"]
            runtime = RUNTIME.WorkerRuntime(root, value, {"python": sys.executable}, FakeClient([]))
            try:
                validation = RUNTIME.ValidationResult(
                    "failed",
                    {},
                    {
                        "exit_code": 4,
                        "output": "ERROR: file or directory not found: tests/test_supplement.py",
                    },
                )
                focus = runtime._validation_repair_focus(validation)[0]
                self.assertEqual(focus["required_next_action"], "SAFE_CREATE")
                self.assertEqual(focus["required_path"], "tests/test_supplement.py")
                self.assertEqual(
                    runtime._compact_repair_payload(focus)["required_next_action"], "SAFE_CREATE"
                )
                runtime.packet["scope"]["create"] = []
                self.assertEqual(
                    runtime._validation_repair_focus(validation)[0]["required_next_action"],
                    "REQUEST_CONTRACT_REVISION",
                )
                validation.focused_tests["exit_code"] = 1
                self.assertEqual(runtime._validation_repair_focus(validation), [])
            finally:
                runtime.close()

    def test_trimmed_duplicate_read_keeps_bounded_source_without_new_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": sys.executable}, FakeClient([])
            )
            try:
                runtime.read_file({"path": "src/example.py"})
                runtime.context_trimmed = True
                runtime.replayed_after_trim_file_versions.add(
                    ("src/example.py", runtime.observed_hashes["src/example.py"])
                )
                duplicate = runtime.read_file({"path": "src/example.py"})
                self.assertEqual(duplicate["status"], "already_read")
                self.assertIn("VALUE = 1", duplicate["source_context"]["content"])
                self.assertEqual(duplicate["new_evidence_count"], 0)
            finally:
                runtime.close()

    def test_repair_nudge_restores_duplicate_read_after_compaction(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            client = FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {"action": "VALIDATE", "arguments": {}},
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {
                        "action": "FINISH_BLOCKED",
                        "arguments": {"reason_code": "no_progress", "reason": "Stopping"},
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), {"python": sys.executable}, client)
            original_execute = runtime.execute

            def execute(action: dict) -> tuple[dict, dict | None]:
                if action["action"] == "VALIDATE":
                    runtime.pending_failed_validation = True
                    return {"status": "failed"}, None
                return original_execute(action)

            focus = {
                "required_next_action": "SAFE_REPLACE",
                "required_path": "src/example.py",
                "candidate_edit_paths": ["src/example.py"],
            }
            with (
                patch.object(runtime, "execute", side_effect=execute),
                patch.object(
                    runtime,
                    "_required_repair_focus",
                    side_effect=lambda: focus if runtime.pending_failed_validation else None,
                ),
            ):
                runtime.run()
            repair_message = client.messages_seen[3][-1]["content"]
            payload = json.loads(repair_message.split("\n", 1)[1])
            self.assertIn("VALUE = 1", payload["restored_prior_read"]["content"])
            self.assertEqual(payload["restored_prior_read"]["new_evidence_count"], 0)

    def test_repair_semantic_invariants_do_not_infer_fields_from_test_names(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            runtime = RUNTIME.WorkerRuntime(
                root, packet_v2(), {"python": "python.exe"}, FakeClient([])
            )
            runtime.validation_failure_delta = {
                "remaining_failures": [
                    "tests/test_identity.py::test_key_preserves_source_metadata_as_input",
                    "tests/test_identity.py::test_key_ignores_row_identity_and_order",
                    "tests/test_identity.py::test_fingerprint_ignores_source_metadata",
                ],
                "resolved_failures": [
                    "tests/test_identity.py::test_fingerprint_ignores_row_identity"
                ],
                "new_failures": [],
            }
            runtime.current_passing_test_ids = {"tests/test_identity.py::test_key_preserves_labels"}
            invariants = runtime._repair_semantic_invariants()
            self.assertEqual(
                invariants["must_keep_resolved"],
                ["tests/test_identity.py::test_fingerprint_ignores_row_identity"],
            )
            self.assertEqual(
                invariants["must_keep_passing"],
                ["tests/test_identity.py::test_key_preserves_labels"],
            )
            self.assertNotIn("must_ignore", invariants)
            self.assertNotIn("must_preserve", invariants)
            payload = runtime._compact_repair_payload(
                {"required_next_action": "SAFE_REPLACE", "candidate_edit_paths": ["src/example.py"]}
            )
            self.assertEqual(payload["semantic_invariants"], invariants)
            self.assertIn("Test names are navigation labels", payload["instruction"])

    def test_first_validation_reserves_finish_turns(self) -> None:
        class LateValidationClient:
            def __init__(self) -> None:
                self.turn = 0

            def complete(self, _messages):
                self.turn += 1
                if self.turn == 1:
                    return json.dumps(
                        {
                            "action": "READ_FILE",
                            "arguments": {"path": "src/example.py"},
                        }
                    )
                if self.turn == 2:
                    self.source_hash = json.loads(_messages[-1]["content"].split("\n", 1)[1])[
                        "sha256"
                    ]
                    return json.dumps(
                        {
                            "action": "READ_FILE",
                            "arguments": {"path": "tests/test_example.py"},
                        }
                    )
                if self.turn == 3:
                    return json.dumps(
                        {
                            "action": "SAFE_REPLACE",
                            "arguments": {
                                "path": "src/example.py",
                                "expected_sha256": self.source_hash,
                                "find": "VALUE = 1",
                                "replace": "VALUE = 2",
                            },
                        }
                    )
                if self.turn == 4:
                    return json.dumps({"action": "VALIDATE", "arguments": {}})
                return json.dumps(
                    {
                        "action": "FINISH_SUCCESS",
                        "arguments": {"summary": ["Validated."], "remaining_uncertainty": []},
                    }
                )

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

    def test_late_successful_edit_reserves_bounded_validation_turns(self) -> None:
        class LateEditClient:
            def __init__(self) -> None:
                self.turn = 0

            def complete(self, messages: list[dict[str, str]]) -> str:
                self.turn += 1
                if self.turn == 1:
                    action = {"action": "READ_FILE", "arguments": {"path": "src/example.py"}}
                elif self.turn == 2:
                    action = {"action": "SEARCH", "arguments": {"query": "VALUE", "path": "src"}}
                elif self.turn == 3:
                    action = {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}}
                elif self.turn == 4:
                    observations = [
                        json.loads(item["content"].split("\n", 1)[1])
                        for item in messages
                        if item["role"] == "user" and item["content"].startswith("OBSERVATION\n")
                    ]
                    action = {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": "src/example.py",
                            "expected_sha256": observations[0]["sha256"],
                            "find": "VALUE = 1\n",
                            "replace": "VALUE = 2\n",
                        },
                    }
                elif self.turn == 5:
                    action = {"action": "VALIDATE", "arguments": {}}
                else:
                    action = {
                        "action": "FINISH_SUCCESS",
                        "arguments": {
                            "summary": ["Validated."],
                            "remaining_uncertainty": [],
                        },
                    }
                return json.dumps(action)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            value = packet_v2()
            value["limits"] = {
                "max_model_turns": 4,
                "prevalidation_edit_turn_reserve": 2,
                "hard_max_model_turns": 6,
            }
            runtime = RUNTIME.WorkerRuntime(
                root, value, {"python": sys.executable}, LateEditClient()
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
            self.assertEqual(runtime.first_validation_turn, 5)
            events = (root / report["evidence_refs"]["events"]).read_text(encoding="utf-8")
            self.assertIn("prevalidation_turns_reserved", events)

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
            self.assertEqual(result["validation"]["configured_checks"][0]["id"], "ruff-check")

    def test_failed_tests_only_run_explicit_diagnostics_with_current_nonzero_junit(self) -> None:
        for mode in (
            "opted",
            "default",
            "missing",
            "skipped",
            "drifted",
            "zero",
            "static-drift",
            "invalid",
            "edited",
        ):
            with self.subTest(mode=mode), TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_tree(root)
                commands = [
                    {
                        "id": "ruff-format",
                        "argv": ["{python}", "-m", "ruff", "format", "--check", "src"],
                    },
                    {"id": "ruff-check", "argv": ["{python}", "-m", "ruff", "check", "src"]},
                    {"id": "unmarked", "argv": ["{python}", "-c", "pass"]},
                ]
                if mode != "default":
                    for command in commands[:2]:
                        command["run_on_test_failure"] = True
                if mode == "invalid":
                    commands[0]["run_on_test_failure"] = "yes"
                config = {
                    "validation_profiles": {
                        "python-focused": {"python": sys.executable, "commands": commands}
                    }
                }
                runtime = RUNTIME.WorkerRuntime(root, packet_v2(), config, FakeClient([]))
                runtime.write_lock.acquire()
                calls = []
                try:
                    runtime._prepare_run_archive()
                    if mode == "edited":
                        observed = runtime.read_file({"path": "src/example.py"})
                        runtime.safe_replace(
                            {
                                "path": "src/example.py",
                                "expected_sha256": observed["sha256"],
                                "find": "VALUE = 1",
                                "replace": "VALUE = 3",
                            }
                        )

                    def fake_command(argv):
                        calls.append(argv)
                        junit_arg = next(
                            (item for item in argv if item.startswith("--junitxml=")), None
                        )
                        if junit_arg:
                            if mode != "missing":
                                tests, skipped = (
                                    (0, 0) if mode == "zero" else (1, int(mode == "skipped"))
                                )
                                Path(junit_arg.split("=", 1)[1]).write_text(
                                    f'<testsuite tests="{tests}" failures="1" errors="0" skipped="{skipped}"><testcase name="test_value"><failure message="AssertionError">failed</failure></testcase></testsuite>'
                                )
                            if mode == "drifted":
                                (root / "src/example.py").write_text("VALUE = 9\n")
                            return {
                                "status": "failed",
                                "exit_code": 1,
                                "output": "assertion failed",
                                "argv": argv,
                            }
                        if "ruff" in argv:
                            if mode == "static-drift":
                                (root / "src/example.py").write_text("VALUE = 9\n")
                            return {
                                "status": "failed",
                                "exit_code": 1,
                                "output": "1 file would be reformatted"
                                if "format" in argv
                                else "src/example.py:1:1: F821 Undefined name `missing`",
                                "argv": argv,
                            }
                        return {"status": "passed", "exit_code": 0, "output": "ok", "argv": argv}

                    with (
                        patch.object(runtime, "_run_command", side_effect=fake_command),
                        patch.object(
                            runtime,
                            "_try_autoformat",
                            side_effect=AssertionError("must not autoformat failed tests"),
                        ),
                    ):
                        if mode == "invalid":
                            with self.assertRaisesRegex(RUNTIME.WorkerError, "must be boolean"):
                                runtime.validate({})
                            self.assertFalse(any("ruff" in argv for argv in calls))
                            continue
                        result = runtime.validate({})
                    static_calls = [argv for argv in calls if "ruff" in argv]
                    self.assertEqual(
                        len(static_calls),
                        2 if mode in {"opted", "edited"} else 1 if mode == "static-drift" else 0,
                    )
                    self.assertEqual(result["status"], "failed")
                    self.assertTrue(runtime.pending_failed_validation)
                    self.assertFalse(runtime._validated_terminal_state())
                    self.assertEqual(runtime.edit_revision, int(mode == "edited"))
                    self.assertEqual(runtime.repairs, 0)
                    if mode == "opted":
                        self.assertEqual(
                            [check["id"] for check in runtime.validation.configured_checks],
                            ["ruff-format", "ruff-check"],
                        )
                        self.assertEqual(runtime.validation.focused_tests["status"], "failed")
                    if mode == "static-drift":
                        self.assertFalse(runtime.validation.focused_tests["inputs_unchanged"])
                    if mode == "edited":
                        check = runtime.validation.configured_checks[0]
                        self.assertTrue(
                            runtime._autoformat_eligible(
                                check["id"], check["argv"], check, Path(sys.executable)
                            )
                        )
                        self.assertEqual(runtime.validation_count, 1)
                finally:
                    runtime.close()

    def test_ruff_autoformat_changes_only_authorized_file_and_revalidates(self) -> None:
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
                            {
                                "id": "ruff-format",
                                "argv": [
                                    "{python}",
                                    "-m",
                                    "ruff",
                                    "format",
                                    "--check",
                                    "src",
                                    "tests",
                                ],
                            }
                        ],
                    }
                }
            }
            runtime = RUNTIME.WorkerRuntime(root, packet_v2(), config, FakeClient([]))
            runtime.write_lock.acquire()
            runtime._prepare_run_archive()
            target = root / "src" / "example.py"
            test_before = (root / "tests" / "test_example.py").read_bytes()
            observed = runtime.read_file({"path": "src/example.py"})
            runtime.safe_replace(
                {
                    "path": "src/example.py",
                    "expected_sha256": observed["sha256"],
                    "find": "VALUE = 1\n",
                    "replace": "VALUE = 'two'\n",
                }
            )
            calls: list[list[str]] = []

            def fake_command(argv: list[str]) -> dict:
                calls.append(argv)
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0" /></testsuites>',
                            encoding="utf-8",
                        )
                if argv[1:4] == ["-m", "ruff", "format"]:
                    if "--check" in argv and "'two'" in target.read_text(encoding="utf-8"):
                        return {
                            "status": "failed",
                            "exit_code": 1,
                            "output": "1 file would be reformatted",
                            "argv": argv,
                        }
                    if "--check" not in argv:
                        target.write_text('VALUE = "two"\n', encoding="utf-8")
                return {"status": "passed", "exit_code": 0, "output": "ok", "argv": argv}

            try:
                with patch.object(runtime, "_run_command", side_effect=fake_command):
                    result = runtime.validate({})
            finally:
                runtime.close()
            self.assertEqual(result["status"], "passed")
            self.assertTrue(runtime.autoformat_used)
            self.assertEqual(len(runtime.validation_refs), 2)
            self.assertEqual(target.read_text(encoding="utf-8"), 'VALUE = "two"\n')
            self.assertEqual((root / "tests" / "test_example.py").read_bytes(), test_before)
            self.assertEqual(
                sum(
                    "--check" not in call for call in calls if call[1:4] == ["-m", "ruff", "format"]
                ),
                1,
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
            client = FakeClient(
                [
                    {
                        "action": "FINISH_BLOCKED",
                        "reason_code": "needs_scope_expansion",
                        "reason": "The implementation is owned by another module.",
                        "requested_scope": {"read": ["src/other.py"], "modify": ["src/other.py"]},
                        "evidence_refs": ["src/example.py:1"],
                        "proposed_next_step": "Primary reviews and issues a revised packet.",
                    }
                ]
            )
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
                {
                    "validation_profiles": {
                        "python-focused": {
                            "python": ".venv/missing-python.exe",
                            "compile": True,
                            "pytest_argv": ["-B", "-m", "pytest"],
                        }
                    }
                },
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
                RUNTIME.WorkerRuntime(
                    root, missing_modify, {"python": sys.executable}, FakeClient([])
                )
            self.assertEqual(modify_error.exception.reason_code, "modify_target_missing")

            existing_create = packet_v2()
            existing_create["scope"]["modify"] = []
            existing_create["scope"]["create"] = ["src/example.py"]
            with self.assertRaisesRegex(RUNTIME.PreflightBlocked, "already exists") as create_error:
                RUNTIME.WorkerRuntime(
                    root, existing_create, {"python": sys.executable}, FakeClient([])
                )
            self.assertEqual(create_error.exception.reason_code, "create_target_exists")

            missing_test = packet_v2()
            missing_test["focused_tests"] = ["tests/test_missing.py"]
            with self.assertRaisesRegex(
                RUNTIME.PreflightBlocked, "focused test does not exist"
            ) as test_error:
                RUNTIME.WorkerRuntime(
                    root, missing_test, {"python": sys.executable}, FakeClient([])
                )
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
            self.assertEqual(report["interruption"]["reason_code"], "invocation_deadline_exceeded")
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
            result = runtime._run_command([sys.executable, "-c", "import time; time.sleep(30)"])
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["timed_out"])
            self.assertEqual(result["termination"]["termination"], "confirmed")
            self.assertTrue(runtime.process_events)

    def test_duplicate_run_id_is_blocked_and_original_archive_is_preserved(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            finish_failed = [
                {
                    "action": "FINISH_FAILED",
                    "arguments": {
                        "summary": ["Stopped."],
                        "reason": "test stop",
                        "remaining_uncertainty": [],
                    },
                }
            ]
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
                    self.test_path.write_text(
                        "def test_value(): pass\n# external change\n", encoding="utf-8"
                    )
                    return json.dumps(
                        {
                            "action": "FINISH_SUCCESS",
                            "arguments": {"summary": ["Done"], "remaining_uncertainty": []},
                        }
                    )
                if self.step == 4:
                    self.step += 1
                    return json.dumps(
                        {
                            "action": "FINISH_FAILED",
                            "arguments": {
                                "summary": ["Validation became stale."],
                                "reason": "external change",
                                "remaining_uncertainty": [],
                            },
                        }
                    )
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
                any(
                    "validation inputs changed" in item["error"]
                    for item in report["protocol_error_details"]
                )
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
