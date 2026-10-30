"""Separately selected C2 runtime: diagnostic facts are not final confirmation."""

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

TARGET = Path(
    os.environ.get("C2_RUNTIME_ROOT", str(Path(__file__).resolve().parents[1] / ".local-agents"))
)
SPEC = importlib.util.spec_from_file_location("c2_helpers", TARGET / "tests/test_worker_runtime.py")
HELPERS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HELPERS
SPEC.loader.exec_module(HELPERS)


@unittest.skipUnless(os.environ.get("C2_RUNTIME_ROOT"), "Select a frozen C2 runtime arm explicitly")
class DiagnosticCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        HELPERS.WorkerRuntimeTests().make_tree(root)
        packet = HELPERS.packet_v2()
        packet["contract_check_required"] = True
        packet["required_order"] = ["preserve order"]
        self.runtime = HELPERS.RUNTIME.WorkerRuntime(
            root, packet, {"python": sys.executable}, HELPERS.FakeClient([])
        )
        self.addCleanup(self.runtime.close)

    def test_diagnostic_check_may_omit_model_confirmation(self):
        self.assertIsNone(self.runtime._contract_check({}, diagnostic=True))
        self.assertIsNone(self.runtime.last_contract_check)

    def test_diagnostic_false_and_unknown_are_not_changed_to_true(self):
        for claim in (False, None):
            with self.subTest(claim=claim):
                result = self.runtime._contract_check(
                    {"contract_check": {"required_order_confirmed": claim}}, diagnostic=True
                )
                self.assertEqual(result["required_order_confirmed"], claim)
                self.assertEqual(result["required_behavior_ids"], [])

    def test_final_missing_confirmation_is_rejected(self):
        with self.assertRaises(HELPERS.RUNTIME.WorkerError):
            self.runtime._contract_check({})

    def test_final_unknown_and_false_order_are_rejected(self):
        for claim in (False, None):
            with self.subTest(claim=claim), self.assertRaises(HELPERS.RUNTIME.WorkerError):
                self.runtime._contract_check(
                    {
                        "contract_check": {
                            "required_behavior_ids": ["behavior-value"],
                            "required_order_confirmed": claim,
                        }
                    }
                )

    def test_supplied_wrong_behavior_id_is_rejected_even_with_correct_id(self):
        with self.assertRaises(HELPERS.RUNTIME.WorkerError):
            self.runtime._contract_check(
                {"contract_check": {"required_behavior_ids": ["behavior-value", "wrong-id"]}},
                diagnostic=True,
            )

    def test_diagnostic_unrelated_changes_still_rejected(self):
        with self.assertRaises(HELPERS.RUNTIME.WorkerError):
            self.runtime._contract_check(
                {"contract_check": {"unrelated_changes": ["unrelated.py"]}}, diagnostic=True
            )


if __name__ == "__main__":
    unittest.main()
