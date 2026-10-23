"""Primary-owned Python symbol identity, not a semantic correctness oracle."""

from __future__ import annotations

import ast
import keyword
from pathlib import PurePosixPath
from typing import Any


def validate_binding(
    value: Any, *, readable: list[str], forbidden: list[str], tests: list[str]
) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"path", "symbol"}:
        raise ValueError("implementation_ref must contain exactly path and symbol")
    path, symbol = value["path"], value["symbol"]
    if (
        not isinstance(path, str)
        or not path
        or "\\" in path
        or ":" in path
        or path != PurePosixPath(path).as_posix()
        or PurePosixPath(path).is_absolute()
        or any(part in {".", "..", ""} for part in path.split("/"))
        or not path.endswith(".py")
    ):
        raise ValueError("implementation_ref.path must be an ordinary relative Python path")

    def inside(root: str) -> bool:
        return root == "." or path == root or path.startswith(root.rstrip("/") + "/")

    if not any(inside(root) for root in readable) or any(inside(root) for root in forbidden):
        raise ValueError("implementation_ref.path exceeds readable authority")
    if (
        path in tests
        or PurePosixPath(path).name.startswith("test_")
        or PurePosixPath(path).name.endswith("_test.py")
        or any(
            part in {"test", "tests", ".agent", ".git", ".local-agents"} for part in path.split("/")
        )
    ):
        raise ValueError("implementation_ref cannot bind a test or control file")
    if (
        not isinstance(symbol, str)
        or len(symbol) > 256
        or not all(
            part.isidentifier() and not keyword.iskeyword(part) for part in symbol.split(".")
        )
    ):
        raise ValueError("implementation_ref.symbol must be a qualified Python identifier")
    return {"path": path, "symbol": symbol}


def statement_lines(source: str, symbol: str) -> set[int]:
    """Locate a unique real declaration; comments/strings/name substrings are not symbols."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        raise ValueError("bound implementation is not valid Python") from exc
    matches: list[ast.FunctionDef | ast.AsyncFunctionDef | ast.Assign | ast.AnnAssign] = []

    def declarations(nodes: list[ast.stmt], prefix: str = "") -> None:
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + node.name
                if name == symbol and not isinstance(node, ast.ClassDef):
                    matches.append(node)
                declarations(node.body, name + ".")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(
                    isinstance(target, ast.Name) and prefix + target.id == symbol
                    for target in targets
                ):
                    matches.append(node)
            else:
                # Conditional declarations remain ambiguous when the same symbol has two definitions.
                for field in ("body", "orelse", "finalbody"):
                    children = getattr(node, field, [])
                    if isinstance(children, list):
                        declarations(children, prefix)
                for handler in getattr(node, "handlers", []):
                    declarations(handler.body, prefix)

    declarations(tree.body)
    if len(matches) != 1:
        raise ValueError("bound implementation symbol must resolve to exactly one declaration")
    match = matches[0]
    if isinstance(match, (ast.Assign, ast.AnnAssign)):
        return {match.lineno}
    lines: set[int] = set()

    def statements(nodes: list[ast.stmt]) -> None:
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                continue
            lines.add(node.lineno)
            for field in ("body", "orelse", "finalbody"):
                children = getattr(node, field, [])
                if isinstance(children, list):
                    statements(children)
            for handler in getattr(node, "handlers", []):
                statements(handler.body)

    statements(match.body)
    if not lines:
        raise ValueError("bound implementation symbol has no implementation statements")
    return lines


def covers(binding: dict[str, str], source: str, refs: list[dict]) -> bool:
    lines = statement_lines(source, binding["symbol"])
    return any(
        ref.get("path") == binding["path"]
        and type(ref.get("start_line")) is int
        and type(ref.get("end_line")) is int
        and any(ref["start_line"] <= line <= ref["end_line"] for line in lines)
        for ref in refs
    )
