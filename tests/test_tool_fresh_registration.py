import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from tool_native_repair_history_trial import assert_fresh_inputs


def test_fresh_source_and_feedback_must_match_registration(tmp_path):
    frozen, root = tmp_path / "fixture", tmp_path / "arm"
    target = "src/agent_runtime/tools/registry.py"
    for directory in (frozen, root):
        (directory / target).parent.mkdir(parents=True)
        (directory / target).write_text("original\n", encoding="utf-8")
    packet = root / ".agent/compat-packet.json"
    packet.parent.mkdir()
    packet.write_text(json.dumps({"review_feedback": []}), encoding="utf-8")
    assert_fresh_inputs(root, frozen)
    (root / target).write_text("previous-model-draft\n", encoding="utf-8")
    with pytest.raises(ValueError, match="identical frozen"):
        assert_fresh_inputs(root, frozen)
    (root / target).write_text("original\n", encoding="utf-8")
    packet.write_text(
        json.dumps({"review_feedback": [{"text": "repair"}]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="previous failure"):
        assert_fresh_inputs(root, frozen)
