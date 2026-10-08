"""New composition of qualified label/async families, not an unseen-repo claim."""

INITIAL = {
    "src/product/__init__.py": "",
    "src/product/labels.py": "def normalize_labels(labels):\n    return list(labels)\n",
    "src/product/collector.py": "async def collect_values(fetch, keys):\n    return []\n",
    "src/product/target.py": "from product.labels import normalize_labels\nfrom product.collector import collect_values\n\nasync def labelled_receipt(fetch, labels):\n    cleaned=normalize_labels(labels)\n    values=await collect_values(fetch,labels)\n    return {'labels':cleaned,'values':values,'count':len(labels)}\n",
    "src/product/entry.py": "from product.target import labelled_receipt\n\nasync def run_batch(fetch, labels):\n    return await labelled_receipt(fetch, labels)\n",
}
REFERENCE = {
    "src/product/labels.py": "def normalize_labels(labels):\n    return [value for label in labels if (value := label.strip())]\n",
    "src/product/collector.py": "async def collect_values(fetch, keys):\n    values=[]\n    for key in keys:\n        values.append(await fetch(key))\n    return values\n",
    "src/product/target.py": "from product.labels import normalize_labels\nfrom product.collector import collect_values\n\nasync def labelled_receipt(fetch, labels):\n    cleaned=normalize_labels(labels)\n    values=await collect_values(fetch,cleaned)\n    return {'labels':cleaned,'values':values,'count':len(values)}\n",
}
TESTS = """import asyncio
import pytest
from product.labels import normalize_labels
from product.collector import collect_values
from product.entry import run_batch

def test_normalize():
    source=[' A ','','  ','A','b\t','0']
    assert normalize_labels(source)==['A','A','b','0']
    assert source==[' A ','','  ','A','b\t','0']

def test_empty_labels():
    assert normalize_labels([])==[]
    assert normalize_labels([' ','\t'])==[]

def test_collect_order():
    calls=[]
    values=[None,False,0,'',9]
    keys=list(range(5))
    async def fetch(key):
        calls.append(key)
        return values[key]
    out=asyncio.run(collect_values(fetch,keys))
    assert out==values and [type(v) for v in out]==[type(v) for v in values]
    assert calls==keys and keys==list(range(5))

def test_collect_error():
    calls=[]
    error=RuntimeError('same')
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
    labels=[' a ',' ','b','c','d','a']
    async def fetch(key):
        calls.append(key)
        return {'a':None,'b':False,'c':0,'d':''}[key]
    out=asyncio.run(run_batch(fetch,labels))
    assert out=={'labels':['a','b','c','d','a'],'values':[None,False,0,'',None],'count':5}
    assert [type(v) for v in out['values']]==[type(None),bool,int,str,type(None)]
    assert calls==['a','b','c','d','a'] and labels==[' a ',' ','b','c','d','a']

def test_batch_empty():
    calls=[]
    async def fetch(key):
        calls.append(key)
        return 9
    for labels in ([],[' ','\t']):
        assert asyncio.run(run_batch(fetch,labels))=={'labels':[],'values':[],'count':0}
    assert calls==[]

def test_batch_error():
    calls=[]
    error=RuntimeError('same')
    async def fetch(key):
        calls.append(key)
        if key=='b':
            raise error
        return 0
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(run_batch(fetch,[' a ','b','c']))
    assert caught.value is error and calls==['a','b']
"""


def case():
    observables = {
        "test_normalize": {
            "input": [" A ", "", "  ", "A", "b\t", "0"],
            "result": ["A", "A", "b", "0"],
            "input_unchanged": True,
        },
        "test_empty_labels": {"inputs": [[], [" ", "\t"]], "result": []},
        "test_collect_order": {
            "fetched_values": [None, False, 0, "", 9],
            "result": [None, False, 0, "", 9],
            "types_preserved": True,
            "call_order": [0, 1, 2, 3, 4],
            "input_unchanged": True,
        },
        "test_collect_error": {
            "keys": [0, 1, 2],
            "error_at_key": 1,
            "call_order": [0, 1],
            "raised_same_instance": True,
        },
        "test_batch_roundtrip": {
            "input_labels": [" a ", " ", "b", "c", "d", "a"],
            "normalized_labels": ["a", "b", "c", "d", "a"],
            "values": [None, False, 0, "", None],
            "count": 5,
            "types_preserved": True,
            "input_unchanged": True,
        },
        "test_batch_empty": {
            "input_labels": [" ", "\t"],
            "result": {"labels": [], "values": [], "count": 0},
            "fetch_calls": 0,
        },
        "test_batch_error": {
            "input_labels": [" a ", "b", "c"],
            "error_at_key": "b",
            "call_order": ["a", "b"],
            "raised_same_instance": True,
        },
    }
    contracts = [
        (
            "normalize-unit",
            "src/product/labels.py",
            "normalize_labels",
            [],
            ["test_normalize", "test_empty_labels"],
            "normalize_labels strips leading/trailing whitespace and drops only resulting empty strings, preserving order, duplicates, case and the input list. Inputs are lists of strings. Pending downstream receipt is separately owned.",
        ),
        (
            "collect-unit",
            "src/product/collector.py",
            "collect_values",
            [],
            ["test_collect_order", "test_collect_error"],
            "collect_values sequentially awaits fetch once per key in order, preserves every result and type including None/False/zero/empty string and the input. Same exception propagates and stops further calls; no retries or parallelism. Pending labelled_receipt is separately owned.",
        ),
        (
            "receipt-unit",
            "src/product/target.py",
            "labelled_receipt",
            ["normalize-unit", "collect-unit"],
            ["test_batch_roundtrip", "test_batch_empty", "test_batch_error"],
            "labelled_receipt normalizes labels with accepted normalize_labels once, then awaits accepted collect_values once on that normalized list. Returns labels=normalized list, values=collected list, count=len(collected list). Keep false-valued results/types, duplicate normalized keys and order; preserve input. Empty normalized keys produce all-empty receipt with no fetch. Same exception propagates and prevents later fetches. Public run_batch delegates to labelled_receipt. Do not edit accepted producers or public entry.",
        ),
    ]
    return {
        "case_id": "labelled-receipt",
        "origin": "new-composition-of-qualified-families",
        "goal": "Normalize a labelled batch, fetch every normalized label in order, and return its complete read-only receipt through the public entry.",
        "feature_risk": "medium",
        "integration_risk": "medium",
        "files": {**INITIAL, "tests/test_target.py": TESTS},
        "units": [
            {
                "unit_id": uid,
                "risk": "medium",
                "dependencies": deps,
                "path": path,
                "anchor": anchor,
                "tests": ["tests/test_target.py::" + t for t in tests],
                "contract": text,
                "acceptance_scenarios": [
                    {
                        "id": t.replace("_", "-"),
                        "text": "Protected observable "
                        + t
                        + " holds under the owned contract.",
                        "observables": observables[t],
                    }
                    for t in tests
                ],
            }
            for uid, path, anchor, deps, tests, text in contracts
        ],
    }
