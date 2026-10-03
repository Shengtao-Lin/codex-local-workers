from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "stability_e2e.py"
SPEC = importlib.util.spec_from_file_location("stability_e2e_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
STABILITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STABILITY
SPEC.loader.exec_module(STABILITY)


def test_localization_requires_actual_faulty_branch_not_just_correct_file():
    case = STABILITY.CASES[0]
    report = {
        "explorer_mode": "locate",
        "semantic_verdict": "not_evaluated",
        "source_refs": [
            {"path": case.target, "kind": "implementation", "quote": "import random"},
            {
                "path": "tests/test_selection_order.py",
                "kind": "test",
                "quote": "assert result == expected",
            },
        ],
    }
    assert not STABILITY.explorer_has_line_evidence(
        report, case, "tests/test_selection_order.py"
    )
    report["source_refs"][0]["quote"] = case.after
    assert STABILITY.explorer_has_line_evidence(
        report, case, "tests/test_selection_order.py"
    )
    report["source_refs"][1]["quote"] = "import pytest"
    assert not STABILITY.explorer_has_line_evidence(
        report, case, "tests/test_selection_order.py"
    )


def test_localization_accepts_exact_faulty_constant_definition() -> None:
    case = next(case for case in STABILITY.CASES if case.name == "metadata-limit")
    report = {
        "explorer_mode": "locate",
        "semantic_verdict": "not_evaluated",
        "source_refs": [
            {"path": case.target, "kind": "definition", "quote": case.after},
            {
                "path": "tests/test_metadata_limit.py",
                "kind": "test",
                "quote": "assert MAX_METADATA_BYTES == 16_384",
            },
        ],
    }
    assert STABILITY.explorer_has_line_evidence(
        report, case, "tests/test_metadata_limit.py"
    )
    report["source_refs"][0]["quote"] = "MAX_METADATA_BYTES = 16_384"
    assert not STABILITY.explorer_has_line_evidence(
        report, case, "tests/test_metadata_limit.py"
    )


def test_localization_task_does_not_ask_for_execution_prediction():
    question = STABILITY.explorer_task(
        STABILITY.CASES[0], "tests/test_selection_order.py", "locate"
    )
    assert "source_refs" in question
    assert "source-predicted result" not in question
    assert "source-predicted result" in STABILITY.explorer_task(
        STABILITY.CASES[0], "tests/test_selection_order.py"
    )


def test_localization_distinguishes_required_targets_from_context():
    case = next(case for case in STABILITY.CASES if case.name == "sample-identity")
    question = STABILITY.explorer_task(case, "tests/test_sample_identity.py", "locate")
    assert "Other source reads are context, not mandatory references" in question
    required = question.split("including these implementation files: ")[1].split(
        ". Other"
    )[0]
    assert case.target in required
    assert all(mutation.target in required for mutation in case.extra_mutations)
    assert "canonical/models.py" not in required


def test_role_aligned_early_stop_uses_best_possible_remaining_outcomes() -> None:
    good = {
        "explorer_status": "success",
        "explorer_evidence_valid": True,
        "qualified_pass": True,
    }
    bad_explorer = {
        "explorer_status": "failed",
        "explorer_evidence_valid": False,
        "qualified_pass": False,
    }
    assert (
        STABILITY.unreachable_role_aligned_gate(
            [good, good, bad_explorer, bad_explorer], 22
        )
        is None
    )
    assert (
        STABILITY.unreachable_role_aligned_gate(
            [good, good, bad_explorer, bad_explorer, bad_explorer], 22
        )
        == "Explorer evidence can reach at most 19/22"
    )
    bad_coder = {**good, "qualified_pass": False}
    assert (
        STABILITY.unreachable_role_aligned_gate(
            [good, good, bad_coder, bad_coder, bad_coder], 22
        )
        == "protocol E2E can reach at most 19/22"
    )


def test_sample_identity_explorer_question_checks_actual_dump_fields() -> None:
    case = next(case for case in STABILITY.CASES if case.name == "sample-identity")
    task = STABILITY.explorer_task(case, "tests/test_sample_identity.py")
    assert "READ_FILE src/evaluation_harness/canonical/models.py" in task
    assert "actually exclude sample_id" in task
    assert "VOLATILE_CONTENT_FIELDS constant is not proof" in task
    assert "source prediction, test expectation" in task
    assert "For each distinct focused assertion" in task
    assert "include boundary and error cases" in task
    assert "full path followed by line N" in task
    assert "observed test path in relevant_tests" in task
    assert "Trace past an outer type guard" in task


def test_static_explorer_question_names_lint_failure_and_narrow_edit_anchor() -> None:
    scorer = next(
        case for case in STABILITY.CASES if case.name == "scorer-unused-binding"
    )
    task = STABILITY.explorer_task(scorer, "tests/test_scorer_unused_binding.py")
    assert "baseline failure is Ruff F841" in task
    citation = next(
        case for case in STABILITY.CASES if case.name == "reviewer-citation"
    )
    assert citation.anchor == "MAX_METADATA_BYTES = 163_840"
    assert len(citation.contract_behaviors) == 2
    assert "MAX_METADATA_BYTES declaration" in citation.contract_behaviors[0]
    metadata = next(case for case in STABILITY.CASES if case.name == "metadata-limit")
    assert metadata.anchor == "MAX_METADATA_BYTES = 163_840"
    identity = next(case for case in STABILITY.CASES if case.name == "sample-identity")
    assert identity.anchor == 'content = sample.model_dump(mode="json")'
    assert (
        identity.extra_mutations[0].anchor
        == '"sample": sample.model_dump(mode="json"),'
    )
    assert "no row_identity field" in identity.implementation_guidance[0]
    assert (
        "test_fingerprint_ignores_source_metadata_but_reuse_key_preserves_it"
        in identity.tests
    )


def test_mapping_explorer_question_traces_container_into_element_validation() -> None:
    case = next(
        case for case in STABILITY.CASES if case.name == "mapping-message-sequence"
    )
    task = STABILITY.explorer_task(case, "tests/test_mapping_message_sequence.py")
    assert "str and bytes message containers" in task
    assert "per-element Message.model_validate" in task


def test_explorer_evidence_requires_each_path_to_have_own_line_citation() -> None:
    case = next(case for case in STABILITY.CASES if case.name == "sample-identity")
    test_path = "tests/test_sample_identity.py"
    targets = [case.target, *(item.target for item in case.extra_mutations)]
    report = {
        "evidence_summary": {"observed_files": [*targets, test_path]},
        "findings": [f"{targets[0]}:52 includes sample_id"],
        "call_flow": [
            f"{targets[1]}:27 includes sample_id",
            f"{test_path}:49 expects exclusion",
        ],
    }
    assert STABILITY.explorer_has_line_evidence(report, case, test_path)
    report["call_flow"][1] = f"{test_path} expects exclusion"
    assert not STABILITY.explorer_has_line_evidence(report, case, test_path)
    report["call_flow"][1] = f"line 49 in {test_path} expects exclusion"
    assert STABILITY.explorer_has_line_evidence(report, case, test_path)


def test_explorer_evidence_accepts_unicode_line_first_citation() -> None:
    case = next(case for case in STABILITY.CASES if case.name == "selection-order")
    report = {
        "evidence_summary": {
            "observed_files": [case.target, "tests/test_selection_order.py"]
        },
        "findings": [
            f"Line\u202f27 of {case.target} sorts rows. "
            + "A separate sentence has a line 42 but no test path. "
            + "Lines\u202f20\u201123 of tests/test_selection_order.py expect newest first."
        ],
        "call_flow": [],
    }
    assert STABILITY.explorer_has_line_evidence(
        report, case, "tests/test_selection_order.py"
    )


def test_full_explorer_report_keeps_compact_observed_files(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"findings": ["complete evidence"]}), encoding="utf-8")
    merged = STABILITY.full_explorer_report(
        tmp_path,
        {
            "diagnostic_report": "report.json",
            "evidence_summary": {"observed_files": ["src/a.py"]},
            "findings": ["truncated"],
        },
    )
    assert merged["findings"] == ["complete evidence"]
    assert merged["evidence_summary"]["observed_files"] == ["src/a.py"]


