"""Post-live evidence audit, independent from launch-time absence checks."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r4_evidence as E


def rows():
    return E.B.read(E.BATCH / "registration.json")["cells"]


def test_preserved_inputs_and_live_pins():
    E.prior_unchanged()
    for path, sha in E.B.read(E.BATCH / "live-freeze.json")["pins"].items():
        assert E.B.sha(Path(path)) == sha
    for row in rows():
        E.R.assert_files(Path(row["root"]), row["files"])


def test_current_indexes_are_new_one_call_outputs():
    for row in rows():
        root = Path(row["root"])
        cell = root.parent
        report = E.B.read(cell / "reviewer.json")
        index = root / ".agent/current-task.json"
        assert ".agent/current-task.json" not in row["files"]
        if report["decision"] == "failed":
            assert not index.exists()
            continue
        state = E.B.read(index)
        assert state["latest_review_id"] == row["identity"]["review_id"]
        assert state["usage"] == {"reviewer_calls": 1}
        assert len(state["recent_attempts"]) == 1
        assert (
            datetime.fromisoformat(state["updated_at"]).timestamp()
            >= E.B.read(cell / "started.json")["at"]
        )


def test_actual_wire_metadata_is_factual_not_answer_injection():
    observed = 0
    for row in rows():
        root = Path(row["root"])
        for path in (root.parent / "wire").glob("*-request.json"):
            request = E.B.read(path)
            for message in request.get("body", {}).get("messages", []):
                if message.get("role") == "assistant":
                    continue
                text = message.get("content", "")
                for token in (
                    "expected_decision",
                    "primary-adjudications.json",
                    "expected_defect_primary_only",
                    ".agent/current-task.json",
                ):
                    assert token not in text
                if not text.startswith("OBSERVATION\n"):
                    continue
                observation = json.loads(text.split("\n", 1)[1])
                if "file_extent" not in observation:
                    continue
                observed += 1
                extent = observation["file_extent"]
                file = root / observation["path"]
                raw = file.read_bytes()
                total = len(raw.decode("utf-8-sig").splitlines())
                assert extent["source_sha256"] == E.B.sha(file)
                assert (
                    extent["size_bytes"] == len(raw) and extent["total_lines"] == total
                )
                displayed = set()
                for item in observation["citation_evidence"]:
                    assert item["source_hash"] == extent["source_sha256"]
                    displayed.update(range(item["start_line"], item["end_line"] + 1))
                missing = set(range(1, total + 1)) - displayed
                assert extent["whole_file_displayed"] == (not missing)
                assert extent["first_unread_line"] == (
                    min(missing) if missing else None
                )
                assert extent["unread_line_count"] == len(missing)
                state = observation["current_evidence_state"]
                assert state["semantic_understanding"] == "not_inferred_from_display"
                assert (
                    "verified_contract_ids" not in state and "assessment" not in state
                )
    assert observed >= 32


def test_old_decisions_remain_hold():
    for batch in (E.D.BATCH, E.D.OLD.H.BATCH):
        assert E.B.read(batch / "decision.json")["qualification"] == "HOLD"
    assert E.B.read(E.D.BATCH / "decision.json")["substantively_correct"] == 15
