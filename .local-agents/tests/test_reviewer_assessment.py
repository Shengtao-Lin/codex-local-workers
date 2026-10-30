"""Explicit model-owned issue kinds, unchanged deterministic/source/semantic gates."""

import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import test_reviewer_runtime as helpers

REVIEWER = helpers.REVIEWER


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        request = helpers.ReviewerRuntimeTests().make_run(self.root, risk="high")
        self.runtime = REVIEWER.ReviewerRuntime(
            self.root,
            request,
            {"reviewer_assessment_protocol": True, "reviewer_evidence_ids": True},
            helpers.FakeClient([]),
        )
        self.runtime.read_file({"path": "src/example.py"})

    def report(self, assessment="consistent", status="verified"):
        return {
            "assessment": assessment,
            "findings": [],
            "verified_contract_ids": ["behavior-1"],
            "contract_review": [
                {
                    "obligation_id": "behavior-1",
                    "status": status,
                    "evidence_ids": ["E1"],
                    "evidence": "Actually displayed VALUE assignment is two.",
                }
            ],
            "unverified_claims": [],
            "ordering_review": [],
        }

    def test_valid_choice_is_preserved_and_original_report_unmodified(self):
        args = self.report()
        before = copy.deepcopy(args)
        result = self.runtime.validate_report(args)
        self.assertEqual(result["decision"], "pass_to_primary")
        self.assertEqual(result["model_assessment"], "consistent")
        self.assertEqual(args, before)

    def test_conflict_and_insufficient_evidence_route_only_explicit_model_choices(self):
        for choice in ("contract_conflict", "insufficient_evidence"):
            with self.subTest(choice=choice):
                args = self.report(choice, "uncertain")
                args["verified_contract_ids"] = []
                result = self.runtime.validate_report(args)
                self.assertEqual(result["decision"], "escalate")
                self.assertEqual(result["contract_review"][0]["status"], "uncertain")
                self.assertEqual(result["model_assessment"], choice)

    def test_optional_choice_does_not_drop_concrete_defect_findings(self):
        args = self.report("optional_test_gap")
        args["findings"] = [
            {
                "id": "F1",
                "severity": "high",
                "category": "behavior",
                "path": "src/example.py",
                "line": 1,
                "evidence": "VALUE assignment",
                "contract_id": "behavior-1",
                "suggested_fix": "Review actual owned behavior",
            }
        ]
        with self.assertRaisesRegex(REVIEWER.ReviewError, "empty findings"):
            self.runtime.validate_report(args)

    def test_defect_choice_without_findings_never_auto_creates_a_defect(self):
        for choice in ("implementation_defect", "required_test_gap"):
            with (
                self.subTest(choice=choice),
                self.assertRaisesRegex(REVIEWER.ReviewError, "at least one finding"),
            ):
                self.runtime.validate_report(self.report(choice))

    def test_unknown_missing_mixed_choice_and_nonstring_rejected(self):
        for choice in ("pass_to_primary", None, [], {}, True):
            with (
                self.subTest(choice=choice),
                self.assertRaisesRegex(REVIEWER.ReviewError, "assessment"),
            ):
                self.runtime.validate_report(self.report(choice))
        args = self.report()
        args["decision"] = "pass_to_primary"
        with self.assertRaisesRegex(REVIEWER.ReviewError, "combined"):
            self.runtime.validate_report(args)

    def test_no_keyword_routing_or_verification_auto_fill(self):
        args = self.report("consistent", "uncertain")
        args["contract_review"][0]["evidence"] = (
            "contradictory impossible mutually exclusive contract"
        )
        with self.assertRaises(REVIEWER.ReviewError):
            self.runtime.validate_report(args)
        args["contract_review"][0]["status"] = "verified"
        result = self.runtime.validate_report(args)
        self.assertEqual(result["decision"], "pass_to_primary")
        self.assertEqual(result["model_assessment"], "consistent")
        # This intentionally proves the runtime is NOT a semantic oracle. The original
        # live controls and independent Primary must detect wrong model choices.

    def test_citation_repair_schema_stays_satisfiable_and_same_transport(self):
        tools = REVIEWER.assessment_tools(REVIEWER.evidence_id_tools(REVIEWER.REVIEW_NATIVE_TOOLS))
        repaired = REVIEWER.canonical_citation_tools(tools)
        self.assertEqual(tools, repaired)
        report = next(t for t in repaired if t["function"]["name"] == "REPORT")["function"][
            "parameters"
        ]
        item = report["properties"]["contract_review"]["items"]
        self.assertLessEqual(set(item["required"]), set(item["properties"]))
        self.assertNotIn("decision", report["properties"])
        self.assertEqual(
            report["properties"]["assessment"]["enum"], list(REVIEWER.ASSESSMENT_DECISIONS)
        )

    def test_legacy_default_report_compatibility(self):
        self.runtime.assessment_protocol = False
        args = self.report()
        args.pop("assessment")
        args["decision"] = "pass_to_primary"
        self.assertEqual(self.runtime.validate_report(args)["decision"], "pass_to_primary")
        with self.assertRaisesRegex(REVIEWER.ReviewError, "not enabled"):
            self.runtime.validate_report(self.report())

    def test_missing_current_source_id_and_drift_still_fail(self):
        args = self.report()
        args["contract_review"][0]["evidence_ids"] = ["E999"]
        with self.assertRaisesRegex(REVIEWER.ReviewError, "actually displayed"):
            self.runtime.validate_report(args)
        (self.root / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
        with self.assertRaisesRegex(REVIEWER.ReviewError, "changed"):
            self.runtime.validate_report(self.report())