def test_repair_metric_counts_guarded_single_line_edit(tmp_path: Path) -> None:
    case = next(case for case in STABILITY.CASES if case.name == "selection-order")
    path = (
        tmp_path
        / ".agent"
        / "tasks"
        / "stability-selection-order"
        / "runs"
        / "selection-order-a1"
        / "events.jsonl"
    )
    path.parent.mkdir(parents=True)
    events = [
        {"event": "tool_action", "facts": {"action": "VALIDATE", "status": "failed"}},
        {
            "event": "tool_action",
            "facts": {"action": "SAFE_REPLACE_LINE", "status": "ok"},
        },
    ]
    path.write_text("\n".join(json.dumps(item) for item in events), encoding="utf-8")
    assert STABILITY.archive_metrics(tmp_path, case)["next_action_is_edit"] == 1


def test_static_fixture_baseline_is_lint_only(tmp_path: Path) -> None:
    case = next(
        case for case in STABILITY.CASES if case.name == "scorer-unused-binding"
    )
    root = tmp_path / "fixture"
    STABILITY.prepare(case, root, {})
    test = STABILITY.run_command(
        root,
        [sys.executable, "-m", "pytest", "tests/test_scorer_unused_binding.py", "-q"],
        90,
    )
    lint = STABILITY.run_command(
        root, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
    )
    assert test.returncode == 0, test.stdout + test.stderr
    assert lint.returncode != 0
    assert "F841" in lint.stdout


