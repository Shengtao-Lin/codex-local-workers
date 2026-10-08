"""Eight bounded diagnostic families; references never enter model scope."""

from __future__ import annotations

import copy


def corpus(template):
    specs = [
        (
            "exact-count",
            "known-semantic-family",
            "count(value) returns value unchanged only for an exact built-in int >= 0; "
            "all other inputs, including bool and int subclasses, raise ValueError.",
            {"target": "def count(value):\n    return value\n"},
            "import pytest\nfrom product.target import count\n"
            "class Child(int):\n    pass\n"
            "def test_valid():\n    assert count(0) == 0\n    assert count(7) == 7\n"
            "@pytest.mark.parametrize('value', [True,False,Child(2),-1,1.0,None,'2'])\n"
            "def test_invalid(value):\n    with pytest.raises(ValueError):\n        count(value)\n",
            {
                "target": "def count(value):\n    if type(value) is not int or value < 0:\n        raise ValueError('count')\n    return value\n"
            },
        ),
        (
            "missing-label",
            "known-semantic-family",
            "label(config) defaults to 'auto' only when the label key is absent. "
            "Present str values including '' pass unchanged. Any other present value "
            "raises ValueError. Ignore unrelated keys; never mutate config.",
            {
                "target": "def label(config):\n    return config.get('label') or 'auto'\n"
            },
            "import pytest\nfrom product.target import label\n"
            "def test_values():\n    assert label({}) == 'auto'\n    assert label({'label':''}) == ''\n"
            "    data = {'label':'X','other':1}\n    assert label(data) == 'X'\n"
            "    assert data == {'label':'X','other':1}\n"
            "@pytest.mark.parametrize('value', [None,False,0,[],{}])\n"
            "def test_invalid(value):\n    with pytest.raises(ValueError):\n        label({'label':value})\n",
            {
                "target": "def label(config):\n    value = config.get('label', 'auto')\n    if not isinstance(value, str):\n        raise ValueError('label')\n    return value\n"
            },
        ),
        (
            "async-fetch",
            "new-diagnostic",
            "async fetch_names(fetch, keys) awaits fetch(key) exactly once per key, "
            "sequentially in input order, returns each resulting mapping's 'name'. "
            "On a fetch exception propagate that same exception and stop; empty keys "
            "returns [] without calls. Do not mutate keys.",
            {
                "target": "async def fetch_names(fetch, keys):\n    return [fetch(key)['name'] for key in keys]\n"
            },
            "import asyncio\nimport pytest\nfrom product.target import fetch_names\n"
            "def test_order():\n    calls = []\n    async def fetch(key):\n"
            "        calls.append(key)\n        return {'name':str(key)}\n"
            "    keys = [3,1,3]\n    assert asyncio.run(fetch_names(fetch, keys)) == ['3','1','3']\n"
            "    assert calls == keys == [3,1,3]\n    calls.clear()\n"
            "    assert asyncio.run(fetch_names(fetch, [])) == []\n    assert calls == []\n"
            "def test_failure():\n    calls = []\n    error = RuntimeError('fetch')\n"
            "    async def fetch(key):\n        calls.append(key)\n        if key == 2:\n"
            "            raise error\n        return {'name':'ok'}\n"
            "    with pytest.raises(RuntimeError) as caught:\n        asyncio.run(fetch_names(fetch, [1,2,3]))\n"
            "    assert caught.value is error\n    assert calls == [1,2]\n",
            {
                "target": "async def fetch_names(fetch, keys):\n    result = []\n    for key in keys:\n        item = await fetch(key)\n        result.append(item['name'])\n    return result\n"
            },
        ),
        (
            "success-totals",
            "new-diagnostic",
            "totals(rows) returns a dict mapping scorer to the sum of score for rows "
            "whose status == 'success'. A group with successful zero remains present; "
            "failed-only groups are absent. Empty rows gives {}. Rows have scorer(str), "
            "status(str), score(number). Do not mutate rows.",
            {
                "target": "def totals(rows):\n    return {r['scorer']:r['score'] for r in rows}\n"
            },
            "from copy import deepcopy\nfrom product.target import totals\n"
            "def test_aggregate():\n    rows = [\n"
            "        {'scorer':'a','status':'success','score':1.5},\n"
            "        {'scorer':'a','status':'success','score':-0.5},\n"
            "        {'scorer':'a','status':'failed','score':99},\n"
            "        {'scorer':'b','status':'failed','score':2},\n"
            "        {'scorer':'c','status':'success','score':0},\n    ]\n"
            "    before = deepcopy(rows)\n    assert totals(rows) == {'a':1.0,'c':0}\n"
            "    assert rows == before\n    assert totals([]) == {}\n",
            {
                "target": "def totals(rows):\n    result = {}\n    for row in rows:\n        if row['status'] == 'success':\n            key = row['scorer']\n            result[key] = result.get(key, 0) + row['score']\n    return result\n"
            },
        ),
        (
            "stable-latest",
            "new-diagnostic",
            "latest(rows) keeps the LAST row for each 'id' but orders results by each "
            "id's FIRST appearance. Return the original chosen row objects; do not "
            "mutate the list or rows. IDs are strings. Empty input returns [].",
            {"target": "def latest(rows):\n    return rows\n"},
            "from copy import deepcopy\nfrom product.target import latest\n"
            "def test_last_in_first_order():\n    rows = [{'id':'b','v':1},{'id':'a','v':2},{'id':'b','v':3}]\n"
            "    before = deepcopy(rows)\n    result = latest(rows)\n"
            "    assert result == [rows[2],rows[1]]\n    assert result[0] is rows[2]\n"
            "    assert result[1] is rows[1]\n    assert rows == before\n    assert latest([]) == []\n",
            {
                "target": "def latest(rows):\n    by_id = {}\n    for row in rows:\n        by_id[row['id']] = row\n    return list(by_id.values())\n"
            },
        ),
        (
            "edit-anchor",
            "new-diagnostic",
            "Change ONLY public slug(text) behavior: strip leading/trailing whitespace, "
            "lowercase, replace every literal space with '-'; do not collapse spaces "
            "or change underscores. Keep legacy_slug behavior unchanged. Strings only.",
            {
                "target": "def legacy_slug(text):\n    return text.replace(' ', '_')\n\ndef slug(text):\n    return text.replace(' ', '_')\n"
            },
            "from product.target import slug, legacy_slug\n"
            "def test_slug():\n    assert slug(' A  B_C ') == 'a--b_c'\n"
            "    assert slug('') == ''\n    assert slug(' X.Y ') == 'x.y'\n"
            "def test_legacy():\n    assert legacy_slug(' A  B_C ') == '_A__B_C_'\n",
            {
                "target": "def legacy_slug(text):\n    return text.replace(' ', '_')\n\ndef slug(text):\n    return text.strip().lower().replace(' ', '-')\n"
            },
        ),
        (
            "duration-pair",
            "new-diagnostic",
            "parse_ms(text) accepts only nonempty ASCII digit strings (leading zeros "
            "allowed), returns their integer value; other strings raise ValueError. "
            "summary(text) uses parse_ms and returns {'ms':value,'seconds':value/1000}, "
            "preserving zero and fractional seconds; propagates invalid-input errors.",
            {
                "options": "def parse_ms(text):\n    return int(text)\n",
                "target": "from product.options import parse_ms\n\ndef summary(text):\n    value = parse_ms(text)\n    return {'ms':value,'seconds':value//1000}\n",
            },
            "import pytest\nfrom product.options import parse_ms\nfrom product.target import summary\n"
            "def test_roundtrip():\n    assert parse_ms('00250') == 250\n"
            "    assert summary('00250') == {'ms':250,'seconds':0.25}\n"
            "    assert summary('0') == {'ms':0,'seconds':0.0}\n"
            "@pytest.mark.parametrize('text', ['', ' 1', '+1', '-1', '１', '٢', '1.0'])\n"
            "def test_rejection(text):\n    with pytest.raises(ValueError):\n        parse_ms(text)\n"
            "    with pytest.raises(ValueError):\n        summary(text)\n",
            {
                "options": "def parse_ms(text):\n    if not text or any(c < '0' or c > '9' for c in text):\n        raise ValueError('ms')\n    return int(text)\n",
                "target": "from product.options import parse_ms\n\ndef summary(text):\n    value = parse_ms(text)\n    return {'ms':value,'seconds':value/1000}\n",
            },
        ),
        (
            "encoded-path",
            "new-diagnostic",
            "encode_segment(text) percent-encodes a single URL path segment using "
            "urllib.parse.quote with no extra safe characters. path_for(text) returns "
            "'/items/' + encode_segment(text). Embedded '/' must be encoded, '+' "
            "preserved through decode rather than interpreted as space. Empty string "
            "and Unicode allowed. Do not double encode.",
            {
                "codec": "from urllib.parse import quote\n\ndef encode_segment(text):\n    return quote(text)\n",
                "target": "def path_for(text):\n    return '/items/' + text\n",
            },
            "from urllib.parse import unquote\nfrom product.codec import encode_segment\n"
            "from product.target import path_for\n"
            "def test_encoding():\n    for text in ('a/b', 'a+b c', '界', '', '%2F'):\n"
            "        segment = encode_segment(text)\n        assert unquote(segment) == text\n"
            "        assert path_for(text) == '/items/' + segment\n        assert '/' not in segment\n"
            "    assert path_for('a/b') == '/items/a%2Fb'\n",
            {
                "codec": "from urllib.parse import quote\n\ndef encode_segment(text):\n    return quote(text, safe='')\n",
                "target": "from product.codec import encode_segment\n\ndef path_for(text):\n    return '/items/' + encode_segment(text)\n",
            },
        ),
    ]
    cases, oracles = [], {}
    for identity, exposure, contract, sources, tests, reference in specs:
        sources = {f"src/product/{p}.py": text for p, text in sources.items()}
        reference = {f"src/product/{p}.py": text for p, text in reference.items()}
        case = copy.deepcopy(template)
        case.update(
            case_id=identity,
            goal=contract,
            feature_risk="medium",
            integration_risk="medium",
        )
        case["exposure"] = exposure
        case["files"] = {
            "src/product/__init__.py": "",
            **sources,
            "tests/test_target.py": tests,
        }
        unit = copy.deepcopy(template["units"][0])
        unit.update(
            unit_id="qual-unit",
            risk="medium",
            path="src/product/target.py",
            paths=list(sources),
            anchor="def ",
            anchors={
                p: text.split("def ")[1].split("(")[0] for p, text in sources.items()
            },
            tests=["tests/test_target.py"],
            dependencies=[],
            contract=contract,
            behavior=contract,
        )
        if identity == "edit-anchor":
            unit["anchors"]["src/product/target.py"] = "slug"
        case["units"] = [unit]
        cases.append(case)
        oracles[identity] = {"reference": reference, "mutants": [sources]}
    return {"cases": cases}, oracles
