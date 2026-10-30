import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_explorer_arguments import arguments, batch, normalized_calls


def tool(name, args):
    return {"function": {"name": name, "arguments": json.dumps(args)}}


def test_unwrap_exact_read_envelope_without_changing_query_or_scope():
    value = {"query": "stable_message_id", "path": "../outside", "max_results": 30}
    assert arguments({"arguments": value}) == value
    assert arguments(value) is value
    assert batch(
        [tool("SEARCH", {"arguments": value}), tool("TRACE", {"symbol": "f"})]
    ) == [
        {"action": "SEARCH", "arguments": value},
        {"action": "TRACE", "arguments": {"symbol": "f"}},
    ]  # Original executor, not normalization, must reject forbidden paths.


@pytest.mark.parametrize(
    "value", [None, [], {"arguments": []}, {"arguments": {"arguments": {"query": "x"}}}]
)
def test_reject_bad_or_recursive_envelope(value):
    with pytest.raises((ValueError, TypeError)):
        arguments(value)


def test_no_ambiguous_unwrap_or_report_write_privilege():
    value = {"query": "x", "arguments": {"query": "y"}}
    assert arguments(value) is value
    for name in ("REPORT", "FINISH_SUCCESS", "SAFE_REPLACE"):
        wrapped = tool(name, {"arguments": {"query": "x"}})
        assert normalized_calls([wrapped]) == [wrapped]
        with pytest.raises(ValueError):
            batch([tool("SEARCH", {"query": "x"}), wrapped])
