"""Actual opt-in CLI on registered normal starts; no model or network."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import normal_task_trial as N


@pytest.mark.parametrize("topic", ["request_keys", "single_content"])
def test_actual_entry_complete_replay(topic, tmp_path):
    row = N.prepare_cell(topic, tmp_path / topic, "offline-" + topic)
    root = Path(row["root"])
    reference = N.OLD / "private" / topic / "reference.py"
    replay = root.parent / "replay.json"
    S.save(replay, [{"replacement": reference.read_text(encoding="utf-8-sig")}])
    result = T.run(N.command(root, replay=replay), root, timeout=180)
    S.save(root.parent / "execution.json", result)
    assert result["exit_code"] == 0, result
    report = S.read(root / ".agent/unit-report.json")
    actual = report["consolidated_harness"]["actual"]
    assert actual["model_requests"] == 0 and actual["scripted_requests"] == 1
    assert actual["edits"] == actual["post_edit_checks"] == 1
    summary = S.read(root / ".agent/unit-summary.json")
    assert summary["reviewer_input_authenticated"]
    assert summary["reviewer_started"] is False
    assert summary["reviewer_decision"] == "NOT_RUN"
    assert all(
        S.sha(root / p) == digest
        for p, digest in row["files"].items()
        if p != row["target"]
    )
    # Verifier must reject a successful archive after its current source changes.
    worker = F.load(
        root / ".local-agents/worker-runtime.py", "normal_stale_worker_" + topic
    )
    editor = root / row["target"]
    editor.write_bytes(editor.read_bytes() + b"\n# stale\n")
    gate = F.load(root / ".local-agents/local-unit.py", "normal_stale_gate_" + topic)
    with pytest.raises(Exception, match="changed|differ|hash|stale|valid|current"):
        gate.verify_handoff(
            root, report, config=worker.load_json(root / ".agent/config.json")
        )


def test_real_cli_rejects_scope_change(tmp_path):
    row = N.prepare_cell("request_keys", tmp_path / "bad", "offline-scope")
    root = Path(row["root"])
    source = (root / row["target"]).read_text(encoding="utf-8-sig")
    replay = root.parent / "bad.json"
    S.save(replay, [{"replacement": "import os\n" + source}] * 3)
    result = T.run(N.command(root, "coder", replay), root, timeout=180)
    assert result["exit_code"] != 0
    report = S.read(root / ".agent/coder-report.json")
    assert report["consolidated_harness"]["actual"]["edits"] == 0
    assert S.sha(root / row["target"]) == row["files"][row["target"]]
