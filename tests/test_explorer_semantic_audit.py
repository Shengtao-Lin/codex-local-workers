from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "benchmarks/explorer_semantic_audit.py"
)
SPEC = importlib.util.spec_from_file_location(
    "explorer_semantic_audit_under_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def cell(round_number: int, *, qualified: bool = True) -> dict:
    return {
        "workspace": f"F:/work/batch/round-{round_number}/sample-identity",
        "case": "sample-identity",
        "explorer_status": "success",
        "explorer_evidence_valid": True,
        "qualified_pass": qualified,
    }


def test_audit_keeps_protocol_and_semantic_denominators_separate() -> None:
    audit = {
        "schema_version": 1,
        "ratings": [
            {"round": 1, "case": "sample-identity", "status": "correct"},
            {
                "round": 2,
                "case": "sample-identity",
                "status": "incomplete",
                "reason": "Second file omitted.",
            },
        ],
    }
    summary = {"schema_version": 1, "results": [cell(1), cell(2)]}
    assert AUDIT.summarize(audit, summary) == {
        "cells": 2,
        "ratings": {"correct": 1, "incomplete": 1},
        "explorer_mechanical": 2,
        "explorer_strict_semantic": 1,
        "protocol_e2e": 2,
        "semantic_release_qualified": 1,
    }


def test_audit_rejects_missing_cell_and_false_correct_grade() -> None:
    audit = {
        "schema_version": 1,
        "ratings": [{"round": 1, "case": "sample-identity", "status": "correct"}],
    }
    with pytest.raises(ValueError, match="missing audit cells"):
        AUDIT.summarize(audit, {"schema_version": 1, "results": [cell(1), cell(2)]})
    broken = cell(1)
    broken["explorer_evidence_valid"] = False
    with pytest.raises(ValueError, match="lacks mechanical evidence"):
        AUDIT.summarize(audit, {"schema_version": 1, "results": [broken]})


def test_audit_requires_consistent_full_diagnostic_report(tmp_path: Path) -> None:
    workspace = tmp_path / "round-1" / "sample-identity"
    agent = workspace / ".agent"
    agent.mkdir(parents=True)
    compact_path = agent / "explorer-report.json"
    full_path = agent / "explorer-runs" / "run-1" / "report.json"
    full_path.parent.mkdir(parents=True)
    compact_path.write_text(
        json.dumps(
            {
                "status": "success",
                "diagnostic_report": ".agent/explorer-runs/run-1/report.json",
                "findings_truncated": True,
            }
        ),
        encoding="utf-8",
    )
    full_path.write_text(json.dumps({"status": "success"}), encoding="utf-8")
    summary = {
        "results": [
            {
                "workspace": str(workspace),
                "explorer_report": str(compact_path),
                "explorer_status": "success",
            }
        ]
    }
    AUDIT.verify_full_reports(summary)
    full_path.write_text(json.dumps({"status": "failed"}), encoding="utf-8")
    with pytest.raises(ValueError, match="status mismatch"):
        AUDIT.verify_full_reports(summary)


def release_batch(misses: set[tuple[int, str]] = frozenset()) -> tuple[dict, dict]:
    results = []
    ratings = []
    for round_number in (1, 2):
        for index in range(11):
            case = f"case-{index}"
            result = cell(round_number)
            result["case"] = case
            result["workspace"] = f"F:/work/batch/round-{round_number}/{case}"
            results.append(result)
            failed = (round_number, case) in misses
            ratings.append(
                {
                    "round": round_number,
                    "case": case,
                    "status": "incomplete" if failed else "correct",
                    **({"reason": "Missing boundary."} if failed else {}),
                }
            )
    return (
        {"schema_version": 1, "reviewer": "Primary Agent", "ratings": ratings},
        {"schema_version": 1, "results": results},
    )


def test_release_gate_accepts_20_of_22_distinct_misses() -> None:
    audit, summary = release_batch({(1, "case-1"), (2, "case-2")})
    result = AUDIT.assess_release(audit, summary)
    assert result["explorer_gate"] == "GO"
    assert result["explorer_strict_semantic"] == 20


def test_release_gate_rejects_repeated_miss_even_at_20_of_22() -> None:
    audit, summary = release_batch({(1, "case-1"), (2, "case-1")})
    result = AUDIT.assess_release(audit, summary)
    assert result["explorer_gate"] == "NO-GO"
    assert "repeated strict miss: case-1" in result["reasons"]


def test_role_aligned_gate_keeps_incomplete_diagnoses_visible() -> None:
    audit, summary = release_batch(
        {(1, "case-1"), (1, "case-2"), (2, "case-1"), (2, "case-2")}
    )
    result = AUDIT.assess_release(audit, summary, gate_version="role-aligned-v1")
    assert result["explorer_gate"] == "GO"
    assert result["explorer_strict_semantic"] == 18
    assert result["explorer_mechanical"] == 22
    assert AUDIT.assess_release(audit, summary)["explorer_gate"] == "NO-GO"


def test_role_aligned_gate_rejects_incorrect_claim() -> None:
    audit, summary = release_batch()
    audit["ratings"][0].update(status="incorrect", reason="Invented branch behavior.")
    result = AUDIT.assess_release(audit, summary, gate_version="role-aligned-v1")
    assert result["explorer_gate"] == "NO-GO"
    assert any("incorrect source claims" in reason for reason in result["reasons"])


def test_release_gate_rejects_small_or_unmatched_sample() -> None:
    audit, summary = release_batch()
    audit["ratings"] = audit["ratings"][:2]
    summary["results"] = summary["results"][:2]
    result = AUDIT.assess_release(audit, summary)
    assert result["explorer_gate"] == "NO-GO"
    assert any("two rounds" in reason for reason in result["reasons"])

    audit, summary = release_batch()
    summary["results"][-1]["case"] = "replacement-case"
    summary["results"][-1]["workspace"] = "F:/work/batch/round-2/replacement-case"
    audit["ratings"][-1]["case"] = "replacement-case"
    result = AUDIT.assess_release(audit, summary)
    assert result["explorer_gate"] == "NO-GO"
    assert any("same case identities" in reason for reason in result["reasons"])


def test_repeat_input_check_compares_packet_manifest_and_protected_files(
    tmp_path: Path,
) -> None:
    results = []
    for round_number in (1, 2):
        workspace = tmp_path / f"round-{round_number}" / "case-a"
        (workspace / ".agent").mkdir(parents=True)
        (workspace / "tests").mkdir()
        (workspace / "src").mkdir()
        (workspace / "src" / "file.py").write_text("faulty = True\n", encoding="utf-8")
        run_id = f"case-a-round-{round_number}"
        archive = workspace / ".agent" / "tasks" / "stability-case-a" / "runs" / run_id
        (archive / "preimages" / "src").mkdir(parents=True)
        preimage = archive / "preimages" / "src" / "file.py"
        preimage.write_text("faulty = True\n", encoding="utf-8")
        (archive / "preimages.json").write_text(
            json.dumps(
                [
                    {
                        "path": "src/file.py",
                        "existed": True,
                        "archive_path": f".agent/tasks/stability-case-a/runs/{run_id}/preimages/src/file.py",
                        "sha256": hashlib.sha256(preimage.read_bytes()).hexdigest(),
                    }
                ]
            ),
            encoding="utf-8",
        )
        (workspace / "fixture-source.json").write_text(
            json.dumps([{"path": "src/file.py", "sha256": "pinned"}]),
            encoding="utf-8",
        )
        (workspace / ".agent" / "packet.json").write_text(
            json.dumps(
                {
                    "unit_id": "case-a",
                    "task_id": "stability-case-a",
                    "run_id": run_id,
                    "scope": {
                        "readonly": ["tests/test_case_a.py"],
                        "modify": ["src/file.py"],
                    },
                    "required_behavior": [{"id": "behavior-1", "text": "pinned"}],
                }
            ),
            encoding="utf-8",
        )
        (workspace / "tests" / "test_case_a.py").write_text(
            "assert True\n", encoding="utf-8"
        )
        results.append({"workspace": str(workspace), "case": "case-a"})
    summary = {"results": results}
    AUDIT.verify_repeat_inputs(summary)

    second = Path(results[1]["workspace"])
    (second / "tests" / "test_case_a.py").write_text("assert False\n", encoding="utf-8")
    with pytest.raises(ValueError, match="repeat input mismatch"):
        AUDIT.verify_repeat_inputs(summary)

    (second / "tests" / "test_case_a.py").write_text("assert True\n", encoding="utf-8")
    second_preimage = (
        second
        / ".agent"
        / "tasks"
        / "stability-case-a"
        / "runs"
        / "case-a-round-2"
        / "preimages"
        / "src"
        / "file.py"
    )
    second_preimage.write_text("faulty = False\n", encoding="utf-8")
    with pytest.raises(ValueError, match="preimage hash mismatch"):
        AUDIT.verify_repeat_inputs(summary)
