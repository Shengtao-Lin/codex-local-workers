"""Exercise the actual installed CLI; no __class__ substitution or model network."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_readiness as READY
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import harness_protocol as P

OLD = S.KIT / "benchmarks/work/harness-convergence/behavior-unit-20261018-3"
REFERENCE = (
    S.KIT
    / "benchmarks/work/harness-convergence/bounded-evidence-prep-20261018-1/task-preparation-v4/private"
)


def prepare(root_parent, topic, label):
    row = S.read(OLD / "cells.json")[topic + "-A1"]
    root = READY.clone(row, root_parent)
    packet_path, policy_path = root / ".agent/packet.json", root / F.POLICY_PATH
    identity = {
        "task_id": "consolidated-" + label,
        "unit_id": "consolidated-" + label,
        "run_id": "consolidated-" + label,
    }
    packet, policy = S.read(packet_path), S.read(policy_path)
    packet.update(identity)
    policy["identity"] = identity
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    config = S.read(root / ".agent/config.json")
    config = {k: v for k, v in config.items() if not k.startswith("experimental_")}
    config.update(
        experimental_consolidated_harness=True,
        experimental_capture_policy_sha256=S.sha(policy_path),
        experimental_approved_imports=[
            ["collections.abc", "Iterator", None],
            ["collections.abc", "Sequence", None],
            ["typing", "cast", None],
        ]
        if topic == "T2"
        else [],
        coordinator_enabled=False,
        autoformat_on_ruff_failure=False,
    )
    (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")
    return root


def command(root, mode, replay=None):
    args = [
        S.PYTHON,
        "-B",
        S.KIT / "benchmarks/consolidated_entry.py",
        "--mode",
        mode,
        "--runtime-dir",
        root / ".local-agents",
        "--packet",
        root / ".agent/packet.json",
        "--config",
        root / ".agent/config.json",
        "--report",
        root / ".agent/report.json",
    ]
    if replay is not None:
        S.save(root / ".agent/replay.json", replay)
        args += ["--replay", root / ".agent/replay.json"]
    if mode == "unit":
        args += [
            "--review-report",
            root / ".agent/review.json",
            "--summary",
            root / ".agent/summary.json",
        ]
    return args


def run(root, mode, replay=None):
    result = T.run(command(root, mode, replay), root, timeout=180)
    S.save(root.parent / "entry-process.json", result)
    assert (root / ".agent/report.json").exists(), result["stderr"]
    return result, S.read(root / ".agent/report.json")


@pytest.mark.parametrize(
    "value",
    [
        '{"replacement":"x","replacement":"y"}',
        '{"replacement":"x","blocked_reason":"y"}',
        '{"replacement":null,"blocked_reason":null}',
        '{"replacement":"x","blocked_reason":""}',
        '{"replacement":"x","shell":null}',
        '{"replacement":false}',
        '{"replacement":""}',
        "[]",
    ],
)
def test_ambiguous_or_unknown_output_rejected(value):
    with pytest.raises(ValueError):
        P.decode(value)


def test_only_inactive_null_is_normalized():
    assert P.decode('{"replacement":"x","blocked_reason":null}') == (
        {"replacement": "x"},
        ["blocked_reason"],
    )
    assert P.decode('{"replacement":null,"blocked_reason":"need evidence"}') == (
        {"blocked_reason": "need evidence"},
        ["replacement"],
    )


def test_preflight_actual_entry_no_archive_or_model(tmp_path):
    root = prepare(tmp_path, "T1", "preflight")
    result, report = run(root, "preflight")
    assert result["exit_code"] == 0, result
    assert report["model_calls"] == 0
    assert report["runtime_mro"] == ["Consolidated", "WorkerRuntime", "object"]
    assert not (root / ".agent/local-worker-write.lock").exists()


def test_actual_unit_entry_canonical_gate_and_fresh_reviewer_input(tmp_path):
    root = prepare(tmp_path, "T2", "positive")
    source = (REFERENCE / "T2/reference.py").read_text(encoding="utf-8")
    result, report = run(
        root, "unit", [{"replacement": source.rstrip("\n"), "blocked_reason": None}]
    )
    assert result["exit_code"] == 0, result["stderr"] + result["stdout"][-1500:]
    assert report["status"] == "validation_passed_pending_review"
    counts = report["consolidated_harness"]["actual"]
    assert counts["model_requests"] == 0 and counts["scripted_requests"] == 1
    assert counts["edits"] == counts["post_edit_checks"] == 1
    assert counts["envelope_normalizations"] == counts["format_preparations"] == 1
    summary = S.read(root / ".agent/summary.json")
    assert (
        summary["reviewer_started"] is False
        and summary["reviewer_decision"] == "NOT_RUN"
    )
    assert summary["reviewer_input_authenticated"] is True


def test_prepared_noop_keeps_edit_and_validation_slots(tmp_path):
    root = prepare(tmp_path, "T1", "noop")
    source = (root / "src/product/code.py").read_text(encoding="utf-8")
    before = S.sha(root / "src/product/code.py")
    proposal = {"replacement": source.rstrip("\n"), "blocked_reason": None}
    result, report = run(root, "coder", [proposal, proposal])
    assert result["exit_code"] == 2, result
    assert report["failure_reason"] == "Two unchanged prepared proposals"
    counts = report["consolidated_harness"]["actual"]
    assert counts["requests"] == counts["noops"] == counts["format_preparations"] == 2
    assert counts["edits"] == counts["post_edit_checks"] == 0
    assert counts["initial_checks"] == 1
    assert before == S.sha(root / "src/product/code.py")


def test_complete_diagnostics_bound_to_current_source(tmp_path):
    root = prepare(tmp_path, "T2", "diagnostics")
    result, report = run(root, "coder", [{"blocked_reason": "control ends"}])
    assert result["exit_code"] == 2, result
    assert report["status"] == "blocked"
    archive = (
        root / ".agent/tasks/consolidated-diagnostics/runs/consolidated-diagnostics"
    )
    req = S.read(archive / "proposal-request-1.json")
    facts = json.JSONDecoder().raw_decode(req["messages"][1]["content"])[0]
    assert facts["validation_failure"]["status"] == "failed"
    assert (
        facts["supplemental_host_diagnostics"]["source_sha256"]
        == facts["target"]["sha256"]
    )
    assert any(
        c["id"] == "pyright" and c["status"] == "failed"
        for c in facts["supplemental_host_diagnostics"]["checks"]
    )


def test_guard_rejects_suppression_and_scope_change():
    source = "from __future__ import annotations\ndef f(x: object) -> object:\n    return x\n"
    for proposed in [
        source + "\ny = 1\n",
        source.replace("return x", "return x  # type: ignore"),
        source.replace("return x", "import os\n    return x"),
    ]:
        with pytest.raises(ValueError):
            P.guard(source, proposed, "f", set())


def test_truncated_output_recovers_without_applying_partial_code(tmp_path):
    root = prepare(tmp_path, "T1", "truncation")
    before = S.sha(root / "src/product/code.py")
    result, report = run(
        root,
        "coder",
        [{"_model_error": "output_token_limit"}, {"blocked_reason": "control ends"}],
    )
    assert result["exit_code"] == 2
    counts = report["consolidated_harness"]["actual"]
    assert counts["protocol_recoveries"] == 1 and counts["requests"] == 2
    assert counts["model_requests"] == counts["edits"] == 0
    assert before == S.sha(root / "src/product/code.py")


def test_validation_epoch_still_rejects_later_changes(tmp_path):
    root = prepare(tmp_path, "T2", "epoch")
    source = (REFERENCE / "T2/reference.py").read_text(encoding="utf-8")
    result, report = run(root, "coder", [{"replacement": source}])
    assert result["exit_code"] == 0, result["stderr"]
    gate = F.load(root / ".local-agents/local-unit.py", "consolidated_epoch_gate")
    gate.verify_handoff(root, report, config=S.read(root / ".agent/config.json"))
    path = root / "src/product/code.py"
    path.write_bytes(path.read_bytes() + b"\n# invalidated\n")
    with pytest.raises((RuntimeError, ValueError)):
        gate.verify_handoff(root, report, config=S.read(root / ".agent/config.json"))


def test_third_real_edit_gets_final_check_through_actual_entry(tmp_path):
    root = prepare(tmp_path, "T2", "third-edit")
    current = (root / "src/product/code.py").read_text(encoding="utf-8")
    first = current.replace("from typing import cast\n", "")
    second = current.replace("return items", "return cast(Sequence[object], items)")
    final = (REFERENCE / "T2/reference.py").read_text(encoding="utf-8")
    result, report = run(
        root, "coder", [{"replacement": source} for source in (first, second, final)]
    )
    assert result["exit_code"] == 0, result["stderr"] + result["stdout"][-1000:]
    actual = report["consolidated_harness"]["actual"]
    assert (
        actual["edits"]
        == actual["post_edit_checks"]
        == actual["format_preparations"]
        == 3
    )
    assert actual["initial_checks"] == 1 and actual["model_requests"] == 0
    gate = F.load(root / ".local-agents/local-unit.py", "consolidated_third_gate")
    gate.verify_handoff(root, report, config=S.read(root / ".agent/config.json"))
