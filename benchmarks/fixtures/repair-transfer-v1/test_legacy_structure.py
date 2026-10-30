"""Protect all structure outside the authorized function bodies."""

import ast
import json
from pathlib import Path


def masked_ast(source: str, allowed: list[str]) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in allowed:
            node.body = [ast.Pass()]
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if (
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name + "." + member.name in allowed
                ):
                    member.body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def test_legacy_structure_and_public_signatures_are_unchanged() -> None:
    expected = json.loads(Path("tests/legacy_structure.json").read_text(encoding="utf-8"))
    for path, facts in expected.items():
        assert masked_ast(Path(path).read_text(encoding="utf-8"), facts["allowed"]) == facts["ast"]
