"""Preregistered formal-contract transfer, not renamed old qualification tasks."""

import copy


def corpus(template):
    rows = [
        (
            "unicode-prefix-budget",
            "prefix(text, cap) returns the longest string prefix whose UTF-8 encoding fits cap bytes, never part of a codepoint. Text is UTF-8-encodable Unicode. Accepted cap values satisfy the observable predicate type(cap) is int and cap >= 0; all others (including bool and int subclasses) raise ValueError, even on empty text. No mutation.",
            {
                "src/product/target.py": "def prefix(text, cap):\n    return text[:cap]\n"
            },
            "import pytest\nfrom product.target import prefix\n\nclass IntChild(int):\n    pass\n\ndef test_prefix():\n    assert prefix('A界😀B',0) == ''\n    assert prefix('A界😀B',3) == 'A'\n    assert prefix('A界😀B',4) == 'A界'\n    assert prefix('A界😀B',8) == 'A界😀'\n    assert prefix('A界😀B',100) == 'A界😀B'\n    assert prefix('',0) == ''\n\n@pytest.mark.parametrize('cap',[True,False,IntChild(2),-1,None,2.0,'2'])\ndef test_invalid_cap(cap):\n    with pytest.raises(ValueError):\n        prefix('',cap)\n",
            {
                "src/product/target.py": "def prefix(text, cap):\n    if type(cap) is not int or cap < 0:\n        raise ValueError('invalid cap')\n    return text.encode('utf-8')[:cap].decode('utf-8',errors='ignore')\n"
            },
        ),
        (
            "ratio-report-boundary",
            "parse_ratio(config) defaults 0.5 exactly when 'ratio' is absent ('ratio' not in config), never for a present None or zero. A present value is accepted exactly when type(value) is float and math.isfinite(value) and 0.0 <= value <= 1.0; all other values raise ValueError. report(config) calls parse_ratio and returns {'ratio': value, 'percent': value * 100}; preserve fractional values and zero, no input mutation.",
            {
                "src/product/options.py": "def parse_ratio(config):\n    return config.get('ratio') or 0.5\n",
                "src/product/target.py": "from product.options import parse_ratio\n\ndef report(config):\n    ratio = parse_ratio(config)\n    return {'ratio':ratio,'percent':int(ratio*100)}\n",
            },
            "import pytest\nfrom product.options import parse_ratio\nfrom product.target import report\n\nclass FloatChild(float):\n    pass\n\ndef test_report():\n    assert report({}) == {'ratio':0.5,'percent':50.0}\n    data = {'ratio':0.0}\n    assert report(data) == {'ratio':0.0,'percent':0.0}\n    assert data == {'ratio':0.0}\n    assert report({'ratio':0.125}) == {'ratio':0.125,'percent':12.5}\n    assert report({'ratio':1.0}) == {'ratio':1.0,'percent':100.0}\n\n@pytest.mark.parametrize('value',[None,True,False,0,1,'0.5',float('nan'),float('inf'),-0.1,1.1,FloatChild(0.5)])\ndef test_invalid_ratio(value):\n    with pytest.raises(ValueError):\n        parse_ratio({'ratio':value})\n    with pytest.raises(ValueError):\n        report({'ratio':value})\n",
            {
                "src/product/options.py": "import math\n\ndef parse_ratio(config):\n    value = config.get('ratio',0.5)\n    if type(value) is not float or not math.isfinite(value) or not 0.0 <= value <= 1.0:\n        raise ValueError('invalid ratio')\n    return value\n",
                "src/product/target.py": "from product.options import parse_ratio\n\ndef report(config):\n    ratio = parse_ratio(config)\n    return {'ratio':ratio,'percent':ratio*100}\n",
            },
        ),
    ]
    cases, oracles = [], {}
    for identity, contract, sources, tests, reference in rows:
        case = copy.deepcopy(template)
        case.update(
            case_id=identity,
            goal=contract,
            feature_risk="medium",
            integration_risk="medium",
        )
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
                path: source.split("def ")[1].split("(")[0]
                for path, source in sources.items()
            },
            tests=["tests/test_target.py"],
            dependencies=[],
            contract=contract,
            behavior=contract,
        )
        case["units"] = [unit]
        cases.append(case)
        near = {
            p: source.replace(
                "type(cap) is not int",
                "(not isinstance(cap,int) or isinstance(cap,bool))",
            ).replace("type(value) is not float", "not isinstance(value,float)")
            for p, source in reference.items()
        }
        oracles[identity] = {"reference": reference, "mutants": [sources, near]}
    return {"cases": cases}, oracles
