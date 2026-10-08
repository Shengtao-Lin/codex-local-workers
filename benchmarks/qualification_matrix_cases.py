"""Six previously unused supervised tasks, references and discriminating mutants."""

import copy


def corpus(template):
    specs = [
        (
            "display-default",
            "local",
            "display_name(record) returns record['name'] unchanged when present, including empty string or None; returns 'unnamed' only when key absent. Never mutate record.",
            {
                "target": "def display_name(record):\n    return record.get('name') or 'unnamed'\n"
            },
            {
                "target": "def display_name(record):\n    return record.get('name', 'unnamed')\n"
            },
            "from product.target import display_name\n\ndef test_present():\n    assert display_name({'name':'Ada'}) == 'Ada'\n    assert display_name({'name':''}) == ''\n    assert display_name({'name':None}) is None\n\ndef test_missing_and_input():\n    data = {'other':1}\n    assert display_name(data) == 'unnamed'\n    assert data == {'other':1}\n",
        ),
        (
            "public-fields",
            "local",
            "public_fields(record) returns a new shallow dict containing all string keys not starting with '_', preserving values including zero, False and None. Input keys are strings. No input mutation, nested values retain identity.",
            {"target": "def public_fields(record):\n    return dict(record)\n"},
            {
                "target": "def public_fields(record):\n    return {key: value for key, value in record.items() if not key.startswith('_')}\n"
            },
            "from product.target import public_fields\n\ndef test_filter():\n    assert public_fields({'_secret':2,'a':0,'b':False,'c':None,'':3,'x_y':4}) == {'a':0,'b':False,'c':None,'':3,'x_y':4}\n\ndef test_shallow_and_input():\n    nested = []\n    source = {'a':nested,'_hidden':1}\n    out = public_fields(source)\n    assert out is not source and out['a'] is nested\n    assert source == {'a':nested,'_hidden':1}\n    assert public_fields({}) == {}\n",
        ),
        (
            "lookup-fallback",
            "branch",
            "lookup_or(fetch, key, default) calls synchronous fetch(key) exactly once. Return its result unchanged, including false-valued results. Return default only if fetch raises KeyError. Propagate every other exception unchanged.",
            {
                "target": "def lookup_or(fetch, key, default):\n    return fetch(key) or default\n"
            },
            {
                "target": "def lookup_or(fetch, key, default):\n    try:\n        return fetch(key)\n    except KeyError:\n        return default\n"
            },
            "import pytest\nfrom product.target import lookup_or\n\n@pytest.mark.parametrize('value',[0,False,'',None,7])\ndef test_values(value):\n    calls=[]\n    def fetch(key):\n        calls.append(key)\n        return value\n    assert lookup_or(fetch,'k','fallback') is value\n    assert calls == ['k']\n\ndef test_errors():\n    def missing(key):\n        raise KeyError(key)\n    assert lookup_or(missing,'k',None) is None\n    error = RuntimeError('same')\n    def broken(key):\n        raise error\n    with pytest.raises(RuntimeError) as observed:\n        lookup_or(broken,'k','fallback')\n    assert observed.value is error\n",
        ),
        (
            "async-first-present",
            "branch",
            "first_present(fetch, keys) awaits fetch for each key sequentially in order until first result that is not None; return it unchanged (0, False and '' count as present). If all None or no keys return None. Propagate exceptions without visiting later keys. Do not mutate keys.",
            {"target": "async def first_present(fetch, keys):\n    return None\n"},
            {
                "target": "async def first_present(fetch, keys):\n    for key in keys:\n        value = await fetch(key)\n        if value is not None:\n            return value\n    return None\n"
            },
            "import asyncio\nimport pytest\nfrom product.target import first_present\n\n@pytest.mark.parametrize('value',[0,False,'',9])\ndef test_first(value):\n    calls=[]\n    keys=['a','b','c']\n    async def fetch(key):\n        calls.append(key)\n        return {'a':None,'b':value,'c':99}[key]\n    assert asyncio.run(first_present(fetch,keys)) is value\n    assert calls == ['a','b'] and keys == ['a','b','c']\n\ndef test_empty_and_all_missing():\n    calls=[]\n    async def fetch(key):\n        calls.append(key)\n        return None\n    assert asyncio.run(first_present(fetch,[])) is None\n    assert calls == []\n    assert asyncio.run(first_present(fetch,[1,2])) is None\n    assert calls == [1,2]\n\ndef test_error():\n    calls=[]\n    error=RuntimeError('same')\n    async def fetch(key):\n        calls.append(key)\n        raise error\n    with pytest.raises(RuntimeError) as caught:\n        asyncio.run(first_present(fetch,[1,2]))\n    assert caught.value is error and calls == [1]\n",
        ),
        (
            "label-rollup",
            "cross-file",
            "normalize_labels(labels) strips leading/trailing whitespace, drops only resulting empty strings and preserves order and duplicates/case. summarize_labels(labels) delegates to normalize_labels and returns {'labels': normalized list, 'count': its length}. Inputs list of strings, no mutation.",
            {
                "labels": "def normalize_labels(labels):\n    return list(labels)\n",
                "target": "from product.labels import normalize_labels\n\ndef summarize_labels(labels):\n    return {'labels':normalize_labels(labels), 'count':len(labels)}\n",
            },
            {
                "labels": "def normalize_labels(labels):\n    return [value for label in labels if (value := label.strip())]\n",
                "target": "from product.labels import normalize_labels\n\ndef summarize_labels(labels):\n    cleaned = normalize_labels(labels)\n    return {'labels':cleaned, 'count':len(cleaned)}\n",
            },
            "from product.labels import normalize_labels\nfrom product.target import summarize_labels\n\ndef test_normalize():\n    data=[' A ','','  ','A','b\\t','0']\n    assert normalize_labels(data) == ['A','A','b','0']\n    assert data == [' A ','','  ','A','b\\t','0']\n\ndef test_roundtrip():\n    assert summarize_labels([' X ',' ','X']) == {'labels':['X','X'],'count':2}\n    assert summarize_labels([]) == {'labels':[],'count':0}\n",
        ),
        (
            "async-receipt",
            "dependent",
            "collect_values(fetch, keys) sequentially awaits every key, collecting results including None/False/zero/empty strings, preserving order and input. On error propagate same exception and do not visit later keys. receipt(fetch, keys) awaits collect_values once and returns {'values': collected list, 'count': length}. No retries or parallel execution.",
            {
                "collector": "async def collect_values(fetch, keys):\n    return []\n",
                "target": "from product.collector import collect_values\n\nasync def receipt(fetch, keys):\n    values = await collect_values(fetch, keys)\n    return {'values':values, 'count':0}\n",
                "entry": "from product.target import receipt\n\nasync def run_receipt(fetch, keys):\n    return await receipt(fetch, keys)\n",
            },
            {
                "collector": "async def collect_values(fetch, keys):\n    values = []\n    for key in keys:\n        values.append(await fetch(key))\n    return values\n",
                "target": "from product.collector import collect_values\n\nasync def receipt(fetch, keys):\n    values = await collect_values(fetch, keys)\n    return {'values':values, 'count':len(values)}\n",
            },
            "import asyncio\nimport pytest\nfrom product.collector import collect_values\nfrom product.entry import run_receipt\n\ndef test_collect_order():\n    calls=[]\n    values=[None,False,0,'',9]\n    async def fetch(key):\n        calls.append(key)\n        return values[key]\n    keys=list(range(5))\n    out=asyncio.run(collect_values(fetch,keys))\n    assert out == values and [type(v) for v in out] == [type(v) for v in values]\n    assert calls == keys and keys == list(range(5))\n\ndef test_collect_error():\n    calls=[]\n    error=RuntimeError('same')\n    async def fetch(key):\n        calls.append(key)\n        if key == 1:\n            raise error\n        return 0\n    with pytest.raises(RuntimeError) as caught:\n        asyncio.run(collect_values(fetch,[0,1,2]))\n    assert caught.value is error and calls == [0,1]\n\ndef test_receipt_roundtrip():\n    calls=[]\n    async def fetch(key):\n        calls.append(key)\n        return [None,False,0,''][key]\n    out=asyncio.run(run_receipt(fetch,[0,1,2,3]))\n    assert out == {'values':[None,False,0,''],'count':4}\n    assert [type(v) for v in out['values']] == [type(None),bool,int,str]\n    assert calls == [0,1,2,3]\n    assert asyncio.run(run_receipt(fetch,[])) == {'values':[],'count':0}\n\ndef test_receipt_error():\n    calls=[]\n    error=RuntimeError('same')\n    async def fetch(key):\n        calls.append(key)\n        raise error\n    with pytest.raises(RuntimeError) as caught:\n        asyncio.run(run_receipt(fetch,[1,2]))\n    assert caught.value is error and calls == [1]\n",
        ),
    ]
    cases, oracles = [], {}
    for identity, kind, contract, broken, reference, tests in specs:
        source = {f"src/product/{key}.py": text for key, text in broken.items()}
        ref = {f"src/product/{key}.py": text for key, text in reference.items()}
        case = copy.deepcopy(template)
        case.update(
            case_id=identity,
            goal=contract,
            feature_risk="medium",
            integration_risk="medium",
            origin={"kind": "primary-authored-unseen", "family": kind},
        )
        case["files"] = {
            "src/product/__init__.py": "",
            **source,
            "tests/test_target.py": tests,
        }
        unit = copy.deepcopy(template["units"][0])
        paths = [p for p in source if not p.endswith("/entry.py")]
        unit.update(
            unit_id="qual-unit",
            risk="medium",
            path=paths[0],
            paths=paths,
            anchor="def ",
            anchors={
                p: text.split("def ")[1].split("(")[0] for p, text in source.items()
            },
            tests=["tests/test_target.py"],
            dependencies=[],
            contract=contract,
            behavior=contract,
        )
        case["units"] = [unit]
        if kind == "dependent":
            first = copy.deepcopy(unit)
            first.update(
                unit_id="collect-unit",
                paths=["src/product/collector.py"],
                path="src/product/collector.py",
                tests=[
                    "tests/test_target.py::test_collect_order",
                    "tests/test_target.py::test_collect_error",
                ],
                contract="collect_values(fetch, keys) sequentially awaits every key in order and retains every result including None, False, zero and ''. Preserve input. Propagate the same error and stop further calls. No retries or parallelism.",
            )
            second = copy.deepcopy(unit)
            second.update(
                paths=["src/product/target.py"],
                path="src/product/target.py",
                dependencies=["collect-unit"],
                tests=[
                    "tests/test_target.py::test_receipt_roundtrip",
                    "tests/test_target.py::test_receipt_error",
                ],
                contract="receipt(fetch, keys) awaits the accepted collect_values exactly once; returns {'values': collected list, 'count': its length}, including all false values and preserving exception propagation. The public run_receipt delegates to receipt. Do not modify the accepted collector.",
            )
            case["units"] = [first, second]
        # A near-correct mutant exercises a distinct contract violation.
        mutant = dict(ref)
        if identity == "display-default":
            mutant["src/product/target.py"] = (
                "def display_name(record):\n    return record.get('name') or 'unnamed'\n"
            )
        elif identity == "public-fields":
            mutant["src/product/target.py"] = ref["src/product/target.py"].replace(
                "if not key.startswith('_')", "if not key.startswith('_') and value"
            )
        elif identity == "lookup-fallback":
            mutant["src/product/target.py"] = ref["src/product/target.py"].replace(
                "except KeyError:", "except Exception:"
            )
        elif identity == "async-first-present":
            mutant["src/product/target.py"] = ref["src/product/target.py"].replace(
                "value is not None", "value"
            )
        elif identity == "label-rollup":
            mutant["src/product/target.py"] = ref["src/product/target.py"].replace(
                "len(cleaned)", "len(labels)"
            )
        else:
            mutant["src/product/collector.py"] = ref[
                "src/product/collector.py"
            ].replace(
                "values.append(await fetch(key))",
                "value = await fetch(key)\n        if value:\n            values.append(value)",
            )
        oracles[identity] = {"reference": ref, "mutants": [source, mutant]}
        cases.append(case)
    return {"cases": cases}, oracles
