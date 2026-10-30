from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks/system_convergence.py"
SPEC = importlib.util.spec_from_file_location("system_convergence_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
COLLECTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COLLECTOR
SPEC.loader.exec_module(COLLECTOR)


class SystemConvergenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.workspace = Path(self.directory.name)
        self.root = self.workspace / "fixtures/cell"
        self.root.mkdir(parents=True)
        self.ident = {"task_id": "task", "unit_id": "unit", "run_id": "run"}
        self.archive = ".agent/tasks/task/runs/run"
        self.source = self.root / "src/a.py"
        self.source.parent.mkdir()
        self.source.write_text("value = 1\n", encoding="utf-8")
        self.protected = self.root / "tests/test_a.py"
        self.protected.parent.mkdir()
        self.protected.write_text("assert True\n", encoding="utf-8")
        self.put(
            "coder",
            {
                "schema_version": 2,
                "status": "ready_for_review",
                "identity": self.ident,
                "protocol_error_count": 1,
            },
        )
        self.put("packet", {**self.ident, "schema_version": 2})
        self.put("completed", {"status": "ready_for_review"})
        self.put(
            "primary",
            {
                **self.ident,
                "decision": "accept",
                "worker_status": "ready_for_review",
                "local_review_id": "review",
            },
        )
        self.put(
            "post_state",
            {
                "validation_inputs": {
                    "src/a.py": {"exists": True, "sha256": COLLECTOR.sha256(self.source)},
                    "tests/test_a.py": {"exists": True, "sha256": COLLECTOR.sha256(self.protected)},
                }
            },
        )
        counts = {"tests": 2, "failures": 0, "errors": 0, "skipped": 0, "executed": 2}
        self.put(
            "validation",
            {
                "status": "passed",
                "focused_tests": {
                    "status": "passed",
                    "inputs_unchanged": True,
                    "junit": counts,
                },
                "configured_checks": [{"id": "lint", "status": "passed"}],
            },
        )
        self.put(
            "reviewer",
            {
                "decision": "pass_to_primary",
                "identity": {**self.ident, "review_id": "review"},
                "runtime_facts": {"protocol_error_count": 0, "inputs_unchanged": True},
            },
        )
        self.put(
            "compact",
            {
                "status": "ready_for_review",
                "identity": self.ident,
                "validation_summary": {"executed": 2},
            },
        )
        self.put("local_invocation", {"seconds": 12.5, "exit": 0})
        junit = self.root / self.archive / "junit.xml"
        junit.write_text(
            '<testsuites><testsuite><testcase name="a"/><testcase name="b"/>'
            "</testsuite></testsuites>",
            encoding="utf-8",
        )
        labels = (
            "coder",
            "packet",
            "completed",
            "primary",
            "post_state",
            "validation",
            "reviewer",
            "compact",
            "local_invocation",
        )
        self.cell = {
            "cell_id": "cell-1",
            "root": "fixtures/cell",
            "identity": self.ident,
            "artifacts": {
                label: COLLECTOR.ref(self.root, self.relative(label)) for label in labels
            },
            "protected_hashes": {"tests/test_a.py": COLLECTOR.sha256(self.protected)},
            "expected": {
                "coder_status": "ready_for_review",
                "primary_decision": "accept",
                "reviewer_outcome": "pass_to_primary",
            },
        }
        self.cell["artifacts"]["junit"] = COLLECTOR.ref(self.root, self.archive + "/junit.xml")

    def relative(self, label: str) -> str:
        return self.archive + "/" + label + ".json"

    def put(self, label: str, value: dict) -> None:
        path = self.root / self.relative(label)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def repin(self, label: str) -> None:
        self.cell["artifacts"][label] = COLLECTOR.ref(self.root, self.relative(label))

    def read(self, label: str) -> dict:
        return json.loads((self.root / self.relative(label)).read_text())

    def collect(self) -> dict:
        return COLLECTOR.collect_cell(self.workspace, self.cell)

    def test_success_uses_canonical_metrics_without_launch_or_source_writes(self) -> None:
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with (
            patch("subprocess.run", side_effect=AssertionError("no launch")),
            patch("urllib.request.urlopen", side_effect=AssertionError("no HTTP")),
        ):
            result = self.collect()
        self.assertEqual(result["collection_status"], "complete")
        self.assertEqual(result["coder_protocol_errors"], 1)
        self.assertTrue(result["historical_acceptance_evidence_eligible"])
        self.assertEqual(result["cost"]["local_unit_wall_seconds"], 12.5)
        self.assertIsNone(result["cost"]["loading_seconds"])
        self.assertIsNone(result["cost"]["primary_active_seconds"])
        self.assertIsNone(result["cost"]["cloud"]["primary_tokens"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_failed_coder_with_no_reviewer_is_retained(self) -> None:
        for label in ("coder", "completed", "compact"):
            value = self.read(label)
            value["status"] = "failed"
            self.put(label, value)
            self.repin(label)
        primary = self.read("primary")
        primary.update(decision="rework", worker_status="failed", local_review_id=None)
        self.put("primary", primary)
        self.repin("primary")
        validation = self.read("validation")
        validation["status"] = "failed"
        self.put("validation", validation)
        self.repin("validation")
        self.cell["artifacts"].pop("reviewer")
        self.cell["expected"] = {
            "coder_status": "failed",
            "primary_decision": "rework",
            "reviewer_outcome": "not_started",
        }
        result = self.collect()
        self.assertEqual(result["semantic_outcome"], "rework")
        self.assertEqual(result["reviewer_outcome"], "not_started")
        self.assertTrue(result["expected_matches"])
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_reviewer_rework_is_not_acceptance(self) -> None:
        review = self.read("reviewer")
        review["decision"] = "rework"
        self.put("reviewer", review)
        self.repin("reviewer")
        primary = self.read("primary")
        primary["decision"] = "rework"
        self.put("primary", primary)
        self.repin("primary")
        self.cell["expected"].update(primary_decision="rework", reviewer_outcome="rework")
        result = self.collect()
        self.assertEqual(result["reviewer_outcome"], "rework")
        self.assertTrue(result["expected_matches"])
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_infrastructure_failure_is_visible_and_cost_stays_unknown(self) -> None:
        coder = self.read("coder")
        coder["infra_failure"] = {"reason_code": "model_request_failed"}
        self.put("coder", coder)
        self.repin("coder")
        result = self.collect()
        self.assertIsNotNone(result["infra_failure"])
        self.assertIn("historical_infrastructure_failure", result["warnings"])
        self.assertEqual(result["cost"]["cloud"]["status"], "unknown")
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_missing_metric_does_not_erase_semantic_result(self) -> None:
        coder = self.read("coder")
        coder.pop("protocol_error_count")
        self.put("coder", coder)
        self.repin("coder")
        result = self.collect()
        self.assertEqual(result["primary_decision"], "accept")
        self.assertEqual(result["collection_status"], "complete")
        self.assertIsNone(result["coder_protocol_errors"])
        self.assertIn("coder_protocol_count_unknown", result["warnings"])

    def test_missing_required_record_preserves_other_facts_and_fails_closed(self) -> None:
        (self.root / self.relative("validation")).unlink()
        result = self.collect()
        self.assertEqual(result["primary_decision"], "accept")
        self.assertEqual(result["collection_status"], "incomplete")
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_truncated_json_is_not_replaced_by_compact_summary(self) -> None:
        path = self.root / self.relative("coder")
        path.write_text('{"status":', encoding="utf-8")
        self.repin("coder")
        result = self.collect()
        self.assertIn("invalid_json:coder", result["issues"])
        self.assertIsNone(result["coder_status"])
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_compact_reviewer_failure_is_not_labelled_not_started_or_accepted(self) -> None:
        self.cell["artifacts"].pop("reviewer")
        self.put("reviewer_compact", {"decision": "failed", "failure_reason": "two tool calls"})
        self.repin("reviewer_compact")
        result = self.collect()
        self.assertEqual(result["reviewer_outcome"], "failed")
        self.assertIn("canonical_reviewer_failure_binding_unavailable", result["issues"])
        self.assertEqual(result["collection_status"], "incomplete")
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_cross_run_identity_and_primary_review_binding_fail_closed(self) -> None:
        for kind in ("run", "review"):
            with self.subTest(kind=kind):
                cell = copy.deepcopy(self.cell)
                reviewer = self.read("reviewer")
                if kind == "run":
                    reviewer["identity"]["run_id"] = "other"
                else:
                    reviewer["identity"]["review_id"] = "other"
                self.put("reviewer", reviewer)
                self.repin("reviewer")
                result = self.collect()
                self.assertEqual(result["collection_status"], "incomplete")
                self.assertFalse(result["historical_acceptance_evidence_eligible"])
                self.cell = cell

    def test_changed_source_and_protected_input_invalidate_current_evidence(self) -> None:
        self.source.write_text("value = 2\n", encoding="utf-8")
        self.protected.write_text("assert False\n", encoding="utf-8")
        result = self.collect()
        self.assertFalse(result["validation_current"])
        self.assertFalse(result["protected_inputs_unchanged"])
        self.assertEqual(result["semantic_outcome"], "accept")
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_changed_archive_hash_is_rejected(self) -> None:
        primary = self.read("primary")
        primary["decision"] = "rework"
        self.put("primary", primary)
        result = self.collect()
        self.assertIn("hash_mismatch:primary", result["issues"])
        self.assertIsNone(result["primary_decision"])

    def test_junit_mismatch_and_all_skipped_cannot_prove_ready(self) -> None:
        path = self.root / self.cell["artifacts"]["junit"]["path"]
        path.write_text(
            '<testsuites><testsuite><testcase name="a"><skipped/>'
            "</testcase></testsuite></testsuites>",
            encoding="utf-8",
        )
        self.cell["artifacts"]["junit"] = COLLECTOR.ref(
            self.root, self.cell["artifacts"]["junit"]["path"]
        )
        result = self.collect()
        self.assertIn("runtime_junit_mismatch", result["issues"])
        self.assertEqual(result["actual_runtime_junit"]["executed"], 0)
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_output_is_exclusive_and_cannot_write_source_or_escape_workspace(self) -> None:
        output = "benchmarks/work/system-convergence/batch/result.json"
        COLLECTOR.write_output(self.workspace, output, {"worker_calls": 0})
        with self.assertRaisesRegex(COLLECTOR.CollectionError, "already exists"):
            COLLECTOR.write_output(self.workspace, output, {"worker_calls": 1})
        for path in (
            "fixtures/cell/source.json",
            "../escape.json",
            "C:/outside.json",
            "benchmarks/work/system-convergence/../../escape.json",
        ):
            with self.subTest(path=path), self.assertRaises(COLLECTOR.CollectionError):
                COLLECTOR.write_output(self.workspace, path, {})

    def test_failed_junit_cannot_pass_even_with_consistent_claimed_pass_status(self) -> None:
        junit = self.root / self.cell["artifacts"]["junit"]["path"]
        junit.write_text("<testsuite><testcase><failure/></testcase></testsuite>", encoding="utf-8")
        self.cell["artifacts"]["junit"] = COLLECTOR.ref(self.root, self.archive + "/junit.xml")
        validation = self.read("validation")
        validation["focused_tests"]["junit"] = COLLECTOR.junit_counts(junit)
        self.put("validation", validation)
        self.repin("validation")
        result = self.collect()
        self.assertIn("readiness_evidence_incomplete", result["issues"])
        self.assertFalse(result["historical_acceptance_evidence_eligible"])

    def test_aggregate_rejects_duplicate_cells_and_changed_registration_source(self) -> None:
        baseline = self.workspace / "baseline.json"
        baseline.write_text("{}", encoding="utf-8")
        registration = {
            "schema_version": 1,
            "worker_launch_allowed": False,
            "experiment_id": "test",
            "baseline": COLLECTOR.ref(self.workspace, "baseline.json"),
            "cells": [self.cell],
        }
        result = COLLECTOR.collect(self.workspace, registration)
        self.assertEqual(result["worker_calls"], 0)
        self.assertEqual(result["complete_cells"], 1)
        self.assertEqual(result["collector_sha256"], COLLECTOR.sha256(MODULE_PATH))
        registration["cells"].append(copy.deepcopy(self.cell))
        with self.assertRaisesRegex(COLLECTOR.CollectionError, "duplicate"):
            COLLECTOR.collect(self.workspace, registration)
        registration["cells"].pop()
        baseline.write_text('{"changed": true}', encoding="utf-8")
        with self.assertRaisesRegex(COLLECTOR.CollectionError, "source changed"):
            COLLECTOR.collect(self.workspace, registration)

    def test_validation_attempt_history_is_retained(self) -> None:
        label = "validation-attempt-1"
        self.put(label, {"status": "failed", "edit_revision": 1})
        self.repin(label)
        result = self.collect()
        self.assertEqual(
            result["validation_attempts"],
            [{"artifact": label, "status": "failed", "edit_revision": 1, "focused_tests": None}],
        )

    def test_reparse_flag_is_rejected_without_host_symlink_privileges(self) -> None:
        from types import SimpleNamespace

        with patch.object(
            Path, "lstat", return_value=SimpleNamespace(st_file_attributes=0x400, st_mode=0x8000)
        ):
            with self.assertRaisesRegex(COLLECTOR.CollectionError, "reparse"):
                COLLECTOR.inside(self.workspace, "fixtures/cell/src/a.py")

    def test_unknown_failed_stream_cost_remains_in_record(self) -> None:
        stream = self.root / "failed.jsonl"
        stream.write_text('{"type":"turn.failed"}\n', encoding="utf-8")
        result = COLLECTOR.token_evidence(stream)
        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["primary_tokens"])
        self.assertIn("failed turn", result["reason"])

    def test_real_usage_is_reused_and_invalid_numbers_are_unknown(self) -> None:
        stream = self.root / "usage.jsonl"
        stream.write_text(
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {"input_tokens": 12, "cached_input_tokens": 5, "output_tokens": 3},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = COLLECTOR.token_evidence(stream)
        self.assertEqual(result["primary_tokens"], 15)
        self.assertEqual(result["cached_input_tokens"], 5)
        for value in (True, -1, float("nan"), float("inf"), "3"):
            self.assertIsNone(COLLECTOR.nullable_number(value))

    def test_symlink_path_is_rejected(self) -> None:
        link = self.workspace / "link"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("host does not permit symlink creation")
        with self.assertRaises(COLLECTOR.CollectionError):
            COLLECTOR.inside(self.workspace, "link/src/a.py")


if __name__ == "__main__":
    unittest.main()
