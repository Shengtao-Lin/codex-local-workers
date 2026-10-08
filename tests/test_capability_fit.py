"""Diagnostic harness must fail closed before invoking a model."""

import importlib.util
import json
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fit(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(KIT / "benchmarks"))
    spec = importlib.util.spec_from_file_location(
        "fit_test", KIT / "benchmarks/capability_fit.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.WORK = tmp_path
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "freeze.json").write_text(json.dumps({"files": {}}), encoding="utf-8")
    return module


def test_invalid_trial_identity_fails_before_materializing(fit):
    with pytest.raises(ValueError, match="trial identity"):
        fit.run_case("bounded-report", "candidate", 1, "snapshot", "../escape")
    assert not (fit.WORK / "runs").exists()


def test_fewshot_cannot_be_mislabeled_as_development(fit):
    with pytest.raises(ValueError, match="transfer cohort"):
        fit.run_case("bounded-report", "fewshot", 1, "snapshot")


def test_snapshot_hash_drift_rejected_before_model(fit):
    (fit.WORK / "snapshot/freeze.json").write_text(
        json.dumps({"files": {"source.py": "not-current-hash"}}), encoding="utf-8"
    )
    (fit.WORK / "snapshot/source.py").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot drift"):
        fit.run_case("bounded-report", "direct", 1, "snapshot")


def test_records_are_create_only(fit):
    record = fit.WORK / "result.json"
    fit.write(record, {"value": 1})
    with pytest.raises(FileExistsError):
        fit.write(record, {"value": 2})
    assert json.loads(record.read_text(encoding="utf-8")) == {"value": 1}


def test_diagnostics_requires_versioned_cohort_and_implemented_snapshot(fit):
    with pytest.raises(ValueError, match="diagnostic cohort"):
        fit.run_case(
            "transfer-overlay", "candidate", 1, "snapshot", failed_test_diagnostics=True
        )
    with pytest.raises(ValueError, match="current/off"):
        fit.run_case("diag-overlay", "candidate", 1, "snapshot")
    with pytest.raises(ValueError, match="does not implement"):
        fit.run_case(
            "diag-overlay", "candidate", 1, "snapshot", failed_test_diagnostics=True
        )
    assert not (fit.WORK / "runs").exists()


def test_skeleton_requires_implemented_candidate_snapshot(fit):
    with pytest.raises(ValueError, match="requires candidate arm"):
        fit.run_case(
            "transfer-overlay", "current", 1, "snapshot", validation_id_skeleton=True
        )
    with pytest.raises(ValueError, match="does not implement"):
        fit.run_case(
            "transfer-overlay", "candidate", 1, "snapshot", validation_id_skeleton=True
        )
    assert not (fit.WORK / "runs").exists()


def test_inline_analysis_requires_isolated_implemented_candidate(fit):
    with pytest.raises(ValueError, match="candidate with no skeleton"):
        fit.run_case(
            "transfer-overlay", "current", 1, "snapshot", inline_repair_analysis=True
        )
    with pytest.raises(ValueError, match="does not implement inline"):
        fit.run_case(
            "transfer-overlay", "candidate", 1, "snapshot", inline_repair_analysis=True
        )
    assert not (fit.WORK / "runs").exists()


@pytest.mark.parametrize("style", ["matrix", "unknown"])
def test_packet_style_rejects_other_cohorts(fit, style):
    with pytest.raises(ValueError, match="packet style"):
        fit.run_case("bounded-report", "candidate", 1, "snapshot", packet_style=style)
    assert not (fit.WORK / "runs").exists()


def test_invalid_repair_focus_rejected_before_model(fit):
    with pytest.raises(ValueError, match="repair focus"):
        fit.run_case(
            "bounded-report", "candidate", 1, "snapshot", repair_focus="unknown"
        )
    assert not (fit.WORK / "runs").exists()


def test_direct_cannot_claim_context_retention_experiment(fit):
    with pytest.raises(ValueError, match="tool-loop"):
        fit.run_case(
            "transfer-lock-release", "direct", 1, "snapshot", retention="budgeted"
        )
    assert not (fit.WORK / "runs").exists()


def test_long_identity_rejected_before_workspace_or_model(fit):
    with pytest.raises(ValueError, match="runtime limit"):
        fit.run_case(
            "transfer-lock-release", "fewshot-actions", 1, "snapshot", "x" * 100
        )
    assert not (fit.WORK / "runs").exists()
