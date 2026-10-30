"""Ruff diagnostic coordinates never bypass scope, version, display or edit guards."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import test_worker_runtime as helpers

RUNTIME = helpers.RUNTIME


class RuffRepairControls(unittest.TestCase):
    def runtime(self, root):
        helpers.WorkerRuntimeTests().make_tree(root)
        runtime = RUNTIME.WorkerRuntime(
            root,
            helpers.packet_v2(),
            {"python": sys.executable, "coder_block_edits_only": True},
            helpers.FakeClient([]),
        )
        runtime.edit_revision = 1
        return runtime

    def validation(self, runtime, path="src/example.py", line=1, output=None):
        return RUNTIME.ValidationResult(
            "failed",
            {"status": "passed"},
            {
                "status": "passed",
                "inputs_unchanged": True,
                "input_facts": runtime._validation_facts(),
                "diagnostic": {"failures": []},
            },
            configured_checks=[
                {
                    "id": "ruff-check",
                    "status": "failed",
                    "output": output
                    or f"E501 Line too long (159 > 100)\n  --> {path}:{line}:101\nFound 1 error.\n",
                }
            ],
        )

    def test_full_concise_ansi_crlf_and_space_path_diagnostics_are_not_mixed(self):
        for output in (
            "E501 Line too long\n  --> src\\space name.py:235:101\n",
            "E501 Line too long\r\n  --> src\\space name.py:235:101\r\n",
            "\x1b[31mE501\x1b[0m Line too long\n  --> src\\space name.py:235:101\n",
            "src/space name.py:235:101: E501 Line too long\n",
        ):
            with self.subTest(output=output):
                hint = RUNTIME.WorkerRuntime._configured_check_repair_hint(
                    [
                        {
                            "id": "ruff-check",
                            "status": "failed",
                            "output": output
                            + "F821 Undefined name `other`\n  --> src/other.py:7:2\n",
                        }
                    ]
                )
                self.assertEqual(
                    (hint["rule"], hint["path"], hint["line"]), ("F821", "src/other.py", 7)
                )
                # Existing special F821 handling takes priority; generic E501 must
                # not borrow another diagnostic's location when tested by itself.
                standalone = output
                hint = RUNTIME.WorkerRuntime._configured_check_repair_hint(
                    [{"id": "ruff-check", "status": "failed", "output": standalone}]
                )
                self.assertEqual(
                    (hint["rule"], hint["path"], hint["line"], hint["column"]),
                    ("E501", "src/space name.py", 235, 101),
                )

    def test_current_source_is_early_bounded_real_evidence_and_static_only_instruction(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self.runtime(root)
            source = root / "src/example.py"
            source.write_text(
                "VALUE = 1\n" + "\n" * 233 + "# offending words " * 10 + "\n", encoding="utf-8"
            )
            validation = self.validation(runtime, path=str(source), line=235)
            runtime.validation = validation
            runtime.pending_failed_validation = True
            focus = runtime._required_repair_focus()
            self.assertEqual(focus["required_path"], "src/example.py")
            self.assertEqual(
                focus["current_source"]["sha256"],
                RUNTIME.RUN_STATE.sha256_bytes(source.read_bytes()),
            )
            self.assertEqual(focus["current_source"]["start_line"], 232)
            self.assertIn("235: # offending words", focus["current_source"]["content"])
            self.assertNotIn("1: VALUE", focus["current_source"]["content"])
            observation = runtime._validation_observation(validation)
            self.assertNotIn("src/example.py", runtime.observed_hashes)
            encoded = runtime._encode_observation(observation)
            self.assertLess(encoded.index("source_excerpts"), encoded.index("configured_checks"))
            self.assertEqual(
                runtime.observed_hashes["src/example.py"], focus["current_source"]["sha256"]
            )
            payload = runtime._compact_repair_payload(focus)
            self.assertEqual(payload["source_excerpts"], [focus["current_source"]])
            self.assertIn("need not change runtime behavior", payload["instruction"])
            self.assertEqual(source.read_text().splitlines()[234], "# offending words " * 10)
            self.assertEqual(runtime.validation_count, 0)  # No validation or edit fabricated.

    def test_outside_forbidden_readonly_and_missing_files_never_get_edit_authority(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self.runtime(root)
            for path in (
                "../outside.py",
                str(root.parent / "outside.py"),
                ".agent/secret.py",
                "src/secret.py",
                "src/missing.py",
            ):
                with self.subTest(path=path):
                    focus = runtime._validation_repair_focus(self.validation(runtime, path=path))[0]
                    self.assertNotIn("current_source", focus)
                    self.assertNotIn("required_next_action", focus)
                    self.assertNotIn("required_path", focus)
            focus = runtime._validation_repair_focus(
                self.validation(runtime, path="tests/test_example.py")
            )[0]
            self.assertIn(
                "current_source", focus
            )  # Read-only source may be displayed, never edited.
            self.assertNotIn("required_next_action", focus)
            self.assertEqual(runtime.packet["scope"]["modify"], ["src/example.py"])

    def test_stale_missing_changed_snapshots_invalid_lines_and_oversized_source_fail_closed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self.runtime(root)
            source = root / "src/example.py"
            validation = self.validation(runtime)
            source.write_text("VALUE = 2\n", encoding="utf-8")
            focus = runtime._validation_repair_focus(validation)[0]
            self.assertEqual(focus["location_status"], "stale_validation_source")
            self.assertNotIn("current_source", focus)
            for mode in ("missing", "changed", "bad_line", "oversized"):
                with self.subTest(mode=mode):
                    value = self.validation(runtime, line=999 if mode == "bad_line" else 1)
                    if mode == "missing":
                        value.focused_tests.pop("input_facts")
                    elif mode == "changed":
                        value.focused_tests["inputs_unchanged"] = False
                    elif mode == "oversized":
                        source.write_text("# word " * 1000 + "\n", encoding="utf-8")
                        value = self.validation(runtime)
                    focus = runtime._validation_repair_focus(value)[0]
                    self.assertNotIn("current_source", focus)
                    self.assertNotIn("required_next_action", focus)

    def test_malformed_or_nonruff_diagnostics_do_not_authorize_coordinates(self):
        for output in (
            "E501 Line too long\n  --> src/example.py:0:101\n",
            "E501 Line too long\n  --> src/example.py:1:0\n",
            "E501 Line too long\n  --> src/example.py:NaN:101\n",
            "E501 Line too long\n  --> src/example.py\n",
        ):
            with self.subTest(output=output):
                hint = RUNTIME.WorkerRuntime._configured_check_repair_hint(
                    [
                        {"id": "ruff-check", "status": "failed", "output": output},
                    ]
                )
                self.assertNotIn("path", hint)
        hint = RUNTIME.WorkerRuntime._configured_check_repair_hint(
            [
                {
                    "id": "unrelated-check",
                    "status": "failed",
                    "output": "E501 Line too long\n  --> src/example.py:1:101\n",
                },
            ]
        )
        self.assertNotIn("path", hint)

    def test_truncated_or_drifted_prefetch_never_grants_source_evidence(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self.runtime(root)
            validation = self.validation(runtime)
            observation = runtime._validation_observation(validation)
            runtime.max_output = 80
            runtime._encode_observation(observation)
            self.assertNotIn("post_edit_source_read", observation)
            self.assertEqual(runtime.observed_hashes, {})
            runtime.max_output = 16000
            observation = runtime._validation_observation(validation)
            focus = runtime._validation_repair_focus(validation)[0]
            (root / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
            runtime._encode_observation(observation)
            self.assertEqual(runtime.observed_hashes, {})
            self.assertEqual(runtime._compact_repair_payload(focus)["source_excerpts"], [])

    def test_baseline_stays_investigative_and_noop_and_hash_guards_stay_enabled(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self.runtime(root)
            validation = self.validation(runtime)
            runtime.edit_revision = 0
            runtime.validation = validation
            runtime.pending_failed_validation = True
            self.assertIsNone(runtime._required_repair_focus())
            self.assertNotIn(
                "required_next_action",
                runtime._validation_observation(validation)["repair_focus"][0],
            )
            runtime.edit_revision = 1
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                value = {
                    "path": "src/example.py",
                    "expected_sha256": "0" * 64,
                    "find": "VALUE = 1\n",
                    "replace": "VALUE = 2\n",
                }
                with self.assertRaisesRegex(RUNTIME.SafeEditError, "changed since"):
                    runtime.safe_replace(value)
                with self.assertRaisesRegex(RUNTIME.WorkerError, "identical"):
                    runtime.safe_replace({**value, "replace": value["find"]})
                with self.assertRaisesRegex(RUNTIME.WorkerError, "unavailable"):
                    runtime.safe_replace_line({})
                self.assertEqual((root / "src/example.py").read_text(), "VALUE = 1\n")
            finally:
                runtime.close()

    def test_displayed_static_failure_converts_to_real_block_edit_in_bounded_loop(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            helpers.WorkerRuntimeTests().make_tree(root)
            source = root / "src/example.py"
            long_line = "# offending words " * 10
            source.write_text("VALUE = 1\n" + "\n" * 233 + long_line + "\n", encoding="utf-8")

            class Model(helpers.AdaptiveSuccessClient):
                def complete(self, messages):
                    if self.step == 0:
                        self.step = 1
                        return json.dumps(
                            {
                                "action": "READ_FILE",
                                "arguments": {"path": "src/example.py", "end_line": 1},
                            }
                        )
                    if self.step == 3:
                        self.step = 4
                        observation = json.loads(messages[-1]["content"].split("\n", 1)[1])
                        assert "source_excerpts" in observation, observation
                        excerpt = observation["source_excerpts"][0]
                        return json.dumps(
                            {
                                "action": "SAFE_REPLACE",
                                "arguments": {
                                    "path": excerpt["path"],
                                    "expected_sha256": excerpt["sha256"],
                                    "find": long_line,
                                    "replace": "# shorter words",
                                },
                            }
                        )
                    if self.step == 4:
                        self.step = 5
                        return json.dumps({"action": "VALIDATE", "arguments": {}})
                    return super().complete(messages)

            runtime = RUNTIME.WorkerRuntime(
                root,
                helpers.packet_v2(),
                {
                    "python": sys.executable,
                    "coder_block_edits_only": True,
                    "validation_profiles": {
                        "python-focused": {
                            "python": sys.executable,
                            "compile": False,
                            "commands": [
                                {
                                    "id": "ruff-check",
                                    "argv": ["{python}", "-m", "ruff", "check", "src"],
                                }
                            ],
                        }
                    },
                },
                Model(),
            )

            def command(argv):
                for item in argv:
                    if item.startswith("--junitxml="):
                        Path(item.split("=", 1)[1]).write_text(
                            '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase name="controlled" /></testsuite></testsuites>',
                            encoding="utf-8",
                        )
                failed = "ruff" in argv and long_line in source.read_text()
                return {
                    "status": "failed" if failed else "passed",
                    "exit_code": int(failed),
                    "argv": argv,
                    "output": "E501 Line too long\n  --> src/example.py:235:101\n"
                    if failed
                    else "controlled check",
                }

            with patch.object(runtime, "_run_command", side_effect=command):
                report = runtime.run()
            self.assertEqual(report["status"], "ready_for_review", report)
            self.assertEqual(runtime.edit_revision, 2)
            self.assertEqual(runtime.validation_count, 2)
            self.assertEqual(source.read_text().splitlines()[234], "# shorter words")
            self.assertIn("VALUE = 2", source.read_text())
            self.assertEqual(report["protocol_error_count"], 0)
