"""Replayable simulated sample lookup, within qualified private helper families."""

import coordinator_numeric_case as numeric

INITIAL = numeric.INITIAL
REFERENCE = numeric.REFERENCE
TESTS = """import asyncio
import pytest
from product.schema import parse_code
from product.labels import normalize_labels
from product.collector import collect_values
from product.entry import run_batch

def test_normalize():
    source = [" +007 ", "", "\\t", "-02", "1_000", "-0", "7"]
    before = source.copy()
    assert normalize_labels(source) == [7, -2, 1000, 0, 7]
    assert source == before
    for text, expected in [("+007", 7), ("-02", -2), ("1_000", 1000), ("-0", 0)]:
        assert parse_code(text) == expected
        assert type(parse_code(text)) is int

def test_empty_labels():
    assert normalize_labels([]) == []
    assert normalize_labels([" ", "\\t", "\\n"]) == []
    for invalid in ("0x10", "1.0", "1__0", "+", "bad"):
        with pytest.raises(ValueError):
            parse_code(invalid)
        with pytest.raises(ValueError):
            normalize_labels(["7", invalid, "8"])

def test_collect_order():
    calls = []
    events = []
    values = [None, False, 0, "", {"score": 0}]
    keys = [7, -2, 1000, 0, 8]
    async def fetch(key):
        calls.append(key)
        events.append(("start", key))
        await asyncio.sleep(0)
        events.append(("end", key))
        return values[keys.index(key)]
    out = asyncio.run(collect_values(fetch, keys))
    assert out == values
    assert [type(v) for v in out] == [type(v) for v in values]
    assert out[-1] is values[-1]
    assert calls == keys == [7, -2, 1000, 0, 8]
    assert events == [(phase, key) for key in keys for phase in ("start", "end")]

def test_collect_error():
    for fail_key, expected in [(7, [7]), (-2, [7, -2])]:
        calls = []
        error = RuntimeError("backend offline")
        async def fetch(key):
            calls.append(key)
            if key == fail_key:
                raise error
            return None
        with pytest.raises(RuntimeError) as caught:
            asyncio.run(collect_values(fetch, [7, -2, 1000]))
        assert caught.value is error
        assert calls == expected

def test_batch_roundtrip():
    calls = []
    labels = [" +007 ", " ", "-02", "1_000", "-0", "7"]
    original = labels.copy()
    async def fetch(key):
        assert type(key) is int
        calls.append(key)
        return {7: None, -2: False, 1000: 0, 0: ""}[key]
    out = asyncio.run(run_batch(fetch, labels))
    assert out == {"labels": [7, -2, 1000, 0, 7], "values": [None, False, 0, "", None], "count": 5}
    assert [type(v) for v in out["values"]] == [type(None), bool, int, str, type(None)]
    assert calls == [7, -2, 1000, 0, 7]
    assert labels == original

def test_batch_empty():
    calls = []
    async def fetch(key):
        calls.append(key)
        return 9
    for labels in ([], [" ", "\\t", "\\n"]):
        assert asyncio.run(run_batch(fetch, labels)) == {"labels": [], "values": [], "count": 0}
    for invalid in ("0x10", "1.0", "1__0", "+", "bad"):
        source = ["7", invalid, "8"]
        with pytest.raises(ValueError):
            asyncio.run(run_batch(fetch, source))
        assert source == ["7", invalid, "8"]
    assert calls == []

def test_batch_error():
    calls = []
    error = LookupError("sample unavailable")
    async def fetch(key):
        calls.append(key)
        if key == -2:
            raise error
        return 0
    with pytest.raises(LookupError) as caught:
        asyncio.run(run_batch(fetch, [" +007 ", "-02", "1_000"]))
    assert caught.value is error
    assert calls == [7, -2]
"""


def case():
    result = numeric.case()
    result["origin"] = "simulated-sample-lookup-not-real-project-deployment"
    result["goal"] = (
        "Complete a private sample-query batch receipt: convert all nonblank textual "
        "sample IDs using Python int(text, 10) before I/O, query them sequentially, "
        "then return normalized IDs, all results and count through run_batch. "
        "No storage writes, external services, SQL or public API changes."
    )
    result["files"]["tests/test_target.py"] = TESTS
    parser, collector, receipt = result["units"]
    parser["contract"] += (
        " Python decimal semantics explicitly include leading plus/zeros, negative "
        "zero and single digit-separating underscores (1_000); reject hex prefixes, "
        "decimal fractions, doubled underscores and sign-only input. "
        "Pending receipt and collector behavior are separately owned."
    )
    parser["acceptance_scenarios"][0]["observables"] = {
        "input": [" +007 ", "", "\t", "-02", "1_000", "-0", "7"],
        "output": [7, -2, 1000, 0, 7],
        "input_unchanged": True,
    }
    parser["acceptance_scenarios"][1]["observables"] = {
        "empty": [],
        "invalid": ["0x10", "1.0", "1__0", "+", "bad"],
        "exception": "ValueError",
    }
    collector["acceptance_scenarios"][0]["observables"] = {
        "keys": [7, -2, 1000, 0, 8],
        "values": [None, False, 0, "", {"score": 0}],
        "strict_start_end_order": True,
        "object_identity_preserved": True,
    }
    collector["acceptance_scenarios"][1]["observables"] = {
        "error_positions": [0, 1],
        "same_instance": True,
        "no_later_calls": True,
    }
    receipt["acceptance_scenarios"][0]["observables"] = {
        "input": [" +007 ", " ", "-02", "1_000", "-0", "7"],
        "keys": [7, -2, 1000, 0, 7],
        "count": 5,
        "false_values_retained": True,
    }
    receipt["acceptance_scenarios"][1]["observables"] = {
        "invalid": ["0x10", "1.0", "1__0", "+", "bad"],
        "fetch_calls": 0,
        "exception": "ValueError",
    }
    receipt["acceptance_scenarios"][2]["observables"] = {
        "calls": [7, -2],
        "same_exception": True,
    }
    return result
