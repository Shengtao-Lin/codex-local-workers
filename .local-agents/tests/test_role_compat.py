from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

MODULE_PATH = Path(__file__).parents[2] / "benchmarks" / "role_compat.py"
SPEC = importlib.util.spec_from_file_location("role_compat_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
COMPAT = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC.loader.exec_module(COMPAT)


class RoleCompatTests(unittest.TestCase):
    def test_finalized_deferred_report_counts_as_report_capability(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / ".agent"
            review_root = agent / "tasks" / "task" / "reviews" / "review"
            review_root.mkdir(parents=True)
            (review_root / "events.jsonl").write_text(
                json.dumps({"event": "deferred_report_finalized", "facts": {"turn": 3}}) + "\n",
                encoding="utf-8",
            )
            report = agent / "review.json"
            report.write_text(
                json.dumps(
                    {
                        "decision": "pass_to_primary",
                        "identity": {"task_id": "task", "review_id": "review"},
                    }
                ),
                encoding="utf-8",
            )
            result = COMPAT.evaluate(
                {
                    "workspace": str(root),
                    "review_report": str(report),
                    "reviewer_decision": "pass_to_primary",
                },
                {"reviewer_model": "muse"},
            )
            self.assertEqual(result["roles"]["reviewer"]["fixture_results"]["REPORT"], "pass")

    def test_action_coverage_counts_executed_validation_but_not_rejected_action(self) -> None:
        events = [
            {"event": "tool_action", "facts": {"action": "VALIDATE", "status": "failed"}},
            {"event": "tool_action", "facts": {"action": "SAFE_REPLACE", "status": "error"}},
            {"event": "diagnostic_action", "facts": {"action": "REPORT", "status": "error"}},
        ]
        self.assertEqual(COMPAT._event_actions(events), {"VALIDATE"})

    def test_evaluate_distinguishes_core_success_from_unexercised_actions(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / ".agent"
            agent.mkdir()
            (agent / "local-explore.py.report.json").write_text(
                json.dumps(
                    {
                        "status": "success",
                        "action_trace": [
                            {"action": "SEARCH"},
                            {"action": "READ_FILE"},
                            {"action": "FINISH_SUCCESS"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (agent / "last-local-coder-report.json").write_text(
                json.dumps({"status": "ready_for_review"}), encoding="utf-8"
            )
            review_root = agent / "tasks" / "task" / "reviews" / "review"
            review_root.mkdir(parents=True)
            (review_root / "events.jsonl").write_text(
                json.dumps(
                    {
                        "event": "diagnostic_action",
                        "facts": {"action": "READ_FILE", "status": "ok"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            review_report = agent / "review.json"
            review_report.write_text(
                json.dumps(
                    {
                        "decision": "pass_to_primary",
                        "identity": {"task_id": "task", "review_id": "review"},
                    }
                ),
                encoding="utf-8",
            )
            result = COMPAT.evaluate(
                {
                    "workspace": str(root),
                    "explorer_status": "success",
                    "coder_status": "ready_for_review",
                    "reviewer_decision": "pass_to_primary",
                    "review_report": str(review_report),
                    "independent_pytest_exit": 0,
                },
                {
                    "explorer_model": "e",
                    "coder_model": "c",
                    "reviewer_model": "r",
                },
            )
            self.assertEqual(result["roles"]["explorer"]["result"], "incomplete")
            self.assertEqual(
                result["roles"]["explorer"]["fixture_results"]["TRACE"], "not_exercised"
            )
            self.assertEqual(result["summary"]["compat_pass"], 0)
            self.assertEqual(result["summary"]["compat_incomplete"], 3)
            self.assertEqual(result["roles"]["reviewer"]["fixture_results"]["READ_FILE"], "pass")

    def test_store_writes_immutable_and_latest_results(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory)
            path = COMPAT.store({"protocol_version": "v1.2"}, output)
            self.assertTrue(path.is_file())
            self.assertEqual(
                json.loads((output / "latest.json").read_text())["protocol_version"], "v1.2"
            )

    def test_coder_http_400_is_infrastructure_not_worker_quality(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / ".agent"
            agent.mkdir()
            (agent / "local-explore.py.report.json").write_text(
                json.dumps({"status": "success"}), encoding="utf-8"
            )
            (agent / "last-local-coder-report.json").write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "failure_reason": "LM Studio request failed: HTTP Error 400: Bad Request",
                    }
                ),
                encoding="utf-8",
            )
            result = COMPAT.evaluate(
                {"workspace": str(root), "explorer_status": "success", "coder_status": "failed"},
                {"coder_model": "candidate"},
            )
            coder = result["roles"]["coder"]
            self.assertEqual(coder["result"], "infra_failure")
            self.assertEqual(coder["infra_failure"]["reason_code"], "model_server_http_400")
            self.assertEqual(result["summary"]["compat_infra_failure"], 1)
            self.assertEqual(result["summary"]["compat_fail"], 0)


if __name__ == "__main__":
    unittest.main()
