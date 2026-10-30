import ast
import importlib.util
import json
from pathlib import Path


def test_generic_protocol_analogy_matches_actual_python_not_target_answer():
    path = (
        Path(__file__).resolve().parents[1]
        / "benchmarks/fixtures/reviewer-protocol-analogy-v1.json"
    )
    example = json.loads(path.read_text(encoding="utf-8"))
    source = path.with_name("reviewer_protocol_analogy_v1.py")
    assert ast.dump(ast.parse(example["code"])) == ast.dump(
        ast.parse(source.read_text(encoding="utf-8"))
    )
    spec = importlib.util.spec_from_file_location("frozen_protocol_analogy", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.results == example["observed"]
    assert all(type(value) is bool for value in module.results.values())
    assert not any(
        word in example["code"]
        for word in ("ToolRegistry", "__await__", "inspect.isawaitable", "PlainMapping")
    )
