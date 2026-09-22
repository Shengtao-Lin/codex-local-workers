from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).resolve().parents[1] / "reviewer-runtime.py"
SPEC = importlib.util.spec_from_file_location("reviewer_runtime_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
REVIEWER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REVIEWER
SPEC.loader.exec_module(REVIEWER)


class FakeClient:
    def __init__(self, actions: list[dict]) -> None:
        self.actions = list(actions)

    def complete(self, _messages):
        return json.dumps(self.actions.pop(0))


class ReviewerRuntimeTests(unittest.TestCase):
    def make_run(self, root: Path, *, risk: str = "small") -> dict:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "example.py").write_text("VALUE = 2\n", encoding="utf-8")
        (root / "tests" / "test_example.py").write_text(
            "def test_value():\n    assert True\n", encoding="utf-8"
        )
        packet = {
            "schema_version": 2,
            "task_id": "task-1",
            "feature_id": "feature-1",
            "unit_id": "unit-1",
            "run_id": "run-1",
            "goal": "Change the value.",
            "risk": {
                "feature": "high",
                "unit": risk,
                "integration": "high",
                "reasons": ["Test risk routing."],
            },
            "scope": {
                "read": ["src", "tests"],
                "readonly": ["tests/test_example.py"],
                "modify": ["src/example.py"],
                "create": [],
                "forbidden": [],
            },
            "required_behavior": [{"id": "behavior-1", "text": "VALUE is two."}],
            "owned_contract_ids": ["behavior-1"],
            "acceptance_criteria": [{"id": "accept-1", "text": "Tests pass."}],
            "acceptance_scenarios": [{"id": "normal", "text": "Read VALUE."}],
            "focused_tests": ["tests/test_example.py"],
            "validation_profile": "python-focused",
        }
        run_root = root / ".agent" / "tasks" / "task-1" / "runs" / "run-1"
        run_root.mkdir(parents=True)
        (run_root / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
        (run_root / "handoff.json").write_text(
            json.dumps({"status": "ready_for_review", "worker_claims": {"summary": []}}),
            encoding="utf-8",
        )
        (run_root / "validation.json").write_text(
            json.dumps({"status": "passed", "focused_tests": {"status": "passed"}}),
            encoding="utf-8",
        )
        (run_root / "post-state.json").write_text(
            json.dumps({
                "validation_inputs": REVIEWER.RUN_STATE.facts_for_paths(
                    root, ["src/example.py", "tests/test_example.py"]
                )
            }),
            encoding="utf-8",
        )
        (run_root / "cumulative.diff").write_text(
            "--- a/src/example.py\n+++ b/src/example.py\n@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n",
            encoding="utf-8",
        )
        (run_root / "completed.json").write_text(
            json.dumps({"status": "ready_for_review"}), encoding="utf-8"
        )
        return {
            "schema_version": 1,
            "task_id": "task-1",
            "unit_id": "unit-1",
            "run_id": "run-1",
            "review_id": "review-1",
        }

    def test_pass_routes_small_unit_to_primary_evidence_acceptance(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            client = FakeClient([
                {
                    "action": "REPORT",
                    "arguments": {
                        "decision": "pass_to_primary",
                        "findings": [],
                        "verified_contract_ids": ["behavior-1"],
                        "unverified_claims": [],
                    },
                }
            ])
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "pass_to_primary")
            self.assertEqual(report["review_route"], "primary_evidence_acceptance")
            self.assertTrue(
                (root / ".agent" / "tasks" / "task-1" / "reviews" / "review-1" / "completed.json").is_file()
            )

    def test_reviewer_can_read_but_never_has_write_actions(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root, risk="medium")
            client = FakeClient([
                {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
                {
                    "action": "REPORT",
                    "arguments": {
                        "decision": "rework",
                        "findings": [{
                            "id": "finding-1",
                            "severity": "medium",
                            "category": "behavior",
                            "path": "src/example.py",
                            "line": 1,
                            "evidence": "VALUE is two without the requested guard.",
                            "contract_id": "behavior-1",
                            "suggested_fix": "Add the guard.",
                        }],
                        "verified_contract_ids": [],
                        "unverified_claims": [],
                    },
                },
            ])
            report = REVIEWER.ReviewerRuntime(root, request, {}, client).run()
            self.assertEqual(report["decision"], "rework")
            self.assertEqual(report["review_route"], "primary_lightweight_review")
            self.assertEqual(report["runtime_facts"]["read_paths"], ["src/example.py"])
            self.assertNotIn("SAFE_REPLACE", REVIEWER.REVIEW_ACTION_SCHEMA["properties"]["action"]["enum"])

    def test_none_placeholder_is_not_an_uncertainty(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            with self.assertRaisesRegex(REVIEWER.ReviewError, "must be an empty array"):
                runtime.validate_report({
                    "decision": "pass_to_primary",
                    "findings": [],
                    "verified_contract_ids": ["behavior-1"],
                    "unverified_claims": ["None"],
                })

    def test_default_search_aggregates_declared_read_roots(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            runtime = REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))
            result = runtime.search({"query": "VALUE", "glob": "*.py"})
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["results"][0]["path"], "src/example.py")

    def test_reviewer_rejects_inputs_changed_after_coder_run(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.make_run(root)
            (root / "src" / "example.py").write_text("VALUE = 3\n", encoding="utf-8")
            with self.assertRaisesRegex(REVIEWER.ReviewError, "inputs changed"):
                REVIEWER.ReviewerRuntime(root, request, {}, FakeClient([]))


if __name__ == "__main__":
    unittest.main()
