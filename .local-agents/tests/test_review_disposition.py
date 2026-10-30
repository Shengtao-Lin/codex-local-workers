import copy
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "disposition", Path(__file__).parents[1] / "review-disposition.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DispositionTests(unittest.TestCase):
    def fixture(self):
        report = {"decision": "rework", "identity": {"run_id": "r"}, "findings": [{"id": "f"}]}
        payload = {
            "schema_version": 1,
            "authority": "primary",
            "identity": report["identity"],
            "report_sha256": "hash",
            "resolution": "cleared",
            "evidence": ["Source proof"],
            "findings": [
                {"finding_id": "f", "disposition": "confirmed_defect", "evidence": "Counterexample"}
            ],
        }
        return report, payload

    def test_routes_each_primary_classification_without_automatic_actions(self):
        for kind, decision in [
            ("confirmed_defect", "rework"),
            ("required_test_gap", "rework"),
            ("nonblocking", "accept"),
            ("contract_revision", "replan"),
            ("unresolved", "replan"),
        ]:
            with self.subTest(kind=kind):
                report, payload = self.fixture()
                payload["findings"][0]["disposition"] = kind
                before = copy.deepcopy(report)
                result = MODULE.adjudicate(report, "hash", payload)
                self.assertEqual(result["primary_decision"], decision)
                self.assertFalse(result["automatic_coder_rework_authorized"])
                self.assertFalse(result["automatic_acceptance"])
                self.assertEqual(report, before)

    def test_stale_cross_run_missing_duplicate_unknown_and_unsubstantiated_rejected(self):
        for field, value in [
            ("report_sha256", "stale"),
            ("identity", {"run_id": "other"}),
            ("authority", "reviewer"),
            ("findings", []),
            ("evidence", []),
        ]:
            report, payload = self.fixture()
            payload[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                MODULE.adjudicate(report, "hash", payload)
        for ids in [("f", "f"), ("other",), ({},)]:
            report, payload = self.fixture()
            payload["findings"] = [
                {"finding_id": i, "disposition": "nonblocking", "evidence": "Source proof"}
                for i in ids
            ]
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                MODULE.adjudicate(report, "hash", payload)

    def test_overall_uncertainty_blocks_even_with_no_findings(self):
        report, payload = self.fixture()
        report.update(decision="escalate", findings=[])
        payload.update(findings=[], resolution="unresolved")
        self.assertEqual(MODULE.adjudicate(report, "hash", payload)["primary_decision"], "replan")
