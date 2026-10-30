"""Real CLI controls: continuity is opt-in and never weakens checks or scope."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import literal_check_feedback as L
import supervised_repair_phase as P
from test_self_audit_entry import setup_cell


def execute(root, proposals, enabled):
    replay = root.parent / "replay.json"
    S.save(replay, proposals)
    args = P.command(root, "unit", replay) + ["--static-focus"]
    if enabled:
        args.append("--execution-memory")
    result = T.run(args, root, timeout=180)
    report = S.read(root / ".agent/unit-report.json")
    identity = S.read(root / ".agent/packet.json")
    archive = root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
    return result, report, archive


@pytest.mark.parametrize("enabled", [False, True])
def test_failed_edit_then_repair_checks_current_code_and_retains_only_true_events(
    tmp_path, enabled
):
    root, _, reference = setup_cell(tmp_path)
    wrong = reference.replace("return str(value)", 'return "wrong"')
    result, report, archive = execute(
        root, [{"replacement": wrong}, {"replacement": reference}], enabled
    )
    assert result["exit_code"] == 0, result
    counts = report["consolidated_harness"]["actual"]
    assert counts["edits"] == counts["post_edit_checks"] == 2
    request = S.read(archive / "proposal-request-2.json")
    facts = L.restore(
        request["messages"][1]["content"]
        .split("\n", 1)[1]
        .split("\nCURRENT_STATIC_DIAGNOSTIC", 1)[0]
    )
    assert ("execution_memory" in facts) is enabled
    if enabled:
        event = facts["execution_memory"]["recent_attempts"][0]
        assert event["observed_counts"]["edits"] == 1
        assert event["source_after"] == facts["target"]["sha256"]
        assert 'return "wrong"' in event["diff_excerpt"]
        assert event["feedback"] is None


def test_noop_history_does_not_grant_handoff_or_add_check(tmp_path):
    root, row, _ = setup_cell(tmp_path)
    original = (root / row["target"]).read_text(encoding="utf-8")
    result, report, archive = execute(root, [{"replacement": original}] * 2, True)
    assert result["exit_code"] != 0
    counts = report["consolidated_harness"]["actual"]
    assert counts["noops"] == 2 and counts["post_edit_checks"] == 0
    request = S.read(archive / "proposal-request-2.json")
    assert '"noops": 1' in request["messages"][1]["content"]
    assert not S.read(root / ".agent/unit-summary.json")["reviewer_started"]


def test_memory_does_not_enable_read_or_shell_actions(tmp_path):
    root, _, _ = setup_cell(tmp_path)
    result, report, _ = execute(root, [{"read": {"path": "secret"}}] * 3, True)
    assert result["exit_code"] != 0
    assert report["consolidated_harness"]["actual"]["edits"] == 0
