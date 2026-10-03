from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "benchmarks" / "localization_route_summary.py"
)
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
                    "review_attempts": [
                        {"decision": "pass_to_primary", "infra_failure": None}
                    ],
                }
            },
        }
        summary = SUMMARY.summarize([failed, passed], question_version=2)
        assert summary["attempts"] == 2
        assert summary["counts"]["explorer_valid"] == 1
        assert summary["counts"]["e2e_first_pass"] == 1
        assert summary["counts"]["explicit_infra_failure"] == 0
        with pytest.raises(ValueError, match="question versions"):
            SUMMARY.summarize(
                [failed, {**passed, "question_version": 1}], question_version=2
            )
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


def test_strict_summary_rejects_mixed_or_changed_runtime_and_case_inputs(
    tmp_path: Path,
) -> None:
    manifest = {"schema_version": 1, "files": {"worker.py": "a" * 64}}
    provenance = {
        "runtime_manifest": manifest,
        "runtime_sha256": SUMMARY.manifest_hash(manifest),
        "case_input_sha256": "b" * 64,
    }
    first = {
        "workspace": str(tmp_path / "round-one"),
        "case": "example",
        "unknown_location": True,
        "question_version": 2,
        "baseline_failed": True,
        "explorer_evidence_valid": False,
        "qualified_pass": False,
        "route": None,
        "provenance": provenance,
        "runtime_changed_during_run": False,
    }
    second = {**first, "workspace": str(tmp_path / "round-two")}
    summary = SUMMARY.summarize(
        [first, second], question_version=2, require_frozen_manifest=True
    )
    assert summary["frozen_manifest_checked"] is True
    assert summary["runtime_sha256"] == provenance["runtime_sha256"]
    with pytest.raises(ValueError, match="requires provenance"):
        SUMMARY.summarize(
            [first, {**second, "provenance": None}],
            question_version=2,
            require_frozen_manifest=True,
        )
    changed_manifest = {"schema_version": 1, "files": {"worker.py": "c" * 64}}
    with pytest.raises(ValueError, match="mixes runtime"):
        SUMMARY.summarize(
            [
                first,
                {
                    **second,
                    "provenance": {
                        **provenance,
                        "runtime_manifest": changed_manifest,
                        "runtime_sha256": SUMMARY.manifest_hash(changed_manifest),
                    },
                },
            ],
            question_version=2,
            require_frozen_manifest=True,
        )
    with pytest.raises(ValueError, match="changes the input"):
        SUMMARY.summarize(
            [
                first,
                {**second, "provenance": {**provenance, "case_input_sha256": "d" * 64}},
            ],
            question_version=2,
            require_frozen_manifest=True,
        )
    with pytest.raises(ValueError, match="incomplete or changed"):
        SUMMARY.summarize(
            [first, {**second, "runtime_changed_during_run": True}],
            question_version=2,
            require_frozen_manifest=True,
        )
