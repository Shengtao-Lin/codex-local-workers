from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import localization_readiness as READINESS


def candidate():
    cases = ["sample-identity", *[f"case-{i}" for i in range(10)]]
    return {
        "results": [
            {
                "case": case,
                "workspace": f"/batch/round-{round_number}/{case}",
                "localization_verified": True,
                "coder_status": "ready_for_review",
                "reviewer_decision": "pass_to_primary",
                "primary_decision": "accept",
                "qualified_pass": True,
                "infra_failure": False,
                "metrics": {
                    "repair_focus_issued": 1,
                    "citation_required": True,
                    "citation_converged": True,
                },
            }
            for round_number in (1, 2)
            for case in cases
        ]
    }


def test_localization_never_qualifies_semantic_routing():
    result = READINESS.assess(candidate())
    assert result["pipeline_decision"] == "GO"
    assert result["general_semantic_routing"] == "NOT_QUALIFIED"
    assert result["explorer"]["semantic_diagnosis"] == "not_evaluated"


def test_repeated_location_miss_is_not_erased_by_coder_success():
    summary = candidate()
    summary["results"][0]["localization_verified"] = False
    summary["results"][11]["localization_verified"] = False
    result = READINESS.assess(summary)
    assert result["pipeline_decision"] == "NO-GO"
    assert any("repeated localization miss" in reason for reason in result["reasons"])


def test_infra_reviewer_and_critical_coder_gates_remain():
    for field, value in (
        ("infra_failure", True),
        ("reviewer_decision", "rework"),
        ("coder_status", "failed"),
    ):
        summary = candidate()
        summary["results"][0][field] = value
        assert READINESS.assess(summary)["pipeline_decision"] == "NO-GO"


def test_duplicate_cells_cannot_inflate_localization_score():
    summary = candidate()
    summary["results"].append(summary["results"][0])
    with pytest.raises(ValueError, match="duplicate"):
        READINESS.assess(summary)


def test_materialized_refs_are_checked_against_preimages_not_model_claims(tmp_path):
    case = READINESS.STABILITY.CASES[0]
    test_path = "tests/test_selection_order.py"
    archive = tmp_path / ".agent/tasks/t/runs/r"
    archive.mkdir(parents=True)
    source = archive / "source.py"
    source.write_text(case.after)
    test = tmp_path / test_path
    test.parent.mkdir()
    test.write_text("assert True\n")
    (tmp_path / ".agent/packet.json").write_text(
        json.dumps({"task_id": "t", "run_id": "r"})
    )
    (archive / "preimages.json").write_text(
        json.dumps(
            [{"path": case.target, "archive_path": ".agent/tasks/t/runs/r/source.py"}]
        )
    )
    report = {
        "status": "success",
        "explorer_mode": "locate",
        "semantic_verdict": "not_evaluated",
        "source_refs": [
            {
                "path": case.target,
                "kind": "implementation",
                "start_line": 1,
                "end_line": 1,
                "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
                "quote": case.after.rstrip("\n"),
            },
            {
                "path": test_path,
                "kind": "test",
                "start_line": 1,
                "end_line": 1,
                "source_hash": hashlib.sha256(test.read_bytes()).hexdigest(),
                "quote": "assert True",
            },
        ],
    }
    report_path = tmp_path / ".agent/explorer-report.json"
    report_path.write_text(json.dumps(report))
    result = {
        "workspace": str(tmp_path),
        "explorer_report": str(report_path),
        "case": case.name,
    }
    assert READINESS.verify_materialized_refs(result)
    report["source_refs"][0]["quote"] = "ordered.reverse()"
    report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="quote"):
        READINESS.verify_materialized_refs(result)
