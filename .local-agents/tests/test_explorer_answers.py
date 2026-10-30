"""Typed claims stay model-owned; read provenance and boundaries stay trusted."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import test_explorer_runtime as helpers

RUNTIME = helpers.RUNTIME


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "module.py").write_text("def existing():\n    return 1\n", encoding="utf-8")
        self.runtime = RUNTIME.ExplorerRuntime(
            self.root,
            "In module.py only, does missing exist?",
            {"explorer_answer_protocol": True},
            helpers.FailIfCalledClient(),
        )

    def answer(self, state="absent_in_cited_ranges"):
        return {
            "question_id": "Q1",
            "answer_state": state,
            "unresolved_scope": "outside_cited_ranges_unknown",
            "source_refs": [
                {"path": "module.py", "start_line": 1, "end_line": 2, "kind": "definition"}
            ],
        }

    def test_list_and_search_do_not_authorize_unread_citations(self):
        self.runtime.list_files({})
        self.runtime.search({"query": "existing"})
        with self.assertRaisesRegex(RUNTIME.ExplorerError, "unread"):
            self.runtime.finish_success(self.answer())

    def test_typed_absence_does_not_invent_a_search_or_global_negative(self):
        self.runtime.read_file({"path": "module.py"})
        report = self.runtime.finish_success(self.answer())
        self.assertEqual(report["model_answer"]["answer_state"], "absent_in_cited_ranges")
        self.assertEqual(report["semantic_verdict"], "not_evaluated")
        self.assertEqual(report["execution_provenance"]["source_observation_method"], "READ_FILE")
        self.assertNotIn("SEARCH", json.dumps(report["findings"]))
        self.assertIn("other files/ranges remain unknown", report["uncertainties"][0])
        compact = RUNTIME.compact_explorer_report(report)
        self.assertEqual(compact["model_answer"], report["model_answer"])

    def test_unknown_ids_states_shapes_and_execution_narratives_rejected(self):
        self.runtime.read_file({"path": "module.py"})
        for field, value in (
            ("question_id", "Q2"),
            ("answer_state", "verified"),
            ("answer_state", []),
            ("unresolved_scope", []),
            ("unresolved_scope", "whole_repository_checked"),
        ):
            args = self.answer()
            args[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RUNTIME.ExplorerError):
                self.runtime.finish_success(args)
        for field in ("findings", "uncertainties", "search_history", "verified"):
            args = self.answer()
            args[field] = "SEARCH returned no matches"
            with self.subTest(field=field), self.assertRaises(RUNTIME.ExplorerError):
                self.runtime.finish_success(args)

    def test_drift_eof_hidden_and_line_budgets_keep_original_gates(self):
        self.runtime.read_file({"path": "module.py"})
        args = self.answer()
        args["source_refs"][0]["end_line"] = 3
        with self.assertRaisesRegex(RUNTIME.ExplorerError, "unread"):
            self.runtime.finish_success(args)
        args["source_refs"][0]["end_line"] = 200
        with self.assertRaisesRegex(RUNTIME.ExplorerError, "80 total"):
            self.runtime.finish_success(args)
        (self.root / "module.py").write_text("def missing():\n    return 1\n", encoding="utf-8")
        with self.assertRaisesRegex(RUNTIME.ExplorerError, "changed"):
            self.runtime.finish_success(self.answer())

    def test_unresolved_is_preserved_not_turned_into_answer(self):
        self.runtime.read_file({"path": "module.py"})
        args = self.answer("unresolved")
        with self.assertRaisesRegex(RUNTIME.ExplorerError, "unresolved"):
            self.runtime.finish_success(args)
        args["unresolved_scope"] = "additional_requested_evidence_unresolved"
        report = self.runtime.finish_success(args)
        self.assertEqual(report["model_answer"]["answer_state"], "unresolved")
        self.assertIn("remains unresolved", report["uncertainties"][0])

    def test_default_contract_unchanged_and_cache_namespaces_differ(self):
        old = RUNTIME.ExplorerRuntime(
            self.root, self.runtime.task, {}, helpers.FailIfCalledClient()
        )
        self.assertNotEqual(old.cache_task, self.runtime.cache_task)
        self.assertIn(
            "uncertainties", old.localization_tool()["function"]["parameters"]["properties"]
        )
        shape = self.runtime.localization_tool()["function"]["parameters"]
        self.assertEqual(
            set(shape["required"]),
            {"question_id", "source_refs", "answer_state", "unresolved_scope"},
        )
        self.assertFalse(shape["additionalProperties"])

    def test_fake_client_full_loop_retains_actual_answer_and_read_provenance(self):
        actions = [
            {"action": "READ_FILE", "path": "module.py"},
            {"action": "FINISH_SUCCESS", **self.answer()},
        ]

        class Client:
            def complete(self, messages):
                return json.dumps(actions.pop(0))

        runtime = RUNTIME.ExplorerRuntime(
            self.root,
            self.runtime.task,
            {"explorer_answer_protocol": True},
            Client(),
            "answer-counter",
        )
        report = runtime.run()
        self.assertEqual(report["status"], "success")
        self.assertEqual(
            [a["action"] for a in report["action_trace"]], ["READ_FILE", "FINISH_SUCCESS"]
        )
        self.assertEqual(report["model_answer"]["answer_state"], "absent_in_cited_ranges")

    def test_required_source_anchor_still_rejects_irrelevant_citation(self):
        self.runtime.read_file({"path": "module.py"})
        self.runtime.required_source_anchors = [{"path": "module.py", "text": "return 1"}]
        args = self.answer("located")
        args["source_refs"][0]["end_line"] = 1
        with self.assertRaisesRegex(RUNTIME.ExplorerError, "anchor"):
            self.runtime.finish_success(args)
