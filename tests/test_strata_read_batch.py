import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_explorer_serial import read_batch


def call(name="READ_FILE", arguments='{"path":"approved.py"}'):
    return {"function": {"name": name, "arguments": arguments}}


def test_order_and_arguments_preserved_without_scope_authority():
    calls = [call("LIST_FILES", '{"path":"src"}'), call()]
    assert read_batch(calls) == [
        {"action": "LIST_FILES", "arguments": {"path": "src"}},
        {"action": "READ_FILE", "arguments": {"path": "approved.py"}},
    ]


@pytest.mark.parametrize(
    "calls",
    [
        [],
        [call()],
        [call()] * 5,
        [call(), call("REPORT")],
        [call(), call("SAFE_REPLACE")],
        [call(), call(arguments="[]")],
        [call(), call(arguments="invalid")],
    ],
)
def test_rejects_whole_unsafe_or_invalid_batch(calls):
    with pytest.raises((ValueError, TypeError)):
        read_batch(calls)
