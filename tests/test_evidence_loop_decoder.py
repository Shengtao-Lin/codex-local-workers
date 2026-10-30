import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import evidence_loop_rules as R
import static_focus_rules as A


@pytest.mark.parametrize(
    "value",
    [
        {"replacement": "def f(): return 1"},
        {"replacement": "def f(): return 1", "blocked_reason": None},
        {"replacement": None, "blocked_reason": "missing scope"},
    ],
)
def test_proposal_normalization_is_identical_to_a(value):
    raw = json.dumps(value)
    assert R.decode(raw) == A.decode(raw)


@pytest.mark.parametrize(
    "raw",
    [
        '{"replacement":"a","replacement":"b"}',
        '{"read":{"path":"x"},"replacement":"a"}',
        '{"shell":"echo bad"}',
        '{"read":{"path":"x"},"read":{"path":"y"}}',
    ],
)
def test_no_duplicate_mixed_or_unapproved_action(raw):
    with pytest.raises(ValueError):
        R.decode(raw)
