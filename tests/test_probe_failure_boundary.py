import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_probe_failure_boundary as F


@pytest.mark.parametrize(
    "reason",
    ["output_token_limit", "http_4xx", "http_5xx", "input_too_large", "timeout", None],
)
def test_only_known_output_limit_changes_stop_classification_not_failure(reason):
    value = {
        "infra_failure": True,
        "error": "retained failure",
        "parsed": None,
        "request_stats": {"rejection_reason": reason},
    }
    before = copy.deepcopy(value)
    result = F.boundary_view(F.H.BATCH / "cells/probe-01/result.json", value)
    assert result["infra_failure"] == (reason != "output_token_limit")
    assert result["error"] == "retained failure" and result["parsed"] is None
    assert value == before
    assert F.boundary_view(F.H.OLD / "cells/probe-01/result.json", value) == before


def test_actual_raw_failure_immutable():
    path = F.H.BATCH / "cells/probe-01/result.json"
    sha = F.H.B.sha(path)
    raw = F.H.B.read(path)
    assert raw["infra_failure"]
    assert not F.boundary_view(path, raw)["infra_failure"]
    assert F.H.B.sha(path) == sha and F.H.B.read(path) == raw
