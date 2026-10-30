"""C1 path counterexamples; C1_RUNTIME_ROOT selects the frozen runtime arm."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[1]
TARGET = Path(os.environ.get("C1_RUNTIME_ROOT", str(KIT / ".local-agents")))
SPEC = importlib.util.spec_from_file_location("c1_helpers", TARGET / "tests/test_worker_runtime.py")
HELPERS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HELPERS
SPEC.loader.exec_module(HELPERS)
RUNTIME = HELPERS.RUNTIME


@unittest.skipUnless(os.environ.get("C1_RUNTIME_ROOT"), "Select a frozen C1 runtime arm explicitly")
class RepairAdvisoryTests(unittest.TestCase):
    def exercise(self, target, stale=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src/example.py").write_text("VALUE = 1\n")
            (root / "src/responsibility.py").write_text("RESULT = 1\n")
            (root / "tests/test_example.py").write_text("def test_value(): pass\n")
            packet = HELPERS.packet_v2()
            packet["scope"]["modify"].append("src/responsibility.py")
            digest = RUNTIME.SAFE_EDIT.sha256_bytes((root / "src/responsibility.py").read_bytes())
            client = HELPERS.FakeClient(
                [
                    {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                    {"action": "READ_FILE", "arguments": {"path": "src/responsibility.py"}},
                    {"action": "VALIDATE", "arguments": {}},
                    {
                        "action": "SAFE_REPLACE",
                        "arguments": {
                            "path": target,
                            "expected_sha256": "0" * 64 if stale else digest,
                            "find": "RESULT = 1",
                            "replace": "RESULT = 2",
                        },
                    },
                    {
                        "action": "FINISH_BLOCKED",
                        "arguments": {
                            "reason_code": "diagnostic_control",
                            "reason": "Control ended",
                        },
                    },
                ]
            )
            runtime = RUNTIME.WorkerRuntime(root, packet, {"python": sys.executable}, client)
            original_execute = runtime.execute

            def execute(action):
                if action["action"] == "VALIDATE":
                    runtime.pending_failed_validation = True
                    return {"status": "failed"}, None
                return original_execute(action)

            focus = {"required_path": "src/example.py", "required_next_action": "SAFE_REPLACE"}
            with (
                patch.object(runtime, "execute", side_effect=execute),
                patch.object(
                    runtime,
                    "_required_repair_focus",
                    side_effect=lambda: focus if runtime.pending_failed_validation else None,
                ),
            ):
                runtime.run()
            return (root / "src/responsibility.py").read_text(), packet["scope"]

    def test_incorrect_anchor_does_not_forbid_actual_authorized_owner(self):
        content, scope = self.exercise("src/responsibility.py")
        self.assertEqual(content, "RESULT = 2\n")
        self.assertEqual(scope["modify"], ["src/example.py", "src/responsibility.py"])

    def test_diagnostic_hint_never_authorizes_outside_scope(self):
        content, _ = self.exercise("tests/test_example.py")
        self.assertEqual(content, "RESULT = 1\n")

    def test_other_authorized_path_still_requires_current_hash(self):
        content, _ = self.exercise("src/responsibility.py", stale=True)
        self.assertEqual(content, "RESULT = 1\n")


if __name__ == "__main__":
    unittest.main()
