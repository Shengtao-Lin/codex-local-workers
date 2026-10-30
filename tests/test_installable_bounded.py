"""Installed/offline equivalence, recovery budget and fail-closed controls."""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
import bounded_evidence_support as S
import capture_fixture_support as F
import limited_family_trial as L

SPEC = importlib.util.spec_from_file_location(
    "bounded_test_installer", KIT / "scripts/install_local_agents.py"
)
INSTALL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALL)


def project(root, topic, label):
    INSTALL.install(KIT, root, apply=True)
    template = L.BATCH / "templates" / topic
    for name in ("src", "tests"):
        shutil.copytree(template / name, root / name)
    shutil.copyfile(template / "pyproject.toml", root / "pyproject.toml")
    packet = S.read(L.BATCH / "cells" / (topic + "-1") / "isolated/.agent/packet.json")
    identity = {k: label for k in ("task_id", "unit_id", "run_id")}
    packet.update(identity)
    config = S.read(L.SEED / ".agent/config.json")
    config.update(bounded_execution_profile="bounded-v1")
    config["coder_single_function"] = S.read(
        L.BATCH / "cells" / (topic + "-1") / "isolated/.agent/config.json"
    )["coder_single_function"]
    sources = [
        p
        for p in packet["scope"]["readonly"]
        if p not in {F.POLICY_PATH, F.PRODUCER, F.HELPER}
    ] + packet["scope"]["modify"]
    spec = L.TASKS[topic]
    _, digest = F.install_material(
        root,
        identity,
        source_paths=sources,
        target={
            "path": "src/product/code.py",
            "module": "product.code",
            "symbol": spec["symbol"],
        },
        family="json-call-model-dump-v1",
        cases=spec["cases"],
        writable=["src/product/code.py"],
        python=S.PYTHON,
    )
    config["experimental_capture_policy_sha256"] = digest
    S.save(root / ".agent/packet.json", packet)
    S.save(root / ".agent/config.json", config)
    return packet, config


def run(root, replacements, *, installed=True):
    replay = root / ".agent/replay.json"
    S.save(replay, replacements)
    if installed:
        argv = [
            S.PYTHON,
            "-B",
            root / ".local-agents/local-bounded-unit.py",
            "--mode",
            "unit",
            "--packet",
            root / ".agent/packet.json",
            "--config",
            root / ".agent/config.json",
            "--report",
            root / ".agent/unit-report.json",
            "--review-report",
            root / ".agent/reviewer-report.json",
            "--summary",
            root / ".agent/unit-summary.json",
            "--replay",
            replay,
        ]
    else:
        argv = L.command(root, replay=replay)
    result = subprocess.run(
        [str(v) for v in argv],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
    )
    return result


def archive(root):
    packet = S.read(root / ".agent/packet.json")
    return root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]


@pytest.mark.parametrize("topic", ["labels", "unique", "route"])
def test_installed_full_chain_matches_frozen_candidate(topic):
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        one, two = base / "experiment", base / "installed"
        one.mkdir()
        two.mkdir()
        project(one, topic, "parity-" + topic)
        project(two, topic, "parity-" + topic)
        replacements = [{"replacement": L.TASKS[topic]["reference"]}]
        old, new = run(one, replacements, installed=False), run(two, replacements)
        assert old.returncode == new.returncode == 0, (old.stderr, new.stderr)
        assert (one / "src/product/code.py").read_bytes() == (
            two / "src/product/code.py"
        ).read_bytes()
        old_report = S.read(one / ".agent/unit-report.json")
        new_report = S.read(two / ".agent/unit-report.json")
        assert (
            old_report["consolidated_harness"]["actual"]
            == new_report["consolidated_harness"]["actual"]
        )
        assert S.read(two / ".agent/unit-summary.json")["reviewer_started"] is False
        assert (
            S.read(two / ".agent/unit-summary.json")["reviewer_input_authenticated"]
            is True
        )
        old_request = S.read(archive(one) / "proposal-request-1.json")
        new_request = S.read(archive(two) / "proposal-request-1.json")
        assert old_request["messages"][0] == new_request["messages"][0]
        assert old_request["binding"] == new_request["binding"]
        assert old_request["schema"] == new_request["schema"]
        old_bundle = S.read(one / ".agent/reviewer-report.json")["bundle"]
        new_bundle = S.read(two / ".agent/reviewer-report.json")["bundle"]
        # Compare substantive model evidence, not durations, host paths or archive hashes.
        assert old_bundle.keys() == new_bundle.keys()
        for key in (
            "risk",
            "owned_contract_ids",
            "obligations",
            "dependencies",
            "approved_observations",
            "verdict_definitions",
        ):
            assert old_bundle[key] == new_bundle[key], key
        assert not (two / "benchmarks").exists()


