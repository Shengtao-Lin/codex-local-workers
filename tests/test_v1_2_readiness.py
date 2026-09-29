from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
import v1_2_readiness as READINESS


def passing_batch() -> tuple[dict, dict]:
    cases = ["sample-identity", *(f"case-{index}" for index in range(10))]
    results = []
    ratings = []
    for round_number in (1, 2):
        for case in cases:
            results.append(
                {
                    "case": case,
                    "workspace": f"F:/work/batch/round-{round_number}/{case}",
                    "explorer_status": "success",
                    "explorer_evidence_valid": True,
                    "metrics": {
                        "repair_focus_issued": 1,
                        "next_action_is_edit": 1,
                        "first_repair_next_action_is_edit": True,
                        "citation_required": True,
                        "citation_converged": True,
                    },
                    "coder_status": "ready_for_review",
                    "reviewer_decision": "pass_to_primary",
                    "primary_decision": "accept",
                    "qualified_pass": True,
                    "infra_failure": False,
                }
            )
            ratings.append({"round": round_number, "case": case, "status": "correct"})
    return (
        {"schema_version": 1, "reviewer": "Primary Agent", "ratings": ratings},
        {"schema_version": 1, "results": results},
    )


def test_pipeline_gate_passes_complete_two_round_evidence() -> None:
    audit, summary = passing_batch()
    result = READINESS.assess_pipeline(audit, summary)
    assert result["pipeline_decision"] == "GO"
    assert result["coder"]["repair_focus_units"] == 22


def test_pipeline_gate_keeps_role_failures_independent() -> None:
    audit, summary = passing_batch()
    for rating in audit["ratings"][:6]:
        rating.update(status="incomplete", reason="Omitted source-predicted result.")
    for item in summary["results"][:8]:
        item["metrics"]["next_action_is_edit"] = 0
        item["metrics"]["first_repair_next_action_is_edit"] = False
    summary["results"][0]["coder_status"] = "failed"
    summary["results"][0]["primary_decision"] = "rework"
    summary["results"][1]["infra_failure"] = True
    summary["results"][2]["metrics"]["citation_converged"] = False
    result = READINESS.assess_pipeline(audit, summary)
    assert result["pipeline_decision"] == "NO-GO"
    assert any("strict Explorer" in reason for reason in result["reasons"])
    assert any("Coder immediate" in reason for reason in result["reasons"])
    assert any("Reviewer" in reason for reason in result["reasons"])
    assert any("infrastructure" in reason for reason in result["reasons"])
    assert any("sample-identity" in reason for reason in result["reasons"])


def test_role_aligned_gate_records_immediate_read_without_blocking_valid_repair() -> (
    None
):
    audit, summary = passing_batch()
    for item in summary["results"][:8]:
        item["metrics"]["first_repair_next_action_is_edit"] = False
    result = READINESS.assess_pipeline(audit, summary, gate_version="role-aligned-v1")
    assert result["pipeline_decision"] == "GO"
    assert result["coder"]["immediate_edit"] == 14
    assert result["coder"]["eventual_validation"] == 22
    assert READINESS.assess_pipeline(audit, summary)["pipeline_decision"] == "NO-GO"


def test_pipeline_gate_requires_enough_repair_focus_units() -> None:
    audit, summary = passing_batch()
    sparse = copy.deepcopy(summary)
    for item in sparse["results"][9:]:
        item["metrics"]["repair_focus_issued"] = 0
    result = READINESS.assess_pipeline(audit, sparse)
    assert result["coder"]["repair_focus_units"] == 9
    assert any("denominator" in reason for reason in result["reasons"])


def test_first_repair_metric_does_not_credit_a_later_edit(tmp_path: Path) -> None:
    workspace = tmp_path / "case"
    agent = workspace / ".agent"
    agent.mkdir(parents=True)
    (agent / "packet.json").write_text(
        json.dumps({"task_id": "task-a", "run_id": "run-a"}), encoding="utf-8"
    )
    events = agent / "tasks/task-a/runs/run-a/events.jsonl"
    events.parent.mkdir(parents=True)
    records = [
        {"event": "repair_focus_issued", "facts": {}},
        {"event": "tool_action", "facts": {"action": "VALIDATE", "status": "failed"}},
        {
            "event": "tool_action",
            "facts": {"action": "READ_FILE", "status": "rejected"},
        },
        {"event": "tool_action", "facts": {"action": "SAFE_REPLACE", "status": "ok"}},
    ]
    events.write_text("\n".join(json.dumps(item) for item in records), encoding="utf-8")
    assert READINESS.first_repair_immediate_edit({"workspace": str(workspace)}) is False
    records[2]["facts"]["action"] = "SAFE_REPLACE"
    events.write_text("\n".join(json.dumps(item) for item in records), encoding="utf-8")
    assert READINESS.first_repair_immediate_edit({"workspace": str(workspace)}) is True
