"""Explicit opt-in guard: preserve baseline imports without new import authority.

Freeze unapproved existing imports rather than rejecting their presence. Only
the previous tiny stdlib allowlist may change. This is not an execution sandbox.
"""

import ast
import re

from harness_protocol import IMPORT_CEILING, PROMPT, SCHEMA, decode

__all__ = ["IMPORT_CEILING", "PROMPT", "SCHEMA", "decode", "guard", "shape"]


def shape(source, symbol, allowed):
    if not allowed <= IMPORT_CEILING:
        raise ValueError("Import authority exceeds unchanged ceiling")
    tree = ast.parse(source)
    target_count = 0
    kept = []
    nested_imports = []
    for node in tree.body:
        # Only explicitly approved top-level imports may be added/removed.
        # Every other import stays in the skeleton, including its aliases/order.
        if isinstance(node, ast.ImportFrom) and node.module != "__future__":
            frozen_names = [
                name
                for name in node.names
                if node.level or (node.module, name.name, name.asname) not in allowed
            ]
            if not frozen_names:
                continue
            node.names = frozen_names
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == symbol
        ):
            target_count += 1
            # Stripping the target body must not silently permit local imports.
            nested_imports = [
                ast.dump(child)
                for child in ast.walk(node)
                if isinstance(child, (ast.Import, ast.ImportFrom))
            ]
            node.body = [ast.Pass()]
        kept.append(node)
    if target_count != 1:
        raise ValueError("Exactly one approved target required")
    tree.body = kept
    return ast.dump(tree), nested_imports


def guard(current, proposed, symbol, allowed):
    if not isinstance(proposed, str) or len(proposed) > 12000:
        raise ValueError("Unchanged 12000-character module limit")
    if shape(current, symbol, allowed) != shape(proposed, symbol, allowed):
        raise ValueError("Existing imports/signature/unrelated AST changed")
    directive = re.compile(
        r"#\s*(?:noqa\b|type:\s*ignore|pyright:|ruff:)", re.IGNORECASE
    )
    old = {line.strip() for line in current.splitlines() if directive.search(line)}
    new = {line.strip() for line in proposed.splitlines() if directive.search(line)}
    if new - old:
        raise ValueError("New check suppression forbidden")
