"""Compaction preserves actual failure messages, not inferred repair advice."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import tool_context_compact_trial as trial
import tool_context_salience_trial as salience


def test_position_only_transform_retains_all_values_and_does_not_mutate_input():
    payload = {
        "packet": {"required_behavior": ["off-thread"]},
        "files": {"a": "source"},
        "baseline": {"exit": 1},
    }
    moved = salience.contract_last(payload)
    assert moved == payload
    assert list(moved)[-1] == "packet"
    assert next(iter(payload)) == "packet"


def test_all_actual_nonpasses_and_exact_messages_are_retained(tmp_path):
    folder = tmp_path / ".agent"
    folder.mkdir()
    (folder / "baseline.json").write_text("{}", encoding="utf-8")
    (folder / "baseline.xml").write_text(
        '<testsuite><testcase classname="unit" name="one"><failure message="bad &amp; exact">repeated frame</failure></testcase>'
        '<testcase classname="unit" name="two"><error message="broken"/></testcase>'
        '<testcase name="skip"><skipped message="unavailable"/></testcase>'
        '<testcase name="pass"/></testsuite>',
        encoding="utf-8",
    )
    result = trial.compact({"argv": ["pytest"], "exit": 1}, tmp_path)
    assert result["tests"] == 4
    assert result["executed"] == 3
    assert [f["message"] for f in result["observed_nonpasses"]] == [
        "bad & exact",
        "broken",
        "unavailable",
    ]
    assert result["argv"] == ["pytest"]
    assert "repeated frame" not in str(result)
