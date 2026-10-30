"""Replay real transport failures and keep semantic/safety authority unchanged."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_semantic_transport as D
import reviewer_semantic_entry as V1
import reviewer_semantic_transport as A
import test_reviewer_semantic_entry as S


def create(row, suffix):
    root = Path(row["root"])
    module = D.R.load(
        root / ".local-agents/reviewer-runtime.py", "transport_control_" + suffix
    )
    runtime = A.install(module)(
        root,
        {**row["identity"], "review_id": "offline-" + suffix},
        D.B.read(root / ".agent/experiment-config.json"),
        S.Client(module),
    )
    runtime.bundle()
    return runtime, module


def test_twenty_inputs_preserved_and_preconditions_before_live():
    rows = D.B.read(D.BATCH / "registration.json")["cells"]
    assert len(rows) == 20
    for row in rows:
        root = Path(row["root"])
        D.R.assert_files(root, row["files"])
        D.R.assert_files(Path(row["origin"]), row["origin_files"])
        assert not (root / ".agent/current-task.json").exists()
        for path, digest in row["same_session_control"].items():
            assert D.B.sha(Path(path)) == digest
        runtime, _ = create(row, row["id"])
        assert runtime.max_turns == 16 and runtime.max_protocol_errors == 4
        assert (
            runtime.required_reads_complete()
            and not runtime.coverage_facts()["missing"]
        )
        assert D.B.read(root / ".agent/experiment-config.json") == D.B.read(
            Path(row["origin"]) / ".agent/experiment-config.json"
        )


@pytest.mark.parametrize("number", [11, 12])
def test_all_four_real_failed_reports_replay_without_semantic_changes(number):
    row = next(
        r
        for r in D.B.read(D.BATCH / "registration.json")["cells"]
        if r["id"] == f"sample-{number:02}-candidate"
    )
    runtime, module = create(row, f"replay-{number}")
    origin = Path(row["origin"])
    review = origin / ".agent/tasks" / row["identity"]["task_id"] / "reviews"
    responses = sorted(review.glob("*/semantic-response-*.json"))
    assert len(responses) == 4
    for response in responses:
        args = module.WORKER.parse_action(D.B.read(response)["raw"])["arguments"]
        original = copy.deepcopy(args)
        normalized = A.assemble(runtime, args, module.ReviewError)
        report = runtime.validate_report(normalized)
        assert report["decision"] == "rework" and args == original
        finding = report["findings"][0]
        assert finding["path"] == "tests/test_target.py"
        assert finding["evidence"] == args["obligations"][0]["explanation"]
        assert finding["suggested_fix"] == args["obligations"][0]["fix"]
        assert finding["line"] == args["obligations"][0]["line"]


def test_real_confirmed_defect_is_not_replaced_by_attached_test_uncertainty():
    row = next(
        r
        for r in D.B.read(D.BATCH / "registration.json")["cells"]
        if r["id"] == "sample-16-candidate"
    )
    runtime, module = create(row, "route-replay")
    args = D.B.read(Path(row["origin"]).parent / "reviewer.json")["semantic_verdicts"]
    assert args["obligations"][0]["verdict"] == "implementation_defect"
    normalized = A.assemble(runtime, args, module.ReviewError)
    report = runtime.validate_report(normalized)
    assert report["decision"] == "rework" and report["findings"]
    assert report["unverified_claims"] == [r["text"] for r in args["uncertainties"]]
    assert report["contract_review"][0]["status"] == "violated"


@pytest.mark.parametrize(
    "kind,decision",
    [
        ("satisfied", "pass_to_primary"),
        ("uncertain", "escalate"),
        ("contract_conflict", "escalate"),
        ("implementation_defect", "rework"),
        ("required_test_gap", "rework"),
    ],
)
def test_original_explicit_states_still_control_disposition(tmp_path, kind, decision):
    runtime, module, _ = S.make(tmp_path)
    runtime.bundle()
    args = S.judgment(kind)
    result = runtime.validate_report(A.assemble(runtime, args, module.ReviewError))
    assert result["decision"] == decision


def test_owned_uncertainty_still_prevents_pass_and_no_keyword_inference(tmp_path):
    runtime, module, _ = S.make(tmp_path)
    runtime.bundle()
    args = S.judgment()
    args["uncertainties"] = [
        {"contract_id": "behavior-1", "text": "Owned requirement unresolved."}
    ]
    with pytest.raises(module.ReviewError, match="satisfied contradicts"):
        A.assemble(runtime, args, module.ReviewError)
    args["uncertainties"][0]["contract_id"] = None
    args["uncertainties"][0]["text"] = "Optional None test suggestion."
    assert (
        runtime.validate_report(A.assemble(runtime, args, module.ReviewError))[
            "decision"
        ]
        == "pass_to_primary"
    )


@pytest.mark.parametrize(
    "change",
    ["no_selected_test", "ambiguous_test", "unread", "outside", "null_implementation"],
)
def test_locator_cannot_invent_source_or_choose_ambiguous_file(tmp_path, change):
    runtime, module, _ = S.make(tmp_path)
    runtime.bundle()
    args = S.judgment(
        "required_test_gap"
        if change in {"no_selected_test", "ambiguous_test"}
        else "implementation_defect"
    )
    row = args["obligations"][0]
    if change == "no_selected_test":
        row["line"] = None
    elif change == "ambiguous_test":
        row["line"] = None
        row["evidence_ids"] = ["E1", "E2"]
        runtime.focused_test_paths = lambda: ["src/example.py", "tests/test_example.py"]
    elif change == "unread":
        row["evidence_ids"] = ["E999"]
    elif change == "outside":
        row["line"] = 999
    else:
        row["line"] = None
    with pytest.raises(module.ReviewError):
        A.assemble(runtime, args, module.ReviewError)


def test_same_prompt_and_shared_run_budget_unchanged(tmp_path):
    request = S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(D.E.D.BATCH / "runtime/reviewer-runtime.py", "transport_fullrun")
    args = S.judgment()
    client = S.Client(module, [{"action": "REPORT", "arguments": args}])
    runtime = A.install(module)(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
        },
        client,
    )
    original = V1.assemble
    report = runtime.run()
    assert V1.assemble is original
    assert client.calls == report["reviewer_model_calls"] == 1
    assert client.messages[0][0]["content"] == V1.SYSTEM
    assert report["semantic_verdicts"] == args
    assert report["semantic_transport_protocol"] == A.PROTOCOL
    assert report["decision"] == "pass_to_primary"
