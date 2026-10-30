"""Receipts shorten transport without changing execution or implying acceptance."""

import copy
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / ".local-agents"))
sys.path.insert(0, str(KIT / "benchmarks"))
import bounded_evidence_support as S
import limited_family_trial as L
from bounded import primary_receipt as R
from test_installable_bounded import archive, project


def normalized_messages(messages, root):
    """Only normalize physical workspace names and observed pytest durations."""
    text = json.dumps(messages)
    spellings = set()
    for path in (
        str(root),
        root.as_posix(),
        str(root).lower(),
        root.as_posix().lower(),
    ):
        for _ in range(3):
            spellings.add(path)
            path = json.dumps(path)[1:-1]
    for path in sorted(spellings, key=len, reverse=True):
        text = re.sub(re.escape(path), "ROOT", text, flags=re.IGNORECASE)
    return re.sub(r"(?<= in )\d+\.\d+s\b", "ELAPSED", text)


def sample():
    return {
        "status": "failed",
        "identity": {"task_id": "t", "unit_id": "u", "run_id": "r"},
        "failure_reason": "Two unchanged prepared proposals",
        "review_route": "primary_full_review",
        "risk": {"unit": "high"},
        "next_action_required": "primary_rework_or_takeover_decision",
        "validation": {
            "status": "failed",
            "focused_tests": {
                "status": "passed",
                "junit": {"tests": 15, "executed": 15, "failures": 0},
                "inputs_unchanged": True,
            },
            "configured_checks": [
                {
                    "id": "ruff-check",
                    "status": "failed",
                    "exit_code": 1,
                    "output": "invalid-syntax: exact failure",
                }
            ],
        },
        "consolidated_harness": {
            "budget": {"requests": 12},
            "actual": {"requests": 2, "edits": 0, "noops": 2},
        },
        "evidence_refs": {
            "run_archive": ".agent/tasks/t/runs/r",
            "validation_attempts": ["attempt-1.json"],
        },
    }


def test_failed_check_not_hidden_by_passing_tests_or_worker_claims():
    report = sample()
    report["worker_claims"] = {"summary": ["everything is correct"]}
    summary = {
        "reviewer_started": False,
        "reviewer_decision": "NOT_RUN",
        "automatic_coder_rework": False,
    }
    before = copy.deepcopy(report)
    receipt = R.build(report, summary, None, {"full_coder_report": "coder.json"})
    assert report == before
    assert receipt["coder_status"] == "failed"
    assert receipt["stop_reason"] == report["failure_reason"]
    assert receipt["validation"]["junit"]["executed"] == 15
    assert receipt["validation"]["configured_checks"]["items"][0]["status"] == "failed"
    assert receipt["execution"] == report["consolidated_harness"]
    assert receipt["reviewer"]["reviewer_decision"] == "NOT_RUN"
    assert receipt["primary_acceptance"] == "not_recorded_by_this_entry"
    assert receipt["review_route"] == "primary_full_review"
    assert "everything is correct" not in json.dumps(receipt)


@pytest.mark.parametrize(
    "decision",
    [
        "pass_to_primary",
        "rework",
        "escalate",
        "failed",
        "blocked",
        "interrupted",
        "NOT_RUN",
    ],
)
def test_all_decisions_are_navigation_not_acceptance(decision):
    summary = {"reviewer_decision": decision, "automatic_coder_rework": False}
    reviewer = {
        "findings": [{"id": "F1", "severity": "high", "evidence": "real concern"}],
        "unverified_claims": ["missing caller"],
    }
    receipt = R.build(sample(), summary, reviewer, {})
    assert receipt["reviewer"]["reviewer_decision"] == decision
    assert receipt["reviewer"]["findings"]["items"][0]["id"] == "F1"
    assert receipt["reviewer"]["uncertainties"]["items"] == ["missing caller"]
    assert receipt["primary_acceptance"] == "not_recorded_by_this_entry"
    assert receipt["automatic_coder_rework"] is False


