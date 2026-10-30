import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import consolidated_entry as E


def test_actual_non_ascii_review_report_is_utf8_not_host_locale():
    path = (
        Path(__file__).resolve().parents[1]
        / "benchmarks/work/harness-convergence/supervised-feedback-20261019-1/cells/ids-1/isolated/.agent/reviewer-report.json"
    )
    with pytest.raises((UnicodeError, json.JSONDecodeError)):
        json.loads(path.read_text(encoding="cp936"))
    assert E.read_review_decision(path) == "pass_to_primary"


@pytest.mark.parametrize("value", [{"decision": "invented"}, {"findings": []}])
def test_invalid_report_does_not_become_pass(value, tmp_path):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises((ValueError, KeyError)):
        E.read_review_decision(path)
