from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "real_task_eval.py"
SPEC = importlib.util.spec_from_file_location("real_task_eval_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
EVAL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EVAL
SPEC.loader.exec_module(EVAL)


START = "a" * 40
ACCEPTANCE = "b" * 64


def manifest() -> dict:
    return {
        "schema_version": 1,
        "tasks": [
            {
                "task_id": "real-01",
                "risk": "high",
                "category": "cross-unit",
                "start_commit": START,
                "acceptance_sha256": ACCEPTANCE,
            },
            {
                "task_id": "real-02",
                "risk": "medium",
                "category": "validation",
                "start_commit": START,
                "acceptance_sha256": ACCEPTANCE,
            },
        ],
    }


def record(task_id: str, arm: str, **changes: object) -> dict:
    item = {
        "task_id": task_id,
        "trial_id": 1,
        "arm": arm,
        "start_commit": START,
        "acceptance_sha256": ACCEPTANCE,
        "primary_model": "gpt-6-sol",
        "qualified_pass": True,
        "first_gate_pass": True,
        "wall_seconds": 60,
        "primary_tokens": None,
        "token_source": None,
    }
    item.update(changes)
    return item


class RealTaskEvalTests(unittest.TestCase):
    def write_inputs(self, root: Path, rows: list[dict]) -> tuple[Path, Path]:
        manifest_path = root / "manifest.json"
        records_path = root / "records.jsonl"
        manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
        records_path.write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )
        return manifest_path, records_path

    def test_paired_scorecard_counts_quality_and_only_measured_usage(self) -> None:
        with TemporaryDirectory() as directory:
            paths = self.write_inputs(
                Path(directory),
                [
                    record(
                        "real-01",
                        "primary",
                        primary_tokens=1000,
                        token_source="host-telemetry",
                        wall_seconds=60,
                    ),
                    record(
                        "real-01",
                        "local",
                        primary_tokens=600,
                        token_source="host-telemetry",
                        wall_seconds=100,
                        qualified_pass=False,
                        first_gate_pass=False,
                        coder_calls=3,
                        takeovers=1,
                        failure_categories=["contract-miss"],
                    ),
                    record("real-02", "primary", wall_seconds=80),
                ],
            )
            catalog = EVAL.load_manifest(paths[0])
            score = EVAL.summarize(EVAL.load_records(paths[1], catalog))
            self.assertEqual(score["paired_trials"], 1)
            self.assertEqual(score["unpaired_trials"][0]["missing_arm"], "local")
            self.assertEqual(score["risk_counts"], {"high": 1})
            self.assertEqual(score["local_qualified"], 0)
            self.assertEqual(score["quality_regressions"][0]["task_id"], "real-01")
            self.assertEqual(score["token_evidence"]["reduction_percent"], 40.0)
            self.assertEqual(score["token_evidence"]["measured_pairs"], 1)
            self.assertEqual(score["token_evidence"]["status"], "measured_all")
            self.assertEqual(score["local_worker_calls"]["takeovers"], 1)
            self.assertEqual(score["local_failure_categories"], {"contract-miss": 1})

    def test_missing_usage_never_becomes_an_estimated_saving(self) -> None:
        with TemporaryDirectory() as directory:
            paths = self.write_inputs(
                Path(directory),
                [
                    record(
                        "real-01",
                        "primary",
                        primary_tokens=1000,
                        token_source="host-telemetry",
                    ),
                    record("real-01", "local", coder_calls=2),
                ],
            )
            score = EVAL.summarize(
                EVAL.load_records(paths[1], EVAL.load_manifest(paths[0]))
            )
            self.assertEqual(score["token_evidence"]["status"], "unavailable")
            self.assertIsNone(score["token_evidence"]["reduction_percent"])

    def test_partial_token_coverage_is_explicit_and_cli_is_read_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.write_inputs(
                root,
                [
                    record(
                        "real-01",
                        "primary",
                        primary_tokens=1000,
                        token_source="host-telemetry",
                    ),
                    record(
                        "real-01",
                        "local",
                        primary_tokens=700,
                        token_source="host-telemetry",
                    ),
                    record("real-02", "primary"),
                    record("real-02", "local", coder_calls=1),
                ],
            )
            before = [path.read_bytes() for path in paths]
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--manifest",
                    str(paths[0]),
                    "--records",
                    str(paths[1]),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            score = json.loads(completed.stdout)
            self.assertEqual(score["paired_trials"], 2)
            self.assertEqual(score["token_evidence"]["measured_pairs"], 1)
            self.assertEqual(score["token_evidence"]["status"], "measured_subset")
            self.assertEqual([path.read_bytes() for path in paths], before)

    def test_mismatched_snapshot_duplicate_or_model_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.write_inputs(
                root,
                [
                    record("real-01", "primary", start_commit="c" * 40),
                ],
            )
            with self.assertRaisesRegex(EVAL.EvaluationError, "differs from manifest"):
                EVAL.load_records(paths[1], EVAL.load_manifest(paths[0]))
            paths = self.write_inputs(
                root,
                [
                    record("real-01", "primary"),
                    record("real-01", "primary"),
                ],
            )
            with self.assertRaisesRegex(EVAL.EvaluationError, "duplicate record"):
                EVAL.load_records(paths[1], EVAL.load_manifest(paths[0]))
            paths = self.write_inputs(
                root,
                [
                    record("real-01", "primary"),
                    record("real-01", "local", primary_model="gpt-6-luna"),
                ],
            )
            with self.assertRaisesRegex(
                EVAL.EvaluationError, "different Primary models"
            ):
                EVAL.summarize(
                    EVAL.load_records(paths[1], EVAL.load_manifest(paths[0]))
                )

    def test_bool_tokens_and_unattributed_tokens_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.write_inputs(
                root,
                [
                    record(
                        "real-01",
                        "primary",
                        primary_tokens=True,
                        token_source="host-telemetry",
                    ),
                ],
            )
            with self.assertRaisesRegex(EVAL.EvaluationError, "nonnegative integer"):
                EVAL.load_records(paths[1], EVAL.load_manifest(paths[0]))
            paths = self.write_inputs(
                root,
                [
                    record("real-01", "primary", primary_tokens=50),
                ],
            )
            with self.assertRaisesRegex(EVAL.EvaluationError, "need token_source"):
                EVAL.load_records(paths[1], EVAL.load_manifest(paths[0]))
            paths = self.write_inputs(
                root,
                [
                    record("real-01", "primary", wall_seconds=float("nan")),
                ],
            )
            with self.assertRaisesRegex(EVAL.EvaluationError, "finite and nonnegative"):
                EVAL.load_records(paths[1], EVAL.load_manifest(paths[0]))


if __name__ == "__main__":
    unittest.main()