def test_every_effective_edit_gets_current_complete_check():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root, "labels", "three-edit-offline")
        proposals = [
            "def merge_labels(defaults: dict[str, str], overrides: dict[str, str | None]) -> dict[str, str]:\n    return {}\n",
            "def merge_labels(defaults: dict[str, str], overrides: dict[str, str | None]) -> dict[str, str]:\n    return {**defaults, **overrides}\n",
            L.TASKS["labels"]["reference"],
        ]
        result = run(root, [{"replacement": p} for p in proposals])
        assert result.returncode == 0, result.stderr
        report = S.read(root / ".agent/unit-report.json")
        actual = report["consolidated_harness"]["actual"]
        assert actual["initial_checks"] == 1
        assert actual["edits"] == actual["post_edit_checks"] == 3
        assert len(list(archive(root).glob("validation-attempt-*.json"))) == 4
        assert report["status"] == "validation_passed_pending_review"


def test_noop_does_not_trigger_review_or_consume_edit_check():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root, "labels", "noop-offline")
        result = run(root, [{"replacement": L.TASKS["labels"]["start"]}] * 2)
        assert result.returncode == 2
        report = S.read(root / ".agent/unit-report.json")
        actual = report["consolidated_harness"]["actual"]
        assert (
            actual["noops"] == 2 and actual["edits"] == actual["post_edit_checks"] == 0
        )
        assert S.read(root / ".agent/unit-summary.json")["reviewer_started"] is False


def test_profile_opt_in_is_required_before_execution():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _, config = project(root, "labels", "no-opt-in")
        del config["bounded_execution_profile"]
        (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")
        result = run(root, [{"replacement": L.TASKS["labels"]["reference"]}])
        assert result.returncode != 0 and "Explicit bounded-v1" in result.stderr
        assert not archive(root).exists()


def test_installed_provider_has_no_historical_fallback():
    sys.path.insert(0, str(KIT / ".local-agents"))
    from bounded import approved_provider as provider

    with pytest.raises(ValueError, match="canonical capture"):
        provider.facts(object(), ValueError)
    assert (
        not (KIT / ".local-agents/config.example.json")
        .read_text(encoding="utf-8")
        .count("bounded_execution_profile")
    )


def test_installed_protocol_matches_reference_rules():
    sys.path.insert(0, str(KIT / ".local-agents"))
    import static_focus_rules as original
    from bounded import static_focus_rules as installed

    assert installed.PROMPT == original.PROMPT
    assert installed.SCHEMA == original.SCHEMA
    assert installed.IMPORT_CEILING == original.IMPORT_CEILING
    for value in ('{"replacement":"x"}', '{"blocked_reason":"missing"}'):
        assert installed.decode(value) == original.decode(value)
    for value in (
        '{"replacement":"x","shell":null}',
        '{"replacement":"x","blocked_reason":"y"}',
    ):
        with pytest.raises(ValueError):
            installed.decode(value)


@pytest.mark.parametrize(
    "name",
    [
        "test_positive_full_run_source_blind_and_total_requests_truthful",
        "test_explicit_prediction_mismatch_cannot_be_verified_but_no_defect_invented",
        "test_host_does_not_correct_wrong_model_prediction_using_hidden_truth",
        "test_prediction_and_report_share_error_budget",
        "test_errors_across_both_phases_are_not_reset",
        "test_sticky_profile_survives_shape_correction_within_shared_budget",
    ],
)
def test_installed_reviewer_reuses_original_semantic_controls(
    tmp_path, monkeypatch, name
):
    sys.path.insert(0, str(KIT / ".local-agents"))
    import test_reviewer_contract_first as original_tests
    from bounded import reviewer_contract_first as installed

    # Same original positive/negative judgments and fake client. Only engine location changes.
    monkeypatch.setattr(original_tests, "A", installed)
    getattr(original_tests, name)(tmp_path)


@pytest.mark.parametrize("reason_code", ["model_switch_lock_held", "model_load_failed"])
def test_busy_role_lease_is_structured_infrastructure_not_worker_quality(
    monkeypatch, reason_code
):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project(root, "labels", "lease-busy-offline")
        sys.path.insert(0, str(root / ".local-agents"))
        entry = F.load(
            root / ".local-agents/local-bounded-unit.py", "bounded_busy_control"
        )
        load = entry.F.load

        def guarded_load(path, name):
            module = load(path, name)
            if name == "bounded_installed_worker":

                def busy(*_args, **_kwargs):
                    raise module.MODEL_RESIDENCY.ModelResidencyError(
                        reason_code, "controlled residency failure"
                    )

                monkeypatch.setattr(module.MODEL_RESIDENCY, "role_model_lease", busy)
            return module

        monkeypatch.setattr(entry.F, "load", guarded_load)
        previous_cwd = Path.cwd()
        monkeypatch.chdir(root)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                str(root / ".local-agents/local-bounded-unit.py"),
                "--packet",
                ".agent/packet.json",
                "--config",
                ".agent/config.json",
                "--report",
                ".agent/unit-report.json",
                "--review-report",
                ".agent/reviewer-report.json",
                "--summary",
                ".agent/unit-summary.json",
            ],
        )
        try:
            outcome = entry.main()
        finally:
            monkeypatch.chdir(previous_cwd)
        assert outcome == 2
        report = S.read(root / ".agent/unit-report.json")
        assert report["status"] == "blocked"
        assert report["infra_failure"]["reason_code"] == reason_code
        assert S.read(root / ".agent/unit-summary.json")["reviewer_started"] is False
        assert not archive(root).exists()
