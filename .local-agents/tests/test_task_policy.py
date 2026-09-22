from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "task-policy.py"
SPEC = importlib.util.spec_from_file_location("task_policy_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
POLICY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = POLICY
SPEC.loader.exec_module(POLICY)


def attempt(
    result: str,
    *,
    signature: str | None = None,
    progress: bool = False,
    worker: str = "coder",
    unit_id: str = "step-1",
    severity: str | None = None,
) -> dict:
    return {
        "worker": worker,
        "unit_id": unit_id,
        "result": result,
        "failure_signature": signature,
        "progress": progress,
        "severity": severity,
    }


class TaskPolicyTests(unittest.TestCase):
    def test_many_successful_steps_do_not_trigger_fallback(self) -> None:
        state = {"recent_attempts": [attempt("success", unit_id=f"step-{index}") for index in range(20)]}
        self.assertEqual(POLICY.evaluate_task_state(state)["decision"], "continue")

    def test_same_failure_three_times_triggers_fallback(self) -> None:
        state = {"recent_attempts": [attempt("failed", signature="pytest:assertion") for _ in range(3)]}
        result = POLICY.evaluate_task_state(state)
        self.assertEqual(result["decision"], "fallback_primary")
        self.assertEqual(result["streaks"]["same_failure"], 3)

    def test_different_failure_signature_does_not_continue_old_streak(self) -> None:
        state = {"recent_attempts": [
            attempt("failed", signature="compile:syntax"),
            attempt("failed", signature="compile:syntax"),
            attempt("failed", signature="pytest:assertion"),
        ]}
        result = POLICY.evaluate_task_state(state)
        self.assertEqual(result["decision"], "fallback_primary")
        self.assertEqual(result["streaks"]["same_failure"], 1)
        self.assertEqual(result["streaks"]["no_progress"], 3)

    def test_material_progress_resets_failure_streaks(self) -> None:
        state = {"recent_attempts": [
            attempt("failed", signature="pytest:assertion"),
            attempt("failed", signature="pytest:assertion"),
            attempt("partial", signature="pytest:assertion", progress=True),
        ]}
        result = POLICY.evaluate_task_state(state)
        self.assertEqual(result["decision"], "continue")

    def test_repeated_coder_quality_failure_triggers_takeover(self) -> None:
        state = {"recent_attempts": [attempt("quality_failed") for _ in range(3)]}
        self.assertEqual(POLICY.evaluate_task_state(state)["decision"], "takeover")

    def test_unsafe_result_triggers_immediate_takeover(self) -> None:
        state = {"recent_attempts": [attempt("failed", severity="unsafe")]}
        self.assertEqual(POLICY.evaluate_task_state(state)["decision"], "takeover")

    def test_ready_for_review_routes_to_local_reviewer_without_counting_failure(self) -> None:
        state = {"recent_attempts": [
            attempt("failed", signature="pytest:assertion"),
            attempt("failed", signature="pytest:assertion"),
            attempt("ready_for_review"),
        ]}
        self.assertEqual(POLICY.evaluate_task_state(state)["decision"], "local_review")

    def test_reviewer_pass_uses_recorded_risk_route(self) -> None:
        item = attempt("pass_to_primary")
        item.update({
            "worker": "reviewer",
            "review_route": "primary_lightweight_review",
        })
        state = {"recent_attempts": [item]}
        self.assertEqual(
            POLICY.evaluate_task_state(state)["decision"],
            "primary_lightweight_review",
        )

    def test_reviewer_findings_route_to_bounded_rework(self) -> None:
        item = attempt("rework")
        item["worker"] = "reviewer"
        state = {"recent_attempts": [item]}
        self.assertEqual(
            POLICY.evaluate_task_state(state)["decision"], "bounded_coder_rework"
        )

    def test_runtime_policy_violation_triggers_takeover(self) -> None:
        state = {"recent_attempts": [attempt("policy_violation")]}
        self.assertEqual(POLICY.evaluate_task_state(state)["decision"], "takeover")


if __name__ == "__main__":
    unittest.main()
