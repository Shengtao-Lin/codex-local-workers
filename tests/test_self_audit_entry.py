"""Real opt-in CLI: validated identity, post-audit rechecks and bounded failure."""

import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import supervised_feedback_trial as F
import supervised_self_audit as A


def setup_cell(tmp_path):
    row = S.read(F.OLD / "cells.json")["ids-1"]
    root = tmp_path / "isolated"
    for name, digest in row["files"].items():
        source = Path(row["root"]) / name
        if name == row["target"]:
            source = F.OLD / "templates/ids" / name
        assert S.sha(source) == digest
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    reference = (F.OLD / "reference-checks/ids" / row["target"]).read_text(
        encoding="utf-8"
    )
    return root, row, reference


def execute(root, proposals):
    replay = root.parent / "replay.json"
    S.save(replay, [{"replacement": value} for value in proposals])
    result = T.run(A.command(root, replay=replay), root, timeout=180)
    S.save(root.parent / "process.json", result)
    return result, S.read(root / ".agent/unit-report.json")


def test_unchanged_audit_requires_real_successful_write_check(tmp_path):
    root, _, reference = setup_cell(tmp_path)
    result, report = execute(root, [reference, reference])
    assert result["exit_code"] == 0, result
    counts = report["consolidated_harness"]["actual"]
    assert (counts["requests"], counts["edits"], counts["post_edit_checks"]) == (
        2,
        1,
        1,
    )
    assert counts["audit_requests"] == counts["audit_unchanged"] == 1
    summary = S.read(root / ".agent/unit-summary.json")
    assert summary["reviewer_input_authenticated"] is True
    assert summary["reviewer_started"] is False


def test_audit_change_invalidates_and_rechecks_current_version(tmp_path):
    root, _, reference = setup_cell(tmp_path)
    revised = re.sub(r"\bdigest\b", "digest_value", reference)
    result, report = execute(root, [reference, revised, revised])
    assert result["exit_code"] == 0, result
    counts = report["consolidated_harness"]["actual"]
    assert (counts["edits"], counts["post_edit_checks"], counts["audit_requests"]) == (
        2,
        2,
        2,
    )


def test_failed_noop_never_becomes_audited_handoff(tmp_path):
    root, row, _ = setup_cell(tmp_path)
    original = (root / row["target"]).read_text(encoding="utf-8")
    result, report = execute(root, [original, original])
    assert result["exit_code"] != 0
    assert report["status"] == "failed"
    counts = report["consolidated_harness"]["actual"]
    assert counts["noops"] == 2 and counts["audit_requests"] == 0
    assert not S.read(root / ".agent/unit-summary.json")["reviewer_started"]


def test_audit_cannot_expand_import_authority(tmp_path):
    root, _, reference = setup_cell(tmp_path)
    bad = "import os\n" + reference
    result, report = execute(root, [reference, bad, bad, bad])
    assert result["exit_code"] != 0
    assert report["consolidated_harness"]["actual"]["edits"] == 1
    assert report["status"] == "failed"


@pytest.mark.parametrize("last_unchanged", [False, True])
def test_three_edit_ceiling_still_allows_only_unchanged_valid_audit(
    tmp_path, last_unchanged
):
    root, _, reference = setup_cell(tmp_path)
    revisions = [
        re.sub(r"\bdigest\b", name, reference)
        for name in ("digest_a", "digest_b", "digest_c")
    ]
    revisions.append(
        revisions[-1]
        if last_unchanged
        else re.sub(r"\bdigest\b", "digest_d", reference)
    )
    result, report = execute(root, revisions)
    counts = report["consolidated_harness"]["actual"]
    assert counts["edits"] == counts["post_edit_checks"] == 3
    assert (result["exit_code"] == 0) == last_unchanged
    assert (report["status"] == "validation_passed_pending_review") == last_unchanged
