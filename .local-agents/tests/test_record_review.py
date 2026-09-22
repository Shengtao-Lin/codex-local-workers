from __future__ import annotations

import contextlib
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
    def test_accept_review_is_immutable_and_updates_primary_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run_root = root / ".agent" / "tasks" / "task-1" / "runs" / "run-1"
            run_root.mkdir(parents=True)
            (run_root / "completed.json").write_text(
                json.dumps({"status": "ready_for_review"}), encoding="utf-8"
            )
            (run_root / "handoff.json").write_text(
                json.dumps({
                    "identity": {"task_id": "task-1", "unit_id": "unit-1", "run_id": "run-1"}
                }),
                encoding="utf-8",
            )
            state_path = root / ".agent" / "tasks" / "task-1" / "state.json"
            state_path.write_text(
                json.dumps({
                    "task_id": "task-1",
                    "completed_units": [],
                    "reviews": [],
                    "open_issues": [],
                    "usage": {"coder_calls": 1, "explorer_calls": 0},
                    "recent_attempts": [{
                        "run_id": "run-1",
                        "unit_id": "unit-1",
                        "worker": "coder",
                        "result": "ready_for_review",
                        "progress": None,
                    }],
                }),
                encoding="utf-8",
            )
            argv = [
                "record-review.py",
                "--task-id", "task-1",
                "--run-id", "run-1",
                "--decision", "accept",
                "--summary", "Primary verified behavior and evidence.",
                "--repo", str(root),
            ]
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(REVIEW.main(), 0)
            review_bytes = (run_root / "review.json").read_bytes()
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["recent_attempts"][-1]["result"], "accepted")
            self.assertTrue(state["recent_attempts"][-1]["progress"])
            self.assertEqual(state["completed_units"][-1]["run_id"], "run-1")
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(REVIEW.main(), 2)
            self.assertEqual((run_root / "review.json").read_bytes(), review_bytes)


if __name__ == "__main__":
    unittest.main()
