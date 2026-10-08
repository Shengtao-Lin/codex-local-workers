"""Mixed numeric-key boundary with a two-file parser unit and async consumer."""

import copy

import coordinator_label_case as label

INITIAL = {
    **label.INITIAL,
    "src/product/schema.py": "def parse_code(text):\n    return 0\n",
}
REFERENCE = {
    **label.REFERENCE,
    "src/product/schema.py": "def parse_code(text):\n    return int(text, 10)\n",
    "src/product/labels.py": "from product.schema import parse_code\n\ndef normalize_labels(labels):\n    return [parse_code(text.strip()) for text in labels if text.strip()]\n",
}
TESTS = """import asyncio
import pytest
from product.schema import parse_code
from product.labels import normalize_labels
from product.collector import collect_values
from product.entry import run_batch

def test_normalize():
    source=[" 02 ",""," ","-1","2","0"]
    assert parse_code("02")==2 and parse_code("-1")==-1
    with pytest.raises(ValueError):
        parse_code("bad")
    assert normalize_labels(source)==[2,-1,2,0]
    assert source==[" 02 ",""," ","-1","2","0"]

def test_empty_labels():
    assert normalize_labels([])==[]
    assert normalize_labels([" ","\t"])==[]
    with pytest.raises(ValueError):
        normalize_labels(["1","bad","2"])

def test_collect_order():
    calls=[]
    values=[None,False,0,"",9]
    keys=list(range(5))
    async def fetch(key):
        calls.append(key)
        return values[key]
    out=asyncio.run(collect_values(fetch,keys))
    assert out==values and [type(v) for v in out]==[type(v) for v in values]
    assert calls==keys and keys==list(range(5))

def test_collect_error():
    calls=[]
    error=RuntimeError("same")
    async def fetch(key):
        calls.append(key)
        if key==1:
            raise error
        return 0
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(collect_values(fetch,[0,1,2]))
    assert caught.value is error and calls==[0,1]

def test_batch_roundtrip():
    calls=[]
    labels=[" 02 "," ","-1","0","3","2"]
    async def fetch(key):
        assert type(key) is int
        calls.append(key)
        return {2:None,-1:False,0:0,3:""}[key]
    out=asyncio.run(run_batch(fetch,labels))
    assert out=={"labels":[2,-1,0,3,2],"values":[None,False,0,"",None],"count":5}
    assert [type(v) for v in out["values"]]==[type(None),bool,int,str,type(None)]
    assert calls==[2,-1,0,3,2] and labels==[" 02 "," ","-1","0","3","2"]

def test_batch_empty():
    calls=[]
    async def fetch(key):
        calls.append(key)
        return 9
    for labels in ([],[" ","\t"]):
        assert asyncio.run(run_batch(fetch,labels))=={"labels":[],"values":[],"count":0}
    with pytest.raises(ValueError):
        asyncio.run(run_batch(fetch,["1","bad","2"]))
    assert calls==[]

def test_batch_error():
    calls=[]
    error=RuntimeError("same")
    async def fetch(key):
        calls.append(key)
        if key==-1:
            raise error
        return 0
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(run_batch(fetch,[" 02 ","-1","3"]))
    assert caught.value is error and calls==[2,-1]
"""


def case():
    result = copy.deepcopy(label.case())
    result["origin"] = "new-numeric-cross-file-composition"
    result["goal"] = (
        "Convert nonblank textual codes to integer keys before any fetching, then sequentially collect and return the complete receipt through the public entry."
    )
    result["files"] = {**INITIAL, "tests/test_target.py": TESTS}
    parser = result["units"][0]
    parser.update(
        paths=["src/product/schema.py", "src/product/labels.py"],
        anchors={
            "src/product/schema.py": "parse_code",
            "src/product/labels.py": "normalize_labels",
        },
        contract="parse_code converts a string with Python int(text, 10), propagating ValueError for malformed decimal input. normalize_labels accepts a list of strings, strips and drops whitespace-only values then converts all remaining values via parse_code before returning a list of integers. Preserve duplicates, order and original input. Any malformed nonblank value propagates ValueError. Own both existing schema and normalization files; no fetching here.",
    )
    parser["acceptance_scenarios"] = [
        {
            "id": "numeric-normal-path",
            "text": "Protected normalization and parser assertions hold.",
            "observables": {
                "input": [" 02 ", "-1", "2", "0"],
                "output": [2, -1, 2, 0],
                "input_unchanged": True,
            },
        },
        {
            "id": "numeric-error-boundary",
            "text": "Empty labels skipped; malformed nonblank code raises ValueError.",
            "observables": {"empty": [], "invalid": "bad", "exception": "ValueError"},
        },
    ]
    consumer = result["units"][2]
    consumer["contract"] = (
        "labelled_receipt calls accepted normalize_labels once to convert the entire textual input to integer keys before any fetch, then awaits accepted collect_values once with that exact normalized list. Return normalized integer labels, all collected values and their count. Preserve order, duplicates, false values/types and original input. Malformed code raises ValueError with zero fetches; empty normalized input gives empty receipt with zero fetches. Fetch exception propagates the same object and prevents later fetches. Public run_batch delegates; accepted producers and entry are read-only."
    )
    consumer["acceptance_scenarios"] = [
        {
            "id": "numeric-roundtrip",
            "text": "Protected public roundtrip consumes actual integer keys.",
            "observables": {
                "keys": [2, -1, 0, 3, 2],
                "count": 5,
                "false_values_retained": True,
            },
        },
        {
            "id": "numeric-rejection-before-io",
            "text": "Malformed input is rejected before any fetch, and empty input performs no fetch.",
            "observables": {
                "input": ["1", "bad", "2"],
                "fetch_calls": 0,
                "exception": "ValueError",
            },
        },
        {
            "id": "numeric-fetch-error",
            "text": "Error on integer key -1 propagates unchanged and stops key 3.",
            "observables": {"calls": [2, -1], "same_exception": True},
        },
    ]
    return result
