"""Post-live controls: completion indexes are outputs, not forbidden inputs."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r4_reviewer as H


def test_frozen_inputs_and_runtime_still_unchanged():
    registry = H.B.read(H.BATCH / "registration.json")
    H.R.assert_files(H.B.KIT, registry["candidate_and_driver"])
    for row in registry["cells"]:
        H.R.assert_files(Path(row["root"]), row["files"])


def test_completion_indexes_are_fresh_outputs_only():
    for row in H.B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        cell = root.parent
        report = H.B.read(cell / "reviewer.json")
        index = root / ".agent/current-task.json"
        assert ".agent/current-task.json" not in row["files"]
        if report["decision"] == "failed":
            assert not index.exists()
            continue
        state = H.B.read(index)
        assert state["latest_review_id"] == row["identity"]["review_id"]
        assert state["usage"] == {"reviewer_calls": 1}
        assert len(state["recent_attempts"]) == 1
        assert state["recent_attempts"][0]["result"] == report["decision"]
        assert (
            datetime.fromisoformat(state["updated_at"]).timestamp()
            >= H.B.read(cell / "started.json")["at"]
        )


def test_no_primary_answers_or_completion_indexes_in_model_requests():
    for row in H.B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        for name in (".agent/primary-control-adjudication.json", "registration.json"):
            assert not (root / name).exists()
        requests = list((root.parent / "wire").glob("*-request.json"))
        assert requests
        for path in requests:
            messages = H.B.read(path).get("body", {}).get("messages", [])
            trusted_context = json.dumps(
                [m for m in messages if m.get("role") != "assistant"]
            )
            for forbidden in (
                "primary-adjudications.json",
                "expected_decision",
                "expected_defect_primary_only",
                ".agent/current-task.json",
            ):
                assert forbidden not in trusted_context


def test_closure_retains_transfer_failure_and_all_registered_cells():
    decision = H.B.read(H.H.BATCH / "decision.json")
    assert decision["qualification"] == "HOLD"
    assert not decision["r5_admitted"] and not decision["product_default_enabled"]
    rows = H.B.read(H.H.BATCH / "grid-results.json")
    assert len(rows) == 12
    assert sum(row.get("status") == "NOT_RUN" for row in rows) == 6
    assert sum(row["accepted"] for row in rows) == 4
    screen = H.B.read(H.BATCH / "grid-results.json")
    assert len(screen) == 16
    assert sum(row["primary_adjudication"]["correct"] for row in screen) == 15
    failed = [row for row in screen if not row["primary_adjudication"]["correct"]]
    assert failed[0]["id"] == "required-coverage-r1"
    assert failed[0]["observed"] == "failed"


def test_semantic_counterexample_does_not_rewrite_original_tests():
    reference = H.B.read(H.H.BATCH / "reference-falsy-probe.json")
    candidate = H.B.read(H.H.BATCH / "candidate-falsy-probe.json")
    assert reference["source_unchanged"] and candidate["source_unchanged"]
    assert all(row["satisfies_explicit_falsy_contract"] for row in reference["rows"])
    failed = [
        row for row in candidate["rows"] if not row["satisfies_explicit_falsy_contract"]
    ]
    assert len(failed) == 1 and failed[0]["input_result"] is None
    assert all(row["input_unchanged"] for row in candidate["rows"])
