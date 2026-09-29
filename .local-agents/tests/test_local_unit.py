from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "local-unit.py"
SPEC = importlib.util.spec_from_file_location("local_unit_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
UNIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = UNIT
SPEC.loader.exec_module(UNIT)


class HandoffTests(unittest.TestCase):
    def test_reviewer_retry_is_bounded_to_transient_startup_failure(self) -> None:
        self.assertTrue(
            UNIT._retryable_reviewer_startup_failure(
                {
                    "decision": "failed",
                    "infra_failure": {
                        "reason_code": "http_4xx",
                        "reason": "The model produced output that does not match the expected peg-native format",
                    },
                }
            )
        )
        self.assertFalse(
            UNIT._retryable_reviewer_startup_failure(
                {
                    "decision": "failed",
                    "infra_failure": {"reason_code": "http_4xx", "reason": "bad request"},
                }
            )
        )

    def test_verified_handoff_retries_reviewer_with_new_identity_and_smaller_cap(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            coder_report, run_root = self.fixture(root)
            packet = root / "packet.json"
            config = root / "config.json"
            config.write_text(json.dumps({"reviewer_max_tokens": 4096}), encoding="utf-8")
            coder_path = root / "coder-report.json"
            review_path = root / "review-report.json"
            calls = []

            def fake_run(argv, **_kwargs):
                calls.append(argv)
                if len(calls) == 1:
                    coder_path.write_text(json.dumps(coder_report), encoding="utf-8")
                elif len(calls) == 2:
                    review_path.write_text(
                        json.dumps(
                            {
                                "decision": "failed",
                                "infra_failure": {
                                    "reason_code": "http_4xx",
                                    "reason": "expected peg-native format",
                                },
                            }
                        ),
                        encoding="utf-8",
                    )
                else:
                    review_path.write_text(
                        json.dumps({"decision": "pass_to_primary"}), encoding="utf-8"
                    )
                return Mock(returncode=0, stderr="")

            with patch.object(UNIT.subprocess, "run", side_effect=fake_run):
                code, result = UNIT.run_unit(root, packet, config, coder_path, review_path)
            self.assertEqual(code, 0)
            self.assertEqual(result["reviewer_decision"], "pass_to_primary")
            self.assertEqual(len(result["review_attempts"]), 2)
            self.assertNotEqual(
                result["review_attempts"][0]["review_id"],
                result["review_attempts"][1]["review_id"],
            )
            self.assertEqual(calls[2][-2:], ["--max-tokens", "2048"])
            self.assertTrue((run_root / "auto-review-retry-request.json").is_file())

    def fixture(self, root: Path) -> tuple[dict, Path]:
        source = root / "src" / "feature.py"
        source.parent.mkdir()
        source.write_text("VALUE = 2\n", encoding="utf-8")
        focused_test = root / "tests" / "test_feature.py"
        focused_test.parent.mkdir()
        focused_test.write_text("def test_value():\n    assert True\n", encoding="utf-8")
        run = root / ".agent" / "tasks" / "task" / "runs" / "run"
        run.mkdir(parents=True)
        documents = {
            "packet.json": {
                "task_id": "task",
                "unit_id": "unit",
                "run_id": "run",
                "scope": {
                    "read": ["src/feature.py", "tests/test_feature.py"],
                    "modify": ["src/feature.py"],
                    "create": [],
                    "forbidden": [],
                },
                "focused_tests": ["tests/test_feature.py"],
            },
            "completed.json": {"status": "ready_for_review"},
            "handoff.json": {
                "status": "ready_for_review",
                "changed_files": [{"path": "src/feature.py"}],
            },
            "validation.json": {
                "status": "passed",
                "focused_tests": {
                    "status": "passed",
                    "inputs_unchanged": True,
                    "junit": {"available": True, "executed": 1},
                },
                "configured_checks": [{"id": "lint", "status": "passed"}],
            },
            "changes.json": {
                "runtime_edits": [{"path": "src/feature.py"}],
                "unattributed_relevant_changes": [],
            },
            "post-state.json": {
                "validation_inputs": {
                    "src/feature.py": {
                        "exists": True,
                        "kind": "file",
                        "sha256": UNIT.hashlib.sha256(source.read_bytes()).hexdigest(),
                    },
                    "tests/test_feature.py": {
                        "exists": True,
                        "kind": "file",
                        "sha256": UNIT.hashlib.sha256(focused_test.read_bytes()).hexdigest(),
                    },
                }
            },
        }
        for name, value in documents.items():
            (run / name).write_text(json.dumps(value), encoding="utf-8")
        preimage = b"VALUE = 1\n"
        archived_source = run / "preimages" / "src" / "feature.py"
        archived_source.parent.mkdir(parents=True)
        archived_source.write_bytes(preimage)
        (run / "preimages.json").write_text(
            json.dumps(
                [
                    {
                        "path": "src/feature.py",
                        "existed": True,
                        "sha256": UNIT.hashlib.sha256(preimage).hexdigest(),
                    }
                ]
            ),
            encoding="utf-8",
        )
        (run / "cumulative.diff").write_text(
            "--- a/src/feature.py\n+++ b/src/feature.py\n@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n",
            encoding="utf-8",
        )
        report = {
            "status": "ready_for_review",
            "identity": {"task_id": "task", "unit_id": "unit", "run_id": "run"},
        }
        return report, run

    def test_verified_archive_can_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, _run = self.fixture(root)
            self.assertEqual(
                UNIT.verify_handoff(root, report),
                {"task_id": "task", "unit_id": "unit", "run_id": "run"},
            )

    def test_unscoped_manifest_in_cumulative_diff_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            with (run / "cumulative.diff").open("a", encoding="utf-8") as stream:
                stream.write(
                    "--- a/pyproject.toml\n+++ b/pyproject.toml\n@@ -1 +1 @@\n-old\n+new\n"
                )
            with self.assertRaisesRegex(UNIT.HandoffError, "diff paths differ"):
                UNIT.verify_handoff(root, report)

    def test_new_local_import_outside_packet_read_scope_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            source = root / "src" / "feature.py"
            source.write_text("import secret\nVALUE = 2\n", encoding="utf-8")
            (root / "src" / "secret.py").write_text("TOKEN = 1\n", encoding="utf-8")
            post = json.loads((run / "post-state.json").read_text(encoding="utf-8"))
            post["validation_inputs"]["src/feature.py"]["sha256"] = UNIT.hashlib.sha256(
                source.read_bytes()
            ).hexdigest()
            (run / "post-state.json").write_text(json.dumps(post), encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "imports out-of-scope"):
                UNIT.verify_handoff(root, report)

    def test_new_local_import_within_read_scope_can_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            source = root / "src" / "feature.py"
            source.write_text("import helper\nVALUE = 2\n", encoding="utf-8")
            (root / "src" / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
            packet = json.loads((run / "packet.json").read_text(encoding="utf-8"))
            packet["scope"]["read"].append("src/helper.py")
            (run / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
            post = json.loads((run / "post-state.json").read_text(encoding="utf-8"))
            post["validation_inputs"]["src/feature.py"]["sha256"] = UNIT.hashlib.sha256(
                source.read_bytes()
            ).hexdigest()
            (run / "post-state.json").write_text(json.dumps(post), encoding="utf-8")
            self.assertEqual(UNIT.verify_handoff(root, report)["unit_id"], "unit")

    def test_verified_node_selector_requires_recorded_execution(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            selector = "tests/test_feature.py::test_value"
            packet = json.loads((run / "packet.json").read_text(encoding="utf-8"))
            packet["focused_tests"] = [selector]
            (run / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
            validation = json.loads((run / "validation.json").read_text(encoding="utf-8"))
            validation["focused_tests"]["argv"] = ["python", "-m", "pytest", selector]
            (run / "validation.json").write_text(json.dumps(validation), encoding="utf-8")
            self.assertEqual(UNIT.verify_handoff(root, report)["unit_id"], "unit")

            validation["focused_tests"]["argv"][-1] = "tests/test_feature.py::different_test"
            (run / "validation.json").write_text(json.dumps(validation), encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "focused tests are missing"):
                UNIT.verify_handoff(root, report)

    def test_changed_input_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, _run = self.fixture(root)
            (root / "src" / "feature.py").write_text("VALUE = 3\n", encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "changed after Coder"):
                UNIT.verify_handoff(root, report)

    def test_unattributed_change_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            changes = json.loads((run / "changes.json").read_text(encoding="utf-8"))
            changes["unattributed_relevant_changes"] = ["src/other.py"]
            (run / "changes.json").write_text(json.dumps(changes), encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "unattributed"):
                UNIT.verify_handoff(root, report)

    def test_failed_configured_check_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            validation = json.loads((run / "validation.json").read_text(encoding="utf-8"))
            validation["configured_checks"][0]["status"] = "failed"
            (run / "validation.json").write_text(json.dumps(validation), encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "validation is incomplete"):
                UNIT.verify_handoff(root, report)

    def test_boolean_executed_count_does_not_fake_one_test(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            validation = json.loads((run / "validation.json").read_text(encoding="utf-8"))
            validation["focused_tests"]["junit"]["executed"] = True
            (run / "validation.json").write_text(json.dumps(validation), encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "validation is incomplete"):
                UNIT.verify_handoff(root, report)

    def test_focused_test_absent_from_snapshot_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            snapshot = json.loads((run / "post-state.json").read_text(encoding="utf-8"))
            del snapshot["validation_inputs"]["tests/test_feature.py"]
            (run / "post-state.json").write_text(json.dumps(snapshot), encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "focused tests are missing"):
                UNIT.verify_handoff(root, report)

    def test_empty_diff_for_reported_edit_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            (run / "cumulative.diff").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "cumulative diff is missing"):
                UNIT.verify_handoff(root, report)

    def test_changed_focused_test_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, _run = self.fixture(root)
            (root / "tests" / "test_feature.py").write_text(
                "def test_value(): pass\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(UNIT.HandoffError, "changed after Coder"):
                UNIT.verify_handoff(root, report)

    def test_changed_path_outside_scope_cannot_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, run = self.fixture(root)
            handoff = json.loads((run / "handoff.json").read_text(encoding="utf-8"))
            handoff["changed_files"] = [{"path": "src/other.py"}]
            (run / "handoff.json").write_text(json.dumps(handoff), encoding="utf-8")
            with self.assertRaisesRegex(UNIT.HandoffError, "not fully attributed"):
                UNIT.verify_handoff(root, report)

    def test_stale_convenience_report_cannot_trigger_reviewer(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            report, _run = self.fixture(root)
            coder_report = root / "coder-report.json"
            coder_report.write_text(json.dumps(report), encoding="utf-8")
            mocked = Mock(return_value=Mock(returncode=0, stderr=""))
            with patch.object(UNIT.subprocess, "run", mocked):
                code, result = UNIT.run_unit(
                    root,
                    root / "packet.json",
                    root / "config.json",
                    coder_report,
                    root / "review-report.json",
                )
            self.assertEqual(code, 2)
            self.assertEqual(result["stage"], "coder_report")
            self.assertEqual(mocked.call_count, 1)


if __name__ == "__main__":
    unittest.main()
