"""Block-only candidate controls; no local model calls and no weakened execution gates."""

import copy
from contextlib import contextmanager
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import test_coder_action_schema as reference
import test_worker_runtime as helpers

RUNTIME = helpers.RUNTIME


class BlockEditControls(unittest.TestCase):
    @contextmanager
    def writer(self, runtime):
        runtime.write_lock.acquire()
        try:
            runtime._prepare_run_archive()
            yield
        finally:
            runtime.close()

    def make_runtime(self, root, enabled=True, packet=None, client=None):
        helpers.WorkerRuntimeTests().make_tree(root)
        return RUNTIME.WorkerRuntime(
            root,
            packet or helpers.packet_v2(),
            {"python": sys.executable, "coder_block_edits_only": enabled},
            client or helpers.FakeClient([]),
        )

    def test_schema_removes_line_after_every_state_gate_without_broadening(self):
        bases = [
            RUNTIME.CODER_ACTION_SCHEMA,
            RUNTIME.repair_only_action_schema(RUNTIME.CODER_ACTION_SCHEMA, "SAFE_REPLACE"),
            RUNTIME.post_edit_progress_schema(RUNTIME.CODER_ACTION_SCHEMA),
            RUNTIME.validation_only_action_schema(RUNTIME.CODER_ACTION_SCHEMA),
        ]
        terminal = copy.deepcopy(RUNTIME.CODER_ACTION_SCHEMA)
        terminal["properties"]["action"]["enum"] = ["FINISH_SUCCESS"]
        bases.append(terminal)
        for base in bases:
            with self.subTest(base=base["properties"]["action"]["enum"]):
                before = copy.deepcopy(base)
                block = RUNTIME.block_edit_action_schema(base)
                self.assertEqual(base, before)
                self.assertEqual(
                    block["properties"]["action"]["enum"],
                    [a for a in before["properties"]["action"]["enum"] if a != "SAFE_REPLACE_LINE"],
                )
                typed = RUNTIME.typed_coder_action_schema(block, contract_check_required=True)
                self.assertFalse(
                    reference.matches(
                        typed,
                        {
                            "action": "SAFE_REPLACE_LINE",
                            "arguments": {
                                "path": "src/example.py",
                                "line": 1,
                                "expected_sha256": "current",
                                "replacement": "VALUE = 2",
                            },
                        },
                    )
                )
                if "VALIDATE" in block["properties"]["action"]["enum"]:
                    self.assertFalse(
                        reference.matches(typed, {"action": "VALIDATE", "arguments": {}})
                    )
                self.assertEqual(RUNTIME.block_edit_action_schema(block), block)

    def test_hidden_action_rejected_before_begin_edit_even_with_valid_current_evidence(self):
        for replacement in ("VALUE = 2", "VALUE = 2\nNEXT = 3"):
            with self.subTest(replacement=replacement), TemporaryDirectory() as directory:
                root = Path(directory)
                runtime = self.make_runtime(root)
                observed = runtime.read_file({"path": "src/example.py"})
                args = {
                    "path": "src/example.py",
                    "expected_sha256": observed["sha256"],
                    "line": 1,
                    "replacement": replacement,
                }
                with patch.object(runtime, "_begin_edit") as begin:
                    with self.assertRaisesRegex(RUNTIME.WorkerError, "unavailable in block-only"):
                        runtime.execute({"action": "SAFE_REPLACE_LINE", "arguments": args})
                    with self.assertRaisesRegex(RUNTIME.WorkerError, "unavailable in block-only"):
                        runtime.safe_replace_line(args)
                    begin.assert_not_called()
                self.assertEqual((root / "src/example.py").read_text(), "VALUE = 1\n")
                self.assertEqual(runtime.edit_revision, 0)

    def test_block_edits_retain_hash_find_and_scope_guards(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self.make_runtime(root)
            observed = runtime.read_file({"path": "src/example.py"})
            good = {
                "path": "src/example.py",
                "expected_sha256": observed["sha256"],
                "find": "VALUE = 1\n",
                "replace": "VALUE = 2\nNEXT = 3\n",
            }
            with self.writer(runtime):
                for override in (
                    {"expected_sha256": "0" * 64},
                    {"find": "absent\n"},
                    {"path": "src/secret.py"},
                    {"replace": "VALUE = 1\n"},
                ):
                    with self.subTest(override=override):
                        with self.assertRaises(
                            (RUNTIME.WorkerError, RUNTIME.SafeEditError)
                        ) as caught:
                            runtime.safe_replace({**good, **override})
                        self.assertNotIn("write lock", str(caught.exception))
                        self.assertEqual((root / "src/example.py").read_text(), "VALUE = 1\n")
                self.assertEqual(runtime.safe_replace(good)["status"], "ok")
            self.assertEqual((root / "src/example.py").read_text(), "VALUE = 2\nNEXT = 3\n")

    def test_legacy_mode_and_default_capability_description_unchanged(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = self.make_runtime(root, enabled=False)
            self.assertIn("- SAFE_REPLACE_LINE:", runtime.system_prompt())
            observed = runtime.read_file({"path": "src/example.py"})
            with self.writer(runtime):
                runtime.safe_replace_line(
                    {
                        "path": "src/example.py",
                        "expected_sha256": observed["sha256"],
                        "line": 1,
                        "replacement": "VALUE = 2",
                    }
                )
            self.assertEqual((root / "src/example.py").read_text(), "VALUE = 2\n")
        with TemporaryDirectory() as directory:
            runtime = self.make_runtime(Path(directory))
            self.assertNotIn("SAFE_REPLACE_LINE", runtime.system_prompt())
            self.assertIn("- SAFE_REPLACE:", runtime.system_prompt())
            self.assertIn("- SAFE_CREATE:", runtime.system_prompt())

    def test_actual_wire_has_no_line_and_preserves_required_ack(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            client = RUNTIME.LMStudioClient(
                "http://unused/v1", "unchanged-model", typed_action_arguments=True
            )
            packet = helpers.packet_v2()
            packet["contract_check_required"] = True
            runtime = self.make_runtime(root, client=client, packet=packet)
            captured = []

            def response(request, **_kwargs):
                captured.append(json.loads(request.data))
                return io.BytesIO(
                    json.dumps(
                        {
                            "choices": [
                                {
                                    "message": {
                                        "content": json.dumps(
                                            {
                                                "action": "FINISH_FAILED",
                                                "arguments": {
                                                    "reason": "negative control",
                                                    "summary": [],
                                                },
                                            }
                                        )
                                    },
                                    "finish_reason": "stop",
                                }
                            ]
                        }
                    ).encode()
                )

            original = copy.deepcopy(client.action_schema)
            with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=response):
                report = runtime.run()
            self.assertEqual(report["status"], "failed")
            self.assertEqual(client.action_schema, original)
            branches = {
                b["properties"]["action"]["enum"][0]: b
                for b in captured[0]["response_format"]["json_schema"]["schema"]["anyOf"]
            }
            self.assertNotIn("SAFE_REPLACE_LINE", branches)
            self.assertEqual(
                branches["VALIDATE"]["properties"]["arguments"]["required"], ["contract_check"]
            )
            self.assertEqual((root / "src/example.py").read_text(), "VALUE = 1\n")

    def test_invalid_flag_and_native_transport_fail_closed(self):
        for invalid in (None, "true", 1):
            with self.subTest(invalid=invalid), TemporaryDirectory() as directory:
                with self.assertRaisesRegex(RUNTIME.WorkerError, "must be a boolean"):
                    self.make_runtime(Path(directory), enabled=invalid)
        with TemporaryDirectory() as directory:
            client = helpers.FakeClient([])
            client.native_tools = []
            with self.assertRaisesRegex(RUNTIME.WorkerError, "requires JSON action transport"):
                self.make_runtime(Path(directory), client=client)
