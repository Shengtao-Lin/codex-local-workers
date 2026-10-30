"""No-network real CLI controls for the reused bounded read/search interface."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import supervised_repair_phase as P
from test_self_audit_entry import setup_cell


def execute(root, actions):
    config_path = root / ".agent/config.json"
    config = S.read(config_path)
    config["experimental_evidence_files"] = [
        "tests/test_contract.py",
        "src/product/code.py",
    ]
    config_path.write_text(json.dumps(config), encoding="utf-8")
    replay = root.parent / "replay.json"
    S.save(replay, actions)
    result = T.run(
        P.command(root, "unit", replay) + ["--static-focus", "--evidence-loop"],
        root,
        timeout=180,
    )
    report = S.read(root / ".agent/unit-report.json")
    identity = S.read(root / ".agent/packet.json")
    archive = root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
    return result, report, archive


@pytest.mark.parametrize("kind", ["read", "search"])
def test_evidence_counts_request_not_edit_and_real_check_still_required(tmp_path, kind):
    root, _, reference = setup_cell(tmp_path)
    args = {"path": "tests/test_contract.py"}
    args.update(
        {"start_line": 1, "end_line": 40} if kind == "read" else {"query": "test_"}
    )
    result, report, archive = execute(root, [{kind: args}, {"replacement": reference}])
    assert result["exit_code"] == 0, result
    actual = report["consolidated_harness"]["actual"]
    assert actual["requests"] == 2 and actual["evidence_actions"] == 1
    assert actual["edits"] == actual["post_edit_checks"] == 1
    request = S.read(archive / "proposal-request-2.json")
    assert '"evidence_observations"' in request["messages"][1]["content"]
    evidence = S.read(archive / "evidence-1.json")
    assert evidence["hashes"]["tests/test_contract.py"] == S.sha(
        root / "tests/test_contract.py"
    )
    assert not {"next_step", "navigation_hint", "source_context"} & set(
        evidence["observation"]
    )
    assert S.read(root / ".agent/unit-summary.json")["reviewer_input_authenticated"]


@pytest.mark.parametrize(
    "path", ["../secret", ".agent/packet.json", "tests/missing.py"]
)
def test_scope_escape_fails_closed_before_edit(tmp_path, path):
    root, _, _ = setup_cell(tmp_path)
    result, report, _ = execute(
        root, [{"read": {"path": path, "start_line": 1, "end_line": 2}}]
    )
    assert result["exit_code"] != 0
    assert report["status"] == "policy_violation"
    assert report["consolidated_harness"]["actual"]["edits"] == 0


def test_duplicate_evidence_stops_without_primary_or_extra_edits(tmp_path):
    root, _, _ = setup_cell(tmp_path)
    action = {
        "read": {"path": "tests/test_contract.py", "start_line": 1, "end_line": 2}
    }
    result, report, _ = execute(root, [action] * 4)
    assert result["exit_code"] != 0
    assert report["consolidated_harness"]["actual"]["evidence_actions"] == 3
    assert report["consolidated_harness"]["actual"]["edits"] == 0