def test_missing_fields_are_unknown_and_truncation_is_explicit():
    receipt = R.build({}, {}, {}, {})
    assert receipt["coder_status"] is None
    assert receipt["validation"]["junit"]["executed"] is None
    assert receipt["execution"] is None
    report = sample()
    report["failure_reason"] = "x" * 2000
    report["validation"]["configured_checks"][0]["output"] = "y" * 10000
    reviewer = {
        "findings": [{"id": f"F{i}", "evidence": "z" * 1000} for i in range(12)]
    }
    receipt = R.build(report, {}, reviewer, {})
    assert {"stop_reason", "check_0", "reviewer_findings"} <= set(
        receipt["truncated_fields"]
    )
    assert receipt["reviewer"]["findings"]["total"] == 12
    assert receipt["reviewer"]["findings"]["omitted"] == 4
    assert "truncated" in receipt["reviewer"]["findings"]["items"][0]["evidence"]


@pytest.mark.parametrize(
    "scenario", ["success", "noops", "blocked", "protocol_exhausted"]
)
def test_installed_stdout_choice_keeps_model_requests_checks_and_archive(scenario):
    with tempfile.TemporaryDirectory(prefix="primary-receipt-") as directory:
        base = Path(directory)
        rows = []
        for compact in (False, True):
            root = base / ("compact" if compact else "full")
            root.mkdir()
            project(root, "labels", "receipt-" + scenario)
            config_path = root / ".agent/config.json"
            config = S.read(config_path)
            config["bounded_compatibility_profile"] = "flat-v1"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            if scenario == "success":
                proposals = [
                    {"kind": "replacement", "content": L.TASKS["labels"]["reference"]}
                ]
            elif scenario == "blocked":
                proposals = [
                    {"kind": "blocked", "content": "missing approved caller evidence"}
                ]
            elif scenario == "protocol_exhausted":
                proposals = ["malformed output"] * 3
            else:
                proposals = [
                    {
                        "kind": "replacement",
                        "content": (root / "src/product/code.py").read_text(
                            encoding="utf-8"
                        ),
                    }
                ] * 2
            replay = root / ".agent/replay.json"
            S.save(replay, proposals)
            command = [
                str(S.PYTHON),
                "-B",
                str(root / ".local-agents/local-bounded-unit.py"),
                "--mode",
                "unit",
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
                "--replay",
                str(replay),
            ]
            if compact:
                command.append("--compact-output")
            result = subprocess.run(
                command,
                cwd=root,
                text=True,
                capture_output=True,
                encoding="utf-8",
                timeout=180,
                check=False,
            )
            assert result.returncode == (0 if scenario == "success" else 2), (
                result.stdout + result.stderr
            )
            full = S.read(root / ".agent/unit-report.json")
            summary = S.read(root / ".agent/unit-summary.json")
            stdout = json.loads(result.stdout)
            if compact:
                assert stdout["receipt_protocol"] == "bounded-primary-receipt-v1"
                assert stdout["coder_status"] == full["status"]
                assert stdout["execution"] == full["consolidated_harness"]
                assert stdout["reviewer"]["reviewer_decision"] == "NOT_RUN"
                assert stdout["primary_acceptance"] == "not_recorded_by_this_entry"
                assert len(result.stdout) < len(json.dumps(full, indent=2))
            else:
                assert stdout == full
            requests = [
                S.read(p) for p in sorted(archive(root).glob("proposal-request-*.json"))
            ]
            rows.append((root, full, summary, requests))
        one, two = rows
        assert one[1]["status"] == two[1]["status"]
        assert (
            one[1]["consolidated_harness"]["actual"]
            == two[1]["consolidated_harness"]["actual"]
        )
        assert one[2] == two[2]
        assert (one[0] / "src/product/code.py").read_bytes() == (
            two[0] / "src/product/code.py"
        ).read_bytes()
        assert len(one[3]) == len(two[3])
        for a, b in zip(one[3], two[3], strict=True):
            assert a["schema"] == b["schema"] and a["binding"] == b["binding"]
            # Check output paths are host-specific; the factual contents and
            # model-facing protocol must otherwise remain byte-for-byte equal.
            left = normalized_messages(a["messages"], one[0])
            right = normalized_messages(b["messages"], two[0])
            if left != right:
                offset = next(
                    (
                        i
                        for i, (x, y) in enumerate(zip(left, right, strict=False))
                        if x != y
                    ),
                    min(len(left), len(right)),
                )
                pytest.fail(
                    f"Observed model-input difference at {offset}: {left[max(0, offset - 100) : offset + 300]!r} versus {right[max(0, offset - 100) : offset + 300]!r}"
                )