def test_sample_identity_protected_metadata_boundary(tmp_path: Path) -> None:
    case = next(case for case in STABILITY.CASES if case.name == "sample-identity")
    root = tmp_path / "fixture"
    STABILITY.prepare(case, root, {})
    test_path = "tests/test_sample_identity.py"

    fingerprint = root / case.target
    fingerprint_text = fingerprint.read_text(encoding="utf-8")
    assert fingerprint_text.count(case.after) == 1
    fingerprint.write_text(
        fingerprint_text.replace(case.after, case.before, 1), encoding="utf-8"
    )
    dedup = root / case.extra_mutations[0].target
    dedup_text = dedup.read_text(encoding="utf-8")
    mutation = case.extra_mutations[0]
    assert dedup_text.count(mutation.after) == 1
    dedup.write_text(
        dedup_text.replace(mutation.after, mutation.before, 1), encoding="utf-8"
    )
    correct = STABILITY.run_command(
        root, [sys.executable, "-m", "pytest", test_path, "-q"], 90
    )
    assert correct.returncode == 0, correct.stdout + correct.stderr

    protected = root / "src/evaluation_harness/canonical/fingerprint.py"
    text = protected.read_text(encoding="utf-8")
    assert '"sample_id", "labels", "source_metadata"' in text
    protected.write_text(
        text.replace(
            '"sample_id", "labels", "source_metadata"',
            '"sample_id", "labels", "row_identity"',
            1,
        ),
        encoding="utf-8",
    )
    regression = STABILITY.run_command(
        root,
        [
            sys.executable,
            "-m",
            "pytest",
            f"{test_path}::test_fingerprint_ignores_source_metadata_but_reuse_key_preserves_it",
            "-q",
        ],
        90,
    )
    assert regression.returncode != 0
    assert "test_fingerprint_ignores_source_metadata_but_reuse_key_preserves_it" in (
        regression.stdout + regression.stderr
    )

    protected.write_text(
        fingerprint_text.replace(
            case.after,
            '    content = sample.model_dump(mode="json")\n'
            '    content.pop("sample_id", None)\n'
            '    content.pop("source_metadata", None)\n',
            1,
        ),
        encoding="utf-8",
    )
    labels_regression = STABILITY.run_command(
        root,
        [
            sys.executable,
            "-m",
            "pytest",
            f"{test_path}::test_fingerprint_ignores_labels_but_reuse_key_preserves_them",
            "-q",
        ],
        90,
    )
    assert labels_regression.returncode != 0
    assert "test_fingerprint_ignores_labels_but_reuse_key_preserves_them" in (
        labels_regression.stdout + labels_regression.stderr
    )
