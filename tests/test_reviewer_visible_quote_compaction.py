import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_visible_quote_compaction import compact, compact_messages, source_index


def test_only_exact_visible_source_quotes_compact_not_model_judgement():
    evidence = [{"path": "src/a.py", "content": "10: value = 2\n11: return value"}]
    original = {
        "source_ref": {"path": "src/a.py", "start_line": 10, "end_line": 11},
        "canonical_quote": "value = 2\nreturn value",
        "source_quote": "value = 2\nreturn value",
        "status": "uncertain",
        "evidence": "model claim",
        "findings": [{"id": "F1", "evidence": "wrong claim"}],
    }
    frozen = copy.deepcopy(original)
    result = compact(original, source_index(evidence))
    assert "canonical_quote" not in result and "source_quote" not in result
    assert result["status"] == original["status"]
    assert result["evidence"] == original["evidence"]
    assert result["findings"] == original["findings"]
    assert result["source_ref"] == original["source_ref"]
    assert original == frozen
    for change in (
        {"canonical_quote": "not actual source"},
        {"source_ref": {"path": "src/a.py", "start_line": 10, "end_line": 12}},
        {"source_ref": {"path": "outside.py", "start_line": 10, "end_line": 11}},
    ):
        changed = {**original, **change}
        assert (
            compact(changed, source_index(evidence))["canonical_quote"]
            == changed["canonical_quote"]
        )


def test_initial_source_and_assistant_claims_are_never_compacted():
    observation = {
        "path": "a.py",
        "start_line": 1,
        "end_line": 1,
        "canonical_quote": "x",
    }
    initial = {"role": "user", "content": "LOCAL_REVIEW_INPUT\nactual source"}
    assistant = {
        "role": "assistant",
        "content": "OBSERVATION\n" + json.dumps(observation),
    }
    messages = [
        initial,
        assistant,
        {"role": "user", "content": "OBSERVATION\n" + json.dumps(observation)},
    ]
    evidence = [{"path": "a.py", "content": "1: x"}]
    result = compact_messages(messages, evidence)
    assert result[:2] == messages[:2]
    assert "canonical_quote_location" in result[2]["content"]
    assert compact_messages(messages, []) == messages
