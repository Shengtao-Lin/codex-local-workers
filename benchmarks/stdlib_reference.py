"""Read-only exact API documentation for statically referenced approved stdlib calls.

No model-selected imports/execution, solution snippets, keyword selection or summaries.
"""

import ast
import hashlib
import inspect
import json
import sys
from pathlib import Path

APPROVED = {"json": json, "hashlib": hashlib}


def collect(source):
    tree = ast.parse(source)
    imports = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name in APPROVED:
                    imports[name.asname or name.name] = name.name
    requested = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        ):
            module = imports.get(node.func.value.id)
            name = node.func.attr
            if (
                module
                and not name.startswith("_")
                and callable(getattr(APPROVED[module], name, None))
            ):
                requested.add((module, name))
    items = []
    for module, name in sorted(requested):
        obj = getattr(APPROVED[module], name)
        try:
            signature = str(inspect.signature(obj))
        except (ValueError, TypeError):
            signature = "unknown"
        origin = Path(APPROVED[module].__file__)
        items.append(
            {
                "api": module + "." + name,
                "signature": signature,
                "documentation": inspect.getdoc(obj) or "",
                "module_source": str(origin),
                "module_sha256": hashlib.sha256(origin.read_bytes()).hexdigest(),
            }
        )
    output = {
        "kind": "verbatim-local-stdlib-api-reference",
        "python": sys.version,
        "selection": "Every directly referenced approved json/hashlib callable; no repair-specific selection",
        "items": items,
    }
    if len(json.dumps(output, ensure_ascii=False)) > 12000:
        raise ValueError("Dependency reference exceeds fixed context cap")
    return output
