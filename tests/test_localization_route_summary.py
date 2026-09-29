from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "localization_route_summary.py"
SPEC = importlib.util.spec_from_file_location("localization_route_summary", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUMMARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_failed_explorer_stays_in_denominator_and_versions_cannot_mix() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        failed = {
            "workspace": str(root / "failed"),
            "case": "metadata-limit",
            "unknown_location": True,
            "question_version": 2,
            "baseline_failed": True,
            "explorer_evidence_valid": False,
            "explorer_infra_failure": None,
            "qualified_pass": False,
            "route": None,
        }
        passed = {
            **failed,
            "workspace": str(root / "passed"),
            "case": "selection-order",
            "explorer_evidence_valid": True,
            "qualified_pass": True,
            "route": {
                "unit_result": {
                    "status": "ready_for_review",
                    "reviewer_decision": "pass_to_primary",
                    "review_attempts": [{"decision": "pass_to_primary", "infra_failure": None}],
                }
            },
        }
        summary = SUMMARY.summarize([failed, passed], question_version=2)
        assert summary["attempts"] == 2
        assert summary["counts"]["explorer_valid"] == 1
        assert summary["counts"]["e2e_first_pass"] == 1
        assert summary["counts"]["explicit_infra_failure"] == 0
        with pytest.raises(ValueError, match="question versions"):
            SUMMARY.summarize([failed, {**passed, "question_version": 1}], question_version=2)
        with pytest.raises(ValueError, match="duplicate frozen workspace"):
            SUMMARY.summarize([failed, failed], question_version=2)


def test_rework_pass_is_separate_from_initial_failure() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        task_root = root / ".agent" / "tasks" / "stability-sample-identity"
        run = task_root / "runs" / "sample-identity-a2"
        write_json(
            run / "packet.json",
            {
                "task_id": "stability-sample-identity",
                "unit_id": "sample-identity",
                "run_id": "sample-identity-a2",
                "attempt": 2,
            },
        )
        write_json(run / "completed.json", {"status": "ready_for_review"})
        write_json(run / "auto-review-request.json", {"review_id": "auto-example"})
        write_json(
            task_root / "reviews" / "auto-example" / "handoff.json",
            {
                "identity": {
                    "task_id": "stability-sample-identity",
                    "unit_id": "sample-identity",
                    "run_id": "sample-identity-a2",
                    "review_id": "auto-example",
                },
                "decision": "pass_to_primary",
            },
        )
        item = {
            "workspace": str(root),
            "case": "sample-identity",
            "unknown_location": True,
            "question_version": 2,
            "baseline_failed": True,
            "explorer_evidence_valid": True,
            "qualified_pass": False,
            "route": {"unit_result": {"status": "failed", "reviewer_decision": None}},
        }
        summary = SUMMARY.summarize([item], question_version=2)
        assert summary["counts"]["e2e_first_pass"] == 0
        assert summary["counts"]["rework_coder_calls"] == 1
        assert summary["counts"]["rework_reviewer_pass"] == 1
        assert summary["counts"]["rework_units_with_reviewer_pass"] == 1
