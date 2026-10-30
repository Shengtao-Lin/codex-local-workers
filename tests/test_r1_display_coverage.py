"""Frozen R1 counterexamples: display is necessary, never semantic proof."""

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

TARGET = Path(
    os.environ.get("R1_RUNTIME_ROOT", str(Path(__file__).resolve().parents[1] / ".local-agents"))
)
SPEC = importlib.util.spec_from_file_location(
    "r1_helpers", TARGET / "tests/test_reviewer_runtime.py"
)
HELPERS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HELPERS
SPEC.loader.exec_module(HELPERS)


@unittest.skipUnless(os.environ.get("R1_RUNTIME_ROOT"), "Select the frozen R1 candidate explicitly")
class DisplayCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        request = HELPERS.ReviewerRuntimeTests().make_run(self.root)
        self.runtime = HELPERS.REVIEWER.ReviewerRuntime(
            self.root, request, {}, HELPERS.FakeClient([])
        )

    def test_full_diff_covers_hunk_not_semantics_or_test(self):
        self.runtime.initial_payload()
        facts = self.runtime.coverage_facts()
        self.assertTrue(facts["requirements"][0]["displayed"])
        self.assertEqual(facts["semantic_understanding"], "not_inferred_from_display")
        self.assertEqual([m["path"] for m in facts["missing"]], ["tests/test_example.py"])

    def test_reading_only_header_does_not_cover_change(self):
        self.runtime.diff = "--- a/src/example.py\n+++ b/src/example.py\n@@ -2 +2 @@\n-old\n+new\n"
        self.runtime.read_file({"path": "src/example.py", "end_line": 1})
        self.assertFalse(self.runtime.coverage_facts()["requirements"][0]["displayed"])

    def test_two_changed_files_need_both_hunks(self):
        self.runtime.diff += "--- a/src/second.py\n+++ b/src/second.py\n@@ -1 +1 @@\n-old\n+new\n"
        self.runtime.read_file({"path": "src/example.py"})
        missing = self.runtime.coverage_facts()["missing"]
        self.assertIn("src/second.py", [m["path"] for m in missing])

    def test_non_python_hunk_requires_display(self):
        (self.root / "src/settings.txt").write_text("enabled\n", encoding="utf-8")
        self.runtime.diff = (
            "--- a/src/settings.txt\n+++ b/src/settings.txt\n@@ -1 +1 @@\n-disabled\n+enabled\n"
        )
        self.assertFalse(self.runtime.coverage_facts()["requirements"][0]["displayed"])
        self.runtime.initial_payload()
        self.assertTrue(self.runtime.coverage_facts()["requirements"][0]["displayed"])

    def test_truncated_diff_cannot_cover_hunk(self):
        self.runtime.config["reviewer_initial_diff_chars"] = 30
        self.assertTrue(self.runtime.initial_payload()["diff_truncated"])
        self.assertFalse(self.runtime.coverage_facts()["requirements"][0]["displayed"])

    def test_truncated_read_cannot_cover_test(self):
        self.runtime.max_output = 12
        self.runtime.read_file({"path": "tests/test_example.py"})
        self.assertIn(
            "tests/test_example.py", [m["path"] for m in self.runtime.coverage_facts()["missing"]]
        )

    def test_display_source_drift_is_rejected(self):
        self.runtime.initial_payload()
        (self.root / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
        with self.assertRaisesRegex(HELPERS.REVIEWER.ReviewError, "changed"):
            self.runtime.coverage_facts()

    def test_primary_call_boundary_needs_exact_range(self):
        self.runtime.request["coverage_targets"] = [
            {"path": "tests/test_example.py", "start_line": 2, "end_line": 2}
        ]
        self.runtime.read_file({"path": "tests/test_example.py", "end_line": 1})
        self.assertFalse(self.runtime.coverage_facts()["requirements"][-1]["displayed"])
        self.runtime.read_file({"path": "tests/test_example.py", "start_line": 2})
        self.assertTrue(self.runtime.coverage_facts()["requirements"][-1]["displayed"])

    def test_complete_display_does_not_populate_contract_citations(self):
        self.runtime.initial_payload()
        self.assertEqual(self.runtime.read_lines, {})
        with self.assertRaisesRegex(HELPERS.REVIEWER.ReviewError, "not read"):
            self.runtime._canonical_contract_ref(
                {"path": "src/example.py", "start_line": 1, "end_line": 1}
            )
