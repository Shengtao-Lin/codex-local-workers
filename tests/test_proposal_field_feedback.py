"""Check rejection parity, useful repair feedback and real installed recovery."""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
import proposal_field_feedback as C

SPEC = importlib.util.spec_from_file_location(
    "installed_feedback_protocol", KIT / ".local-agents/bounded/harness_protocol.py"
)
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


@pytest.mark.parametrize("value", [
    {"replacement": "def f():\n    return 1\n"},
    {"replacement": "x", "blocked_reason": None},
    {"blocked_reason": "need approved dependency"},
    {"replacement": ["def f():", "    return 1"]},
    {"replacement": False}, {"replacement": 3}, {"replacement": {}},
    {"replacement": ""}, {"blocked_reason": []},
    {"replacement": "x", "blocked_reason": "y"},
    {"replacement": "x", "shell": "anything"}, [], {}, None,
])
def test_original_acceptance_is_unchanged(value):
    raw = json.dumps(value)
    try:
        expected = P.decode(raw)
    except ValueError:
        with pytest.raises(ValueError):
            C.wrap_decode(P.decode)(raw)
    else:
        assert C.wrap_decode(P.decode)(raw) == expected


@pytest.mark.parametrize("raw", [
    '{"replacement":"x","replacement":"y"}', '{"replacement":',
])
def test_malformed_and_duplicate_keys_remain_rejected(raw):
    with pytest.raises(ValueError):
        C.wrap_decode(P.decode)(raw)


def test_type_feedback_is_specific_bounded_and_has_no_algorithm_hint():
    with pytest.raises(ValueError) as caught:
        C.wrap_decode(P.decode)('{"replacement":["untrusted source"]}')
    text = str(caught.value)
    assert "replacement" in text and "received array" in text
    assert "No proposal was applied" in text and len(text) < 500
    assert "untrusted source" not in text


def test_installed_recovery_uses_feedback_without_spending_edit_check_slots():
    with tempfile.TemporaryDirectory(prefix="feedback-control-") as directory:
        _installed_recovery(Path(directory))


def _installed_recovery(tmp_path):
    from test_installable_bounded import archive, project, run
    import limited_family_trial as L
    import bounded_evidence_support as S

    project(tmp_path, "labels", "feedback-offline")
    target = tmp_path / ".local-agents/bounded/harness_protocol.py"
    # This is an isolated pytest fixture; production is never changed.
    source = target.read_text(encoding="utf-8")
    adapter = tmp_path / ".local-agents/bounded/proposal_field_feedback.py"
    adapter.write_bytes(Path(C.__file__).read_bytes())
    target.write_text(source + "\nfrom .proposal_field_feedback import wrap_decode\ndecode = wrap_decode(decode)\n", encoding="utf-8")
    result = run(tmp_path, [
        {"replacement": ["invalid array"]},
        {"replacement": L.TASKS["labels"]["reference"]},
    ])
    assert result.returncode == 0, result.stderr
    report = S.read(tmp_path / ".agent/unit-report.json")
    actual = report["consolidated_harness"]["actual"]
    assert actual["requests"] == 2 and actual["protocol_recoveries"] == 1
    assert actual["edits"] == actual["post_edit_checks"] == 1
    request = S.read(archive(tmp_path) / "proposal-request-2.json")
    assert "received array" in request["messages"][1]["content"]
    assert report["status"] == "validation_passed_pending_review"
