"""Coverage checks are mechanical; semantic answers remain model judgments."""

import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_observation_accounting as D
import reviewer_conditional_recovery as OLD
import reviewer_fixed_observations as F
import reviewer_observation_accounting as A
import reviewer_semantic_entry as V1
import test_reviewer_semantic_entry as S


def rows(verdict="consistent"):
    return [
        {
            "profile_id": "fixed",
            "case_index": i,
            "contract_id": "behavior-1",
            "verdict": verdict,
            "explanation": "Model's explicit semantic judgment, not host inference.",
        }
        for i in range(2)
    ]


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "order",
        "boolean_index",
        "unknown_contract",
        "blank",
        "conflict",
    ],
)
def test_incomplete_or_contradictory_accounting_rejected(change):
    items = rows()
    if change == "missing":
        items.pop()
    if change == "duplicate":
        items[1]["case_index"] = 0
    if change == "order":
        items.reverse()
    if change == "boolean_index":
        items[0]["case_index"] = False
    if change == "unknown_contract":
        items[0]["contract_id"] = "other"
    if change == "blank":
        items[0]["explanation"] = " "
    if change == "conflict":
        items[0]["verdict"] = "violation"
    with pytest.raises(ValueError):
        A.validate_accounting(
            items,
            [("fixed", 0), ("fixed", 1)],
            [{"obligation_id": "behavior-1", "status": "verified"}],
            ValueError,
        )


def test_host_does_not_infer_semantics_from_text_or_manufacture_failure():
    items = rows()
    items[0]["explanation"] = (
        "Words None defect false pass do not change this explicit status."
    )
    assert (
        A.validate_accounting(
            items,
            [("fixed", 0), ("fixed", 1)],
            [{"obligation_id": "behavior-1", "status": "verified"}],
            ValueError,
        )
        == items
    )
    for status in ("violated", "uncertain"):
        assert A.validate_accounting(
            rows("violation"),
            [("fixed", 0), ("fixed", 1)],
            [{"obligation_id": "behavior-1", "status": status}],
            ValueError,
        )


def test_full_run_preserves_raw_report_and_existing_semantic_gates(tmp_path):
    request = S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(D.E.D.BATCH / "runtime/reviewer-runtime.py", "accounting_full")
    args = {**S.judgment(), "observation_assessments": rows()}
    client = S.Client(module, [{"action": "REPORT", "arguments": args}])
    client.temperature = 1
    runtime = A.install(module)(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
            "reviewer_temperature": 1,
        },
        client,
    )
    with patch.object(
        F, "facts", return_value=([{"profile_id": "fixed", "examples": [{}, {}]}], None)
    ):
        result = runtime.run()
    assert (
        result["decision"] == "pass_to_primary"
        and result["observation_assessments"] == rows()
    )
    assert client.calls == result["reviewer_model_calls"] == 1
    raw = D.B.read(runtime.review_root / "observation-response-1.json")
    assert json.loads(raw["raw"])["arguments"]["observation_assessments"] == rows()
    assert client.messages[0][0]["content"] == V1.SYSTEM
    assert client.native_tools == A.TOOLS
    assert "observation_assessments" not in V1.PARAMS["properties"]


def test_twenty_inputs_unchanged_before_live():
    for row in D.B.read(D.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        assert not (root / ".agent/current-task.json").exists()
        assert row["identity"]["review_id"].startswith("accounting-v1-")
        D.R.assert_files(root, row["files"])
        bundles = []
        for adapter in (OLD, A):
            module = D.R.load(
                root / ".local-agents/reviewer-runtime.py",
                "accounting_input_" + row["id"] + adapter.__name__,
            )
            runtime = adapter.install(module)(
                root,
                {
                    **row["identity"],
                    "review_id": "offline-" + adapter.__name__ + row["id"],
                },
                D.B.read(root / ".agent/experiment-config.json"),
                S.Client(module),
            )
            bundles.append(runtime.bundle())
        assert bundles[0] == bundles[1]
    old = copy.deepcopy(V1.PARAMS)
    new = copy.deepcopy(A.PARAMS)
    new["required"].remove("observation_assessments")
    new["properties"].pop("observation_assessments")
    assert old == new


def test_missing_observation_uses_existing_correction_budget_not_auto_verdict(tmp_path):
    request = S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(
        D.E.D.BATCH / "runtime/reviewer-runtime.py", "accounting_correction"
    )
    missing = {"action": "REPORT", "arguments": S.judgment()}
    corrected = {
        "action": "REPORT",
        "arguments": {**S.judgment(), "observation_assessments": rows()},
    }
    client = S.Client(module, [missing, corrected])
    client.temperature = 1
    runtime = A.install(module)(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
            "reviewer_temperature": 1,
        },
        client,
    )
    with patch.object(
        F, "facts", return_value=([{"profile_id": "fixed", "examples": [{}, {}]}], None)
    ):
        result = runtime.run()
    assert (
        result["decision"] == "pass_to_primary" and result["reviewer_model_calls"] == 2
    )
    assert runtime.protocol_errors == 1
    assert "observation_assessments" in client.messages[1][-1]["content"]
    assert (runtime.review_root / "observation-response-1.json").exists()
    assert (runtime.review_root / "observation-response-2.json").exists()
