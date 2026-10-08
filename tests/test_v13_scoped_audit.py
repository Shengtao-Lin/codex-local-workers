"""The review split must not hide A2 changes inside a renamed A1 baseline."""

import ast
import importlib.util
import sys
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
SPEC = importlib.util.spec_from_file_location(
    "v13_scoped_audit_test", BENCHMARKS / "v13_scoped_audit.py"
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_intermediate_preserves_all_non_a1_functions_and_clears_no_acknowledgement():
    before = "def resolve_inherited_packet():\n    return 0\n\nclass Runtime:\n    def _begin_edit(self):\n        return 0\n\n    def _record_edit(self):\n        return 0\n\n    def validate(self):\n        return 'before'\n"
    candidate = "def resolve_inherited_packet():\n    return 1\n\nclass Runtime:\n    def _begin_edit(self):\n        return 1\n\n    def _is_repair_edit(self):\n        return True\n\n    def _record_edit(self):\n        self.last_contract_check = None\n        return 1\n\n    def validate(self):\n        return 'candidate'\n"
    intermediate = AUDIT.intermediate_source(before, candidate)
    assert "self.last_contract_check = None" not in intermediate
    functions = {
        node.name: node
        for node in ast.walk(ast.parse(intermediate))
        if isinstance(node, ast.FunctionDef)
    }
    assert set(functions) == AUDIT.A1_SYMBOLS | {"validate"}
    assert ast.literal_eval(functions["validate"].body[0].value) == "before"
    assert ast.literal_eval(functions["_record_edit"].body[0].value) == 1


def test_intermediate_rejects_missing_or_renamed_budget_symbol():
    import pytest

    with pytest.raises(ValueError, match="symbol set drift"):
        AUDIT.intermediate_source(
            "def unrelated():\n    pass\n", "def unrelated():\n    pass\n"
        )
