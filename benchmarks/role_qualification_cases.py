"""New supervised-role qualification tasks; oracles never enter worker scope."""

from __future__ import annotations

import copy


def corpus(template):
    specs = [
        (
            "filename-suffix",
            "small",
            "suffix(name) returns text after the last dot lowercased. A basename beginning with a single dot and no other dot, no dot, or trailing dot has empty suffix. Other punctuation is unchanged; inputs are strings.",
            {
                "src/product/target.py": "def suffix(name):\n    return name.split('.')[-1].lower()\n"
            },
            "from product.target import suffix\n\ndef test_normal():\n    assert suffix('report.TAR.GZ') == 'gz'\n    assert suffix('a.b-c') == 'b-c'\n\ndef test_boundaries():\n    assert suffix('README') == ''\n    assert suffix('.profile') == ''\n    assert suffix('file.') == ''\n    assert suffix('.config.JSON') == 'json'\n",
            {
                "src/product/target.py": "def suffix(name):\n    head, dot, tail = name.rpartition('.')\n    return tail.lower() if dot and head and tail else ''\n"
            },
        ),
        (
            "utf8-capacity",
            "small",
            "fits(text, limit) is True iff UTF-8 encoding length is at most limit; exact equality passes; empty text fits limit zero. Inputs are valid Unicode strings and nonnegative ints.",
            {
                "src/product/target.py": "def fits(text, limit):\n    return len(text) <= limit\n"
            },
            "from product.target import fits\n\ndef test_ascii():\n    assert fits('ab', 2) is True\n    assert fits('abc', 2) is False\n\ndef test_encoded_boundary():\n    assert fits('界', 2) is False\n    assert fits('界', 3) is True\n    assert fits('😀', 3) is False\n    assert fits('', 0) is True\n",
            {
                "src/product/target.py": "def fits(text, limit):\n    return len(text.encode('utf-8')) <= limit\n"
            },
        ),
        (
            "window-groups",
            "medium",
            "groups(items, width) returns consecutive list slices, last may be shorter. Empty input returns empty list. width must be exact int >=1, otherwise raise ValueError even on empty input. Do not mutate items; no deep copy required.",
            {
                "src/product/target.py": "def groups(items, width):\n    return [items]\n"
            },
            "import pytest\nfrom product.target import groups\n\ndef test_groups():\n    data = [1,2,3,4,5]\n    assert groups(data, 2) == [[1,2],[3,4],[5]]\n    assert data == [1,2,3,4,5]\n    assert groups([], 1) == []\n    assert groups([1], 8) == [[1]]\n\n@pytest.mark.parametrize('width', [0,-1,True,False,1.0,'2',None])\ndef test_invalid(width):\n    with pytest.raises(ValueError):\n        groups([], width)\n",
            {
                "src/product/target.py": "def groups(items, width):\n    if type(width) is not int or width < 1:\n        raise ValueError('invalid width')\n    return [items[start:start+width] for start in range(0, len(items), width)]\n"
            },
        ),
        (
            "explicit-switch",
            "medium",
            "enabled(config) defaults True only when 'enabled' key is absent. Present value must be exact bool and is returned unchanged; None, numbers and strings raise ValueError. Other keys ignored; input mapping not mutated.",
            {
                "src/product/target.py": "def enabled(config):\n    return bool(config.get('enabled', True))\n"
            },
            "import pytest\nfrom product.target import enabled\n\ndef test_switch():\n    assert enabled({}) is True\n    assert enabled({'enabled':False}) is False\n    assert enabled({'enabled':True}) is True\n    config = {'other':4}\n    assert enabled(config) is True\n    assert config == {'other':4}\n\n@pytest.mark.parametrize('value', [None,0,1,'false',[],{}])\ndef test_invalid(value):\n    with pytest.raises(ValueError):\n        enabled({'enabled':value})\n",
            {
                "src/product/target.py": "def enabled(config):\n    value = config.get('enabled', True)\n    if type(value) is not bool:\n        raise ValueError('invalid enabled')\n    return value\n"
            },
        ),
        (
            "timeout-roundtrip",
            "medium",
            "parse_timeout(config) reads timeout_ms, default 1000. Exact nonnegative int only, bool invalid, invalid raises ValueError. summarize(config) calls parser and returns {'timeout_ms': integer, 'timeout_seconds': integer/1000}. Preserve zero and input; do not truncate fractional seconds.",
            {
                "src/product/options.py": "def parse_timeout(config):\n    return config.get('timeout_ms') or 1000\n",
                "src/product/target.py": "from product.options import parse_timeout\n\ndef summarize(config):\n    value = parse_timeout(config)\n    return {'timeout_ms':value, 'timeout_seconds':value // 1000}\n",
            },
            "import pytest\nfrom product.target import summarize\nfrom product.options import parse_timeout\n\ndef test_default_and_fraction():\n    assert summarize({}) == {'timeout_ms':1000,'timeout_seconds':1.0}\n    assert summarize({'timeout_ms':250}) == {'timeout_ms':250,'timeout_seconds':0.25}\n\ndef test_zero_and_input():\n    data = {'timeout_ms':0}\n    assert summarize(data) == {'timeout_ms':0,'timeout_seconds':0.0}\n    assert data == {'timeout_ms':0}\n\n@pytest.mark.parametrize('value', [True,-1,'0',None,1.0])\ndef test_invalid(value):\n    with pytest.raises(ValueError):\n        parse_timeout({'timeout_ms':value})\n    with pytest.raises(ValueError):\n        summarize({'timeout_ms':value})\n",
            {
                "src/product/options.py": "def parse_timeout(config):\n    value = config.get('timeout_ms', 1000)\n    if type(value) is not int or value < 0:\n        raise ValueError('invalid timeout')\n    return value\n",
                "src/product/target.py": "from product.options import parse_timeout\n\ndef summarize(config):\n    value = parse_timeout(config)\n    return {'timeout_ms':value, 'timeout_seconds':value / 1000}\n",
            },
        ),
        (
            "case-preserving-query",
            "medium",
            "decode_query(text) splits '&' components, skips empty components, splits each at first '=' (missing '=' means empty value), decodes percent escapes and plus via urllib.parse.unquote_plus, preserves case and keeps the last value of duplicate decoded keys. encode_query(mapping) uses urllib.parse.urlencode without lowercasing. Both operate on string keys/values; encode followed by decode preserves mapping exactly, including spaces, plus, ampersand, equals and Unicode. No mutation; malformed percent encodings follow unquote_plus standard behavior.",
            {
                "src/product/codec.py": "def decode_query(text):\n    return dict(part.split('=') for part in text.split('&'))\n",
                "src/product/target.py": "from urllib.parse import urlencode\n\ndef encode_query(mapping):\n    return urlencode(mapping).lower()\n",
            },
            "from product.codec import decode_query\nfrom product.target import encode_query\n\ndef test_decode():\n    assert decode_query('X=a%3Db&empty&X=last+Value&&') == {'X':'last Value','empty':''}\n    assert decode_query('A%2BB=v%26w') == {'A+B':'v&w'}\n    assert decode_query('') == {}\n\ndef test_roundtrip():\n    data = {'Name':'AbC + & = 界','EMPTY':''}\n    assert decode_query(encode_query(data)) == data\n    assert data == {'Name':'AbC + & = 界','EMPTY':''}\n",
            {
                "src/product/codec.py": "from urllib.parse import unquote_plus\n\ndef decode_query(text):\n    result = {}\n    for part in text.split('&'):\n        if part:\n            key, _, value = part.partition('=')\n            result[unquote_plus(key)] = unquote_plus(value)\n    return result\n",
                "src/product/target.py": "from urllib.parse import urlencode\n\ndef encode_query(mapping):\n    return urlencode(mapping)\n",
            },
        ),
    ]
    cases, oracles = [], {}
    for identity, risk, contract, sources, tests, reference in specs:
        if identity in {"window-groups", "timeout-roundtrip"}:
            tests += "\nclass IntegerSubclass(int):\n    pass\n\ndef test_exact_integer_boundary():\n"
            if identity == "window-groups":
                tests += "    with pytest.raises(ValueError):\n        groups([], IntegerSubclass(2))\n"
            else:
                tests += "    for value in (False, IntegerSubclass(2)):\n        with pytest.raises(ValueError):\n            parse_timeout({'timeout_ms': value})\n        with pytest.raises(ValueError):\n            summarize({'timeout_ms': value})\n"
        case = copy.deepcopy(template)
        case.update(
            case_id=identity, goal=contract, feature_risk=risk, integration_risk=risk
        )
        case["files"] = {
            "src/product/__init__.py": "",
            **sources,
            "tests/test_target.py": tests,
        }
        unit = copy.deepcopy(template["units"][0])
        unit.update(
            unit_id="qual-unit",
            risk=risk,
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
        case["units"] = [unit]
        cases.append(case)
        oracles[identity] = {"reference": reference, "mutants": [sources]}
        if identity in {"window-groups", "timeout-roundtrip"}:
            # A near-correct mutant must fail: bool-only rejection is not exact int.
            mutant = dict(reference)
            path = (
                "src/product/target.py"
                if identity == "window-groups"
                else "src/product/options.py"
            )
            name = "width" if identity == "window-groups" else "value"
            mutant[path] = mutant[path].replace(
                f"type({name}) is not int",
                f"(not isinstance({name}, int) or isinstance({name}, bool))",
            )
            oracles[identity]["mutants"].append(mutant)
    return {"cases": cases}, oracles
