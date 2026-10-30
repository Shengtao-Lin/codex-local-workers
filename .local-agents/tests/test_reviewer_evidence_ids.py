"""IDs represent displayed ranges, not automatic semantic verification."""

import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import test_reviewer_runtime as helpers

REVIEWER = helpers.REVIEWER


class EvidenceIdTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        request = helpers.ReviewerRuntimeTests().make_run(self.root, risk="high")
        self.runtime = REVIEWER.ReviewerRuntime(
            self.root, request, {"reviewer_evidence_ids": True}, helpers.FakeClient([])
        )

    def report(self, ids=None, status="verified"):
        return {
            "decision": "pass_to_primary",
            "findings": [],
            "verified_contract_ids": ["behavior-1"],
            "unverified_claims": [],
            "contract_review": [
                {
                    "obligation_id": "behavior-1",
                    "status": status,
                    "evidence_ids": ["E1"] if ids is None else ids,
                    "evidence": "The displayed assignment sets VALUE to two.",
                }
            ],
        }

    def test_diff_display_search_and_template_do_not_issue_ids(self):
        self.runtime.initial_payload()
        self.runtime.search({"query": "VALUE", "path": "src"})
        self.assertEqual(self.runtime.evidence_catalog, {})
        entry = self.runtime.report_template()["arguments"]["contract_review"][0]
        self.assertEqual(entry["status"], "CHOOSE verified, violated, or uncertain")
        self.assertNotIn("source_ref", entry)
        with self.assertRaisesRegex(REVIEWER.ReviewError, "actually displayed IDs"):
            self.runtime.validate_report(self.report())

    def test_ids_resolve_selected_range_and_leave_input_and_status_unchanged(self):
        observation = self.runtime.read_file({"path": "src/example.py"})
        self.assertEqual(observation["citation_evidence"][0]["id"], "E1")
        submitted = self.report()
        before = copy.deepcopy(submitted)
        result = self.runtime.validate_report(submitted)
        self.assertEqual(submitted, before)
        item = result["contract_review"][0]
        self.assertEqual(item["status"], "verified")
        self.assertEqual(item["canonical_quote"], "VALUE = 2")
        self.assertEqual(item["source_ref"]["path"], "src/example.py")

    def test_uncertain_claim_never_becomes_verified(self):
        self.runtime.read_file({"path": "src/example.py"})
        with self.assertRaises(REVIEWER.ReviewError):
            self.runtime.validate_report(self.report(status="uncertain"))

    def test_unknown_duplicate_nonstring_and_mixed_refs_reject(self):
        self.runtime.read_file({"path": "src/example.py"})
        for ids in (["E999"], ["E1", "E1"], [None], [], "E1", ["E1"] * 4):
            with self.subTest(ids=ids), self.assertRaises(REVIEWER.ReviewError):
                self.runtime.validate_report(self.report(ids))
        for field in ("source_ref", "source_refs", "path", "line", "source_quote"):
            args = self.report()
            args["contract_review"][0][field] = None
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(REVIEWER.ReviewError, "combined"),
            ):
                self.runtime.validate_report(args)

    def test_drift_rejects_before_id_resolution_and_duplicate_read_preserves_ids(self):
        self.runtime.read_file({"path": "src/example.py"})
        original = copy.deepcopy(self.runtime.evidence_catalog)
        self.runtime.read_file({"path": "src/example.py"})
        self.assertEqual(self.runtime.evidence_catalog, original)
        (self.root / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
        with self.assertRaisesRegex(REVIEWER.ReviewError, "changed"):
            self.runtime.validate_report(self.report())

    def test_truncated_and_eof_read_do_not_issue_hidden_ranges(self):
        self.runtime.max_output = 3
        self.runtime.read_file({"path": "src/example.py"})
        self.assertEqual(self.runtime.evidence_catalog, {})
        self.runtime.max_output = 1000
        self.runtime.read_file({"path": "src/example.py", "start_line": 100})
        self.assertEqual(self.runtime.evidence_catalog, {})

    def test_only_selected_id_is_used_not_other_read_evidence(self):
        self.runtime.read_file({"path": "tests/test_example.py"})
        self.runtime.read_file({"path": "src/example.py"})
        result = self.runtime.validate_report(self.report(["E2"]))
        self.assertEqual(result["contract_review"][0]["canonical_quote"], "VALUE = 2")

    def test_legacy_report_compatibility_and_new_transport_opt_in(self):
        self.runtime.read_file({"path": "src/example.py"})
        args = self.report()
        args["contract_review"][0].pop("evidence_ids")
        args["contract_review"][0]["source_ref"] = {
            "path": "src/example.py",
            "start_line": 1,
            "end_line": 1,
        }
        self.assertEqual(self.runtime.validate_report(args)["decision"], "pass_to_primary")
        self.runtime.evidence_ids_enabled = False
        with self.assertRaisesRegex(REVIEWER.ReviewError, "not enabled"):
            self.runtime.validate_report(self.report())

    def test_schema_is_copy_and_does_not_fill_verdict(self):
        before = copy.deepcopy(REVIEWER.REVIEW_NATIVE_TOOLS)
        tools = REVIEWER.evidence_id_tools(before)
        self.assertEqual(before, REVIEWER.REVIEW_NATIVE_TOOLS)
        item = next(t for t in tools if t["function"]["name"] == "REPORT")["function"][
            "parameters"
        ]["properties"]["contract_review"]["items"]
        self.assertEqual(
            set(item["properties"]), {"obligation_id", "status", "evidence_ids", "evidence"}
        )
        self.assertEqual(
            item["properties"]["status"]["enum"], ["verified", "violated", "uncertain"]
        )
        self.assertIn("IDs prove display, not correctness", self.runtime.system_prompt())
