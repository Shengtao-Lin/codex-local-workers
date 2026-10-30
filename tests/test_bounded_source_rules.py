import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_source_rules as B

BASE = 'import json\n\nCONST = 1\n\ndef f(x: int) -> int:\n    return x\n\ndef other():\n    return "unchanged"\n'


def test_both_representations_produce_same_bound_module():
    function = "def f(x: int) -> int:\n    return x + 1\n"
    module = BASE.replace("return x\n", "return x + 1\n")
    assert ast.dump(ast.parse(B.materialize(BASE, function, "f", set()))) == ast.dump(
        ast.parse(B.materialize(BASE, module, "f", set()))
    )


@pytest.mark.parametrize(
    "bad",
    [
        BASE.replace("import json", "import os"),
        BASE.replace("CONST = 1", "CONST = 2"),
        BASE.replace('return "unchanged"', 'return "changed"'),
        BASE.replace("x: int", "x: str"),
        BASE + "print('side effect')\n",
        BASE + "def f(x: int) -> int:\n    return 2\n",
        "def f(x: int) -> int:\n    import os\n    return x\n",
        BASE.replace("return x\n", "return x # type: ignore\n"),
        "def f(x: int) -> int:\\n    return x",
        'print("no target")\n',
    ],
)
def test_module_shape_does_not_expand_authority(bad):
    with pytest.raises((ValueError, SyntaxError)):
        B.materialize(BASE, bad, "f", set())


def test_noop_module_remains_noop():
    assert B.materialize(BASE, BASE, "f", set()) == BASE
