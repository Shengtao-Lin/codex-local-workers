from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "record-review.py"
SPEC = importlib.util.spec_from_file_location("record_review_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
REVIEW = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REVIEW
SPEC.loader.exec_module(REVIEW)


class RecordReviewTests(unittest.TestCase):
    def test_primary_disposition_cli_enforces_rework_and_preserves_acceptance_gate(self):
        cases = [
            (None, "rework", 2),
            ("confirmed_defect", "rework", 0),
            ("contract_revision", "rework", 2),
            ("contract_revision", "replan", 0),
            ("nonblocking", "accept", 2),
            ("stale", "rework", 2),
            ("stale_source", "rework", 2),
        ]
        for kind, decision, expected in cases:
            with self.subTest(kind=kind, decision=decision), TemporaryDirectory() as directory:
                root = Path(directory)
                task = root / ".agent/tasks/t"
                run = task / "runs/r"
                archive = task / "reviews/v"
                run.mkdir(parents=True)
                archive.mkdir(parents=True)
                source = root / "source.py"
                source.write_text("VALUE = 2\n", encoding="utf-8")
                identity = {"task_id": "t", "unit_id": "u", "run_id": "r"}
                documents = {
                    run / "completed.json": {"status": "ready_for_review"},
                    run / "handoff.json": {
                        "identity": identity,
                        "next_action_required": "local_review",
                    },
                    task / "state.json": {
                        "reviews": [],
                        "completed_units": [],
                        "recent_attempts": [],
                    },
                    archive / "completed.json": {"decision": "rework"},
                    archive / "handoff.json": {
                        "identity": {**identity, "review_id": "v"},
                        "decision": "rework",
                        "findings": [{"id": "f"}],
                        "runtime_facts": {
                            "observed_read_hashes": {
                                "source.py": hashlib.sha256(source.read_bytes()).hexdigest()
                            }
                        },
                    },
                }
                for path, data in documents.items():
                    path.write_text(json.dumps(data), encoding="utf-8")
                original = (archive / "handoff.json").read_bytes()
                argv = [
                    "record-review.py",
                    "--repo",
                    str(root),
                    "--task-id",
                    "t",
                    "--run-id",
                    "r",
                    "--decision",
                    decision,
                    "--summary",
                    "Primary inspected evidence",
                ]
                if kind:
                    payload = {
                        "schema_version": 1,
                        "authority": "primary",
                        "identity": {**identity, "review_id": "v"},
                        "report_sha256": hashlib.sha256(original).hexdigest()
                        if kind != "stale"
                        else "wrong",
                        "resolution": "cleared",
                        "evidence": ["Independent source/test evidence"],
                        "findings": [
                            {
                                "finding_id": "f",
                                "disposition": "confirmed_defect"
                                if kind in {"stale", "stale_source"}
                                else kind,
                                "evidence": "Concrete inspected evidence",
                            }
                        ],
                    }
                    path = root / "disposition.json"
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    argv.extend(["--disposition", str(path)])
                    if kind == "stale_source":
                        source.write_text("VALUE = 3\n", encoding="utf-8")
                with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(REVIEW.main(), expected)
                self.assertEqual((archive / "handoff.json").read_bytes(), original)
                self.assertEqual((run / "review.json").exists(), expected == 0)
                if expected == 0:
                    saved = json.loads((run / "review.json").read_text(encoding="utf-8"))
                    self.assertEqual(
                        saved["review_disposition"]["report_sha256"],
                        hashlib.sha256(original).hexdigest(),
                    )

    def test_accept_requires_local_review_for_new_routed_runs(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run_root = root / ".agent" / "tasks" / "task-1" / "runs" / "run-1"
            run_root.mkdir(parents=True)
            (run_root / "completed.json").write_text(
                json.dumps({"status": "ready_for_review"}), encoding="utf-8"
            )
            (run_root / "handoff.json").write_text(
                json.dumps(
                    {
                        "identity": {"task_id": "task-1", "unit_id": "unit-1", "run_id": "run-1"},
                        "next_action_required": "local_review",
                    }
                ),
                encoding="utf-8",
            )
            state_path = root / ".agent" / "tasks" / "task-1" / "state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "task_id": "task-1",
                        "reviews": [],
                        "completed_units": [],
                        "recent_attempts": [],
                    }
                ),
                encoding="utf-8",
            )
            argv = [
                "record-review.py",
                "--task-id",
                "task-1",
                "--run-id",
                "run-1",
                "--decision",
                "accept",
                "--summary",
                "No local review yet.",
                "--repo",
                str(root),
            ]
            output = io.StringIO()
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
                self.assertEqual(REVIEW.main(), 2)
            self.assertIn("requires a passing Local Reviewer", output.getvalue())
            self.assertFalse((run_root / "review.json").exists())

    def test_accept_review_is_immutable_and_updates_primary_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "example.py").write_text("VALUE = 2\n", encoding="utf-8")
            run_root = root / ".agent" / "tasks" / "task-1" / "runs" / "run-1"
            run_root.mkdir(parents=True)
            (run_root / "completed.json").write_text(
                json.dumps({"status": "ready_for_review"}), encoding="utf-8"
            )
            (run_root / "handoff.json").write_text(
                json.dumps(
                    {
                        "identity": {"task_id": "task-1", "unit_id": "unit-1", "run_id": "run-1"},
                        "next_action_required": "local_review",
                        "changed_files": [{"path": "src/example.py"}],
                    }
                ),
                encoding="utf-8",
            )
            local_review_root = root / ".agent" / "tasks" / "task-1" / "reviews" / "review-1"
            local_review_root.mkdir(parents=True)
            (local_review_root / "handoff.json").write_text(
                json.dumps(
                    {
                        "decision": "pass_to_primary",
                        "identity": {
                            "task_id": "task-1",
                            "unit_id": "unit-1",
                            "run_id": "run-1",
                            "review_id": "review-1",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (local_review_root / "completed.json").write_text(
                json.dumps({"decision": "pass_to_primary"}), encoding="utf-8"
            )
            state_path = root / ".agent" / "tasks" / "task-1" / "state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "task_id": "task-1",
                        "completed_units": [],
                        "reviews": [],
                        "open_issues": [],
                        "usage": {"coder_calls": 1, "explorer_calls": 0},
                        "recent_attempts": [
                            {
                                "run_id": "run-1",
                                "unit_id": "unit-1",
                                "worker": "coder",
                                "result": "ready_for_review",
                                "progress": None,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            argv = [
                "record-review.py",
                "--task-id",
                "task-1",
                "--run-id",
                "run-1",
                "--decision",
                "accept",
                "--summary",
                "Primary verified behavior and evidence.",
                "--repo",
                str(root),
            ]
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(REVIEW.main(), 0)
            review_bytes = (run_root / "review.json").read_bytes()
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["recent_attempts"][-1]["result"], "accepted")
            self.assertTrue(state["recent_attempts"][-1]["progress"])
            self.assertEqual(state["recent_attempts"][-1]["worker"], "primary")
            self.assertEqual(state["completed_units"][-1]["run_id"], "run-1")
            review = json.loads((run_root / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(review["local_review_id"], "review-1")
            map_data = json.loads((root / ".agent" / "repo-map.json").read_text(encoding="utf-8"))
            self.assertEqual(map_data["accepted_changes"][0]["path"], "src/example.py")
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(REVIEW.main(), 2)
            self.assertEqual((run_root / "review.json").read_bytes(), review_bytes)


if __name__ == "__main__":
    unittest.main()
