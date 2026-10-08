"""New near-transfer cases; known semantic families, not unseen qualification."""

from layer_isolation_cases import corpus


def cases(template):
    data, _ = corpus(template)
    prototypes = {c["case_id"]: c for c in data["cases"]}
    specs = [
        (
            "window-bounds",
            "exact-count",
            "window(items, start, size) requires exact built-in integers start >= 0 and size >= 0, rejecting bool and subclasses with ValueError, including when items is empty. Return a new list for the slice from start of at most size items. Out-of-range start and zero size return []; never mutate items.",
            {
                "target": "def window(items, start, size):\n    return items[start:start+size]\n"
            },
            "import pytest\nfrom product.target import window\nclass Child(int):\n    pass\ndef test_values():\n    items=[1,2,3]\n    assert window(items,1,9)==[2,3]\n    assert window(items,9,1)==[]\n    assert window(items,0,0)==[]\n    result=window(items,0,3)\n    assert result==items and result is not items\n    assert items==[1,2,3]\n@pytest.mark.parametrize('bad',[True,False,Child(1),-1,1.0,None])\n@pytest.mark.parametrize('items',[[],[1,2]])\ndef test_bad(bad,items):\n    with pytest.raises(ValueError):\n        window(items,bad,1)\n    with pytest.raises(ValueError):\n        window(items,0,bad)\n",
            {
                "target": "def window(items, start, size):\n    if type(start) is not int or type(size) is not int or start < 0 or size < 0:\n        raise ValueError('bounds')\n    return list(items[start:start+size])\n"
            },
        ),
        (
            "port-roundtrip",
            "duration-pair",
            "parse_port(text) accepts only nonempty ASCII decimal digit strings whose numeric value is 1..65535 inclusive; leading zeros allowed, all other strings raise ValueError. endpoint(host,text) uses parse_port and returns host + ':' + the canonical decimal port (no leading zeros). Host is a nonempty DNS name. Invalid port must propagate ValueError.",
            {
                "options": "def parse_port(text):\n    return int(text)\n",
                "target": "def endpoint(host, text):\n    return host + ':' + text\n",
            },
            "import pytest\nfrom product.options import parse_port\nfrom product.target import endpoint\ndef test_ports():\n    for text,value in [('00080',80),('1',1),('65535',65535)]:\n        assert parse_port(text)==value\n        assert endpoint('node.test',text)==f'node.test:{value}'\n@pytest.mark.parametrize('text',['','0','65536','-1','+80',' 80','80 ','８０','٨٠','8_0'])\ndef test_bad(text):\n    with pytest.raises(ValueError):\n        parse_port(text)\n    with pytest.raises(ValueError):\n        endpoint('node.test',text)\n",
            {
                "options": "def parse_port(text):\n    if not text or any(c < '0' or c > '9' for c in text):\n        raise ValueError('port')\n    value=int(text)\n    if not 1 <= value <= 65535:\n        raise ValueError('range')\n    return value\n",
                "target": "from product.options import parse_port\n\ndef endpoint(host, text):\n    return host + ':' + str(parse_port(text))\n",
            },
        ),
        (
            "async-stop",
            "async-fetch",
            "async collect_until(fetch, keys) awaits fetch(key) sequentially exactly once for each visited key. The first None result is a stop sentinel: do not include it and do not visit later keys. Keep all other values including 0, False and ''. Propagate the same fetch exception and stop. Empty keys returns [] without calls; do not mutate keys.",
            {
                "target": "async def collect_until(fetch, keys):\n    return [fetch(key) for key in keys]\n"
            },
            "import asyncio\nimport pytest\nfrom product.target import collect_until\ndef test_stop():\n    calls=[]\n    values=[0,False,'',None,99]\n    async def fetch(key):\n        calls.append(key)\n        return values[key]\n    keys=[0,1,2,3,4]\n    result=asyncio.run(collect_until(fetch,keys))\n    assert result==[0,False,''] and result[0] is not False and result[1] is False\n    assert calls==[0,1,2,3] and keys==[0,1,2,3,4]\n    calls.clear()\n    assert asyncio.run(collect_until(fetch,[]))==[] and calls==[]\ndef test_error():\n    error=RuntimeError('failed')\n    calls=[]\n    async def fetch(key):\n        calls.append(key)\n        if key==2:\n            raise error\n        return key\n    with pytest.raises(RuntimeError) as caught:\n        asyncio.run(collect_until(fetch,[1,2,3]))\n    assert caught.value is error and calls==[1,2]\n",
            {
                "target": "async def collect_until(fetch, keys):\n    result=[]\n    for key in keys:\n        value=await fetch(key)\n        if value is None:\n            break\n        result.append(value)\n    return result\n"
            },
        ),
    ]
    result, oracles = [], {}
    for name, prototype, contract, broken, tests, reference in specs:
        case = prototypes[prototype]
        sources = {f"src/product/{p}.py": text for p, text in broken.items()}
        case.update(
            case_id=name,
            goal=contract,
            exposure="new-near-transfer-known-semantic-family",
            files={
                "src/product/__init__.py": "",
                **sources,
                "tests/test_target.py": tests,
            },
        )
        unit = case["units"][0]
        unit.update(
            contract=contract,
            behavior=contract,
            paths=list(sources),
            anchors={
                p: text.split("def ")[1].split("(")[0] for p, text in sources.items()
            },
        )
        result.append(case)
        oracles[name] = {f"src/product/{p}.py": text for p, text in reference.items()}
    return {"cases": result}, oracles
