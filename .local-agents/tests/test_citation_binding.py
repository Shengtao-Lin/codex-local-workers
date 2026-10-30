"""Mechanical identity negatives, report transport controls and trusted plan propagation."""

import copy
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import test_reviewer_runtime as helpers

SPEC = importlib.util.spec_from_file_location(
    "citation_binding_under_test", Path(__file__).resolve().parents[1] / "citation-binding.py"
)
BINDING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BINDING)
REVIEWER = helpers.REVIEWER
WORKER = REVIEWER.WORKER
REF = {"path": "src/example.py", "symbol": "Client.fetch"}
SOURCE = 'class Client:\n    def other(self):\n        return 1\n\n    async def fetch(self):\n        """fetch implementation explanation"""\n        # fetch should await get\n        return await self.get("x")\n'


class BindingControls(unittest.TestCase):
    def validate(self, value):
        return BINDING.validate_binding(
            value, readable=["src", "tests"], forbidden=["src/private"], tests=["tests/check.py"]
        )

    def test_bad_shape_scope_control_test_nonpython_and_symbol_fail_closed(self):
        cases = [
            None,
            {},
            {**REF, "extra": True},
            {"path": "../src/a.py", "symbol": "fetch"},
            {"path": "src\\a.py", "symbol": "fetch"},
            {"path": "src//a.py", "symbol": "fetch"},
            {"path": "src/private/a.py", "symbol": "fetch"},
            {"path": "elsewhere/a.py", "symbol": "fetch"},
            {"path": "tests/check.py", "symbol": "fetch"},
            {"path": "src/test_helper.py", "symbol": "fetch"},
            {"path": "src/a.js", "symbol": "fetch"},
            {"path": "src/a.py", "symbol": ""},
            {"path": "src/a.py", "symbol": "Client..fetch"},
            {"path": "src/a.py", "symbol": "class"},
        ]
        for item in cases:
            with self.subTest(item=item), self.assertRaises(ValueError):
                self.validate(item)
        self.assertEqual(self.validate(REF), REF)

    def test_wrong_file_symbol_header_comment_docstring_and_similar_name_reject(self):
        self.assertEqual(BINDING.statement_lines(SOURCE, "Client.fetch"), {8})
        for start, end in ((1, 1), (2, 3), (5, 5), (6, 6), (7, 7)):
            with self.subTest(start=start):
                self.assertFalse(
                    BINDING.covers(
                        REF, SOURCE, [{"path": REF["path"], "start_line": start, "end_line": end}]
                    )
                )
        self.assertFalse(
            BINDING.covers(REF, SOURCE, [{"path": "src/other.py", "start_line": 8, "end_line": 8}])
        )
        self.assertTrue(
            BINDING.covers(REF, SOURCE, [{"path": REF["path"], "start_line": 8, "end_line": 8}])
        )
        for source in (
            "# Client.fetch\nVALUE = 1\n",
            'TEXT = "Client.fetch"\n',
            "class Client:\n    def fetch_extra(self):\n        return 1\n",
            "class Other:\n    def fetch(self):\n        return 1\n",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                BINDING.statement_lines(source, REF["symbol"])

    def test_missing_ambiguous_syntax_error_and_bodyless_symbol_reject(self):
        for source in (
            "def fetch(:\n",
            'class Client:\n    def fetch(self):\n        """only docs"""\n',
            "class Client:\n    def fetch(self):\n        return 1\n    def fetch(self):\n        return 2\n",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                BINDING.statement_lines(source, REF["symbol"])
        self.assertEqual(BINDING.statement_lines("VALUE = 2\n", "VALUE"), {1})


class ReportBindingControls(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.request = helpers.ReviewerRuntimeTests().make_run(
            self.root, risk="high", source_content=SOURCE
        )
        self.run = self.root / ".agent/tasks/task-1/runs/run-1"
        packet = json.loads((self.run / "packet.json").read_text())
        packet["required_behavior"][0]["implementation_ref"] = REF
        (self.run / "packet.json").write_text(json.dumps(packet))
        self.runtime = REVIEWER.ReviewerRuntime(
            self.root,
            self.request,
            {"reviewer_evidence_ids": True, "reviewer_assessment_protocol": True},
            helpers.FakeClient([]),
        )
        self.runtime.initial_payload()

    def report(self, ids):
        return {
            "assessment": "consistent",
            "findings": [],
            "verified_contract_ids": ["behavior-1"],
            "unverified_claims": [],
            "contract_review": [
                {
                    "obligation_id": "behavior-1",
                    "status": "verified",
                    "evidence_ids": ids,
                    "evidence": "Observed implementation awaits get sequentially.",
                }
            ],
        }

    def read_all(self):
        self.runtime.read_file({"path": "src/example.py"})
        self.runtime.read_file({"path": "tests/test_example.py"})

    def test_test_only_citation_rejects_even_when_correct_code_was_read(self):
        self.read_all()
        with self.assertRaisesRegex(REVIEWER.ReviewError, "bound implementation citation"):
            self.runtime.validate_report(self.report(["E2"]))

    def test_unrelated_same_file_and_signature_only_ranges_reject(self):
        self.runtime.read_file({"path": "src/example.py", "start_line": 2, "end_line": 3})
        self.runtime.read_file({"path": "src/example.py", "start_line": 5, "end_line": 5})
        self.runtime.read_file({"path": "src/example.py", "start_line": 8, "end_line": 8})
        self.runtime.read_file({"path": "tests/test_example.py"})
        for evidence_id in ("E1", "E2"):
            with (
                self.subTest(evidence_id=evidence_id),
                self.assertRaisesRegex(REVIEWER.ReviewError, "bound implementation citation"),
            ):
                self.runtime.validate_report(self.report([evidence_id]))
        self.assertEqual(
            self.runtime.validate_report(self.report(["E3"]))["decision"], "pass_to_primary"
        )

    def test_positive_source_plus_test_refs_preserve_verdict_and_input(self):
        self.read_all()
        submitted = self.report(["E1", "E2"])
        before = copy.deepcopy(submitted)
        result = self.runtime.validate_report(submitted)
        self.assertEqual(submitted, before)
        self.assertEqual(result["decision"], "pass_to_primary")
        self.assertEqual(result["contract_review"][0]["implementation_ref"], REF)

    def test_stale_source_unread_lines_and_invented_id_still_reject(self):
        self.read_all()
        with self.assertRaisesRegex(REVIEWER.ReviewError, "actually displayed IDs"):
            self.runtime.validate_report(self.report(["E999"]))
        legacy = self.report(["E1"])
        entry = legacy["contract_review"][0]
        entry.pop("evidence_ids")
        entry["source_ref"] = {"path": "src/example.py", "start_line": 99, "end_line": 99}
        with self.assertRaises(REVIEWER.ReviewError):
            self.runtime.validate_report(legacy)
        (self.root / "src/example.py").write_text(SOURCE + "# drift\n")
        with self.assertRaisesRegex(REVIEWER.ReviewError, "changed"):
            self.runtime.validate_report(self.report(["E1"]))

    def test_legacy_transport_cannot_bypass_binding(self):
        self.read_all()
        bad = self.report(["E2"])
        entry = bad["contract_review"][0]
        entry.pop("evidence_ids")
        entry["path"] = "tests/test_example.py"
        entry["line"] = 2
        entry["source_quote"] = "assert True"
        with self.assertRaisesRegex(REVIEWER.ReviewError, "bound implementation citation"):
            self.runtime.validate_report(bad)
        entry.pop("path")
        entry.pop("line")
        entry.pop("source_quote")
        entry["source_refs"] = [{"path": "src/example.py", "start_line": 8, "end_line": 8}]
        self.assertEqual(self.runtime.validate_report(bad)["decision"], "pass_to_primary")

    def test_repair_offers_only_eligible_displayed_ids_not_a_verdict(self):
        self.read_all()
        repair = self.runtime.report_repair(
            "contract_review behavior-1 requires bound implementation citation", self.report(["E2"])
        )
        self.assertEqual(repair["required_implementation_ref"], REF)
        self.assertEqual(repair["eligible_evidence_ids"], ["E1"])
        self.assertNotIn("decision", repair)
        self.assertNotIn("status", repair)
        self.assertNotIn("source_quote", repair)

    def test_missing_implementation_can_escalate_but_not_claim_verified(self):
        self.read_all()
        report = self.report(["E2"])
        report["assessment"] = "insufficient_evidence"
        report["verified_contract_ids"] = []
        report["contract_review"][0]["status"] = "uncertain"
        self.assertEqual(self.runtime.validate_report(report)["decision"], "escalate")

    def test_packet_binding_is_preserved_and_test_or_scope_binding_rejected(self):
        packet = json.loads((self.run / "packet.json").read_text())
        self.assertEqual(
            WORKER.validate_packet(copy.deepcopy(packet))["required_behavior"][0][
                "implementation_ref"
            ],
            REF,
        )
        for ref in (
            {"path": "tests/test_example.py", "symbol": "test_value"},
            {"path": "outside.py", "symbol": "fetch"},
            None,
        ):
            bad = copy.deepcopy(packet)
            bad["required_behavior"][0]["implementation_ref"] = ref
            with self.subTest(ref=ref), self.assertRaises(WORKER.WorkerError):
                WORKER.validate_packet(bad)

    def test_binding_requires_contract_entry_even_for_small_or_medium_units(self):
        self.read_all()
        for level in ("small", "medium"):
            with self.subTest(level=level):
                self.runtime.packet["risk"]["unit"] = level
                missing = self.report(["E1"])
                missing["contract_review"] = []
                with self.assertRaisesRegex(REVIEWER.ReviewError, "source-backed contract_review"):
                    self.runtime.validate_report(missing)
                self.assertEqual(
                    self.runtime.validate_report(self.report(["E1"]))["decision"], "pass_to_primary"
                )


class PlanBindingControls(unittest.TestCase):
    def setUp(self):
        import test_coordinator_brief as helpers_brief

        self.brief_module = helpers_brief.MODULE
        self.brief, _ = helpers_brief.example()
        self.brief["contracts"][0]["implementation_ref"] = {"path": "src/a.py", "symbol": "collect"}
        self.proposal = {
            "status": "proposed",
            "questions": [],
            "rationale": "One owned implementation each.",
            "units": [
                {
                    "id": c,
                    "goal": c,
                    "owner": "local-coder",
                    "risk": "medium",
                    "contracts": [c],
                    "dependencies": [],
                    "modify": [p],
                    "create": [],
                }
                for c, p in (("producer", "src/a.py"), ("consumer", "src/b.py"))
            ],
        }

    def packet(self):
        plan = self.brief_module.proposal_plan(self.brief, self.proposal)
        proposal = {
            "unit_id": "unit-1",
            "run_id": "binding-run",
            "attempt": 1,
            "packet_revision": 1,
            "goal": "producer",
            "scope": {"read": ["src", "tests"], "modify": ["src/a.py"], "create": []},
            "edit_targets": [{"path": "src/a.py", "anchor": "collect"}],
            "focused_tests": ["tests/test_a.py"],
            "supplemental_tests": [],
            "implementation_guidance": [],
        }
        return plan, self.brief_module.CONTRACT.materialize_bounded_packet(plan, proposal)

    def test_primary_binding_survives_brief_plan_packet_and_normalization(self):
        _, packet = self.packet()
        self.assertEqual(
            packet["required_behavior"][0]["implementation_ref"],
            self.brief["contracts"][0]["implementation_ref"],
        )

    def test_model_cannot_omit_change_or_add_unapproved_binding(self):
        plan, packet = self.packet()
        for value in (None, {"path": "src/a.py", "symbol": "wrong"}):
            bad = copy.deepcopy(packet)
            if value is None:
                bad["required_behavior"][0].pop("implementation_ref")
            else:
                bad["required_behavior"][0]["implementation_ref"] = value
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "implementation_ref"),
            ):
                self.brief_module.CONTRACT.validate_unit_packet(plan, bad)
        plan["contracts"][0].pop("implementation_ref")
        packet["primary_plan_sha256"] = self.brief_module.CONTRACT.authority_fingerprint(plan)
        with self.assertRaisesRegex(ValueError, "implementation_ref"):
            self.brief_module.CONTRACT.validate_unit_packet(plan, packet)
