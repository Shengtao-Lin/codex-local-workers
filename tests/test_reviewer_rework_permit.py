import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_support as S
import reviewer_rework_permit as P
import supervised_repair_phase as OLD


def evidence():
    row = S.read(OLD.BATCH / "cells.json")["json-2"]
    root = Path(row["root"])
    packet = S.read(root / ".agent/packet.json")
    report = S.read(root / ".agent/reviewer-report.json")
    return root, packet, report


def test_actual_json_recommendation_is_eligible_not_confirmed():
    root, packet, report = evidence()
    feedback = P.eligibility(root, packet, report, {"decision": "rework"})
    assert "not a confirmed defect" in feedback[0]["text"]
    assert report["findings"][0]["evidence"] in feedback[0]["text"]
    assert report["findings"][0]["suggested_fix"] in feedback[0]["text"]
    assert feedback[0]["verify_in_review"] is False


@pytest.mark.parametrize(
    "change",
    [
        {"category": "contract_conflict"},
        {"category": "required_test_gap"},
        {"path": "tests/test_contract.py"},
        {"path": "../escape.py"},
        {"contract_id": "foreign"},
        {"line": None},
        {"line": 999999},
    ],
)
def test_unbounded_or_unsupported_findings_stay_primary(change):
    root, packet, report = evidence()
    report["findings"][0].update(change)
    with pytest.raises(ValueError):
        P.eligibility(root, packet, report, {"decision": "rework"})


def test_escalation_and_incomplete_report_are_not_retry_candidates():
    root, packet, report = evidence()
    for decision in ("escalate", "failed", "pass_to_primary"):
        bad = copy.deepcopy(report)
        bad["decision"] = decision
        with pytest.raises(ValueError):
            P.eligibility(root, packet, bad, {"decision": decision})


def test_stale_read_evidence_fails_closed():
    root, packet, report = evidence()
    path = next(iter(report["runtime_facts"]["observed_read_hashes"]))
    report["runtime_facts"]["observed_read_hashes"][path] = "stale"
    with pytest.raises(ValueError):
        P.eligibility(root, packet, report, {"decision": "rework"})


def test_parent_effective_edits_are_not_replenished():
    root, _, _ = evidence()
    parent = S.read(root / ".agent/unit-report.json")
    remaining = P.credits(parent)
    assert remaining["edits"] == remaining["post_edit_checks"] == 1
    assert remaining["requests"] == 10
    parent["consolidated_harness"]["actual"]["edits"] = 3
    with pytest.raises(ValueError):
        P.credits(parent)


def test_hook_does_not_touch_production_and_default_is_closed(tmp_path):
    runtime = tmp_path / ".local-agents/worker-runtime.py"
    runtime.parent.mkdir(parents=True)
    original = S.KIT / ".local-agents/worker-runtime.py"
    before = S.sha(original)
    shutil.copyfile(original, runtime)
    facts = P.install_hook(runtime, tmp_path)
    assert facts["before"] == before and facts["after"] != before
    text = runtime.read_text(encoding="utf-8")
    assert "reviewer_rework_authorizer is None" in text
    assert "Reviewer-based inherited rework requires Primary disposition" in text
    assert S.sha(original) == before
    with pytest.raises(ValueError):
        P.install_hook(original, tmp_path)


def test_locator_projection_removes_interpretation_without_rewriting_report():
    _, _, report = evidence()
    before = copy.deepcopy(report)
    projected = P.locator_feedback(report)
    text = json.loads(projected[0]["text"])
    assert set(text) == {"path", "line", "category"}
    assert report == before
    assert report["findings"][0]["evidence"] not in projected[0]["text"]
    assert report["findings"][0]["suggested_fix"] not in projected[0]["text"]


def test_projection_keeps_all_findings_without_semantic_selection():
    _, _, report = evidence()
    extra = copy.deepcopy(report["findings"][0])
    extra["id"] = "F2"
    report["findings"].append(extra)
    assert [f["finding_id"] for f in P.locator_feedback(report)] == ["F1", "F2"]


def test_projection_grants_no_new_review_obligation():
    _, _, report = evidence()
    for projected in P.locator_feedback(report):
        assert projected["verify_in_review"] is False
        assert projected["contract_id"] in {
            f["contract_id"] for f in report["findings"]
        }
