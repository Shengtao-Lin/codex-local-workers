"""Bind experiment inputs to an upstream pre-run freeze, not a result workspace."""
from pathlib import Path

import harness_convergence as B


def source_inputs(manifest):
    result = {}
    for name, digest in manifest.items():
        name = name.replace("\\", "/")
        if name.startswith(("src/", "tests/")) or name == "pyproject.toml":
            if name in result:
                raise ValueError("Duplicate normalized frozen path")
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("Invalid frozen input path")
            result[name] = digest
    if not result or not any(name.startswith("src/") for name in result):
        raise ValueError("No source input anchors")
    return result


def drift(root, manifest):
    result = []
    for name, expected in source_inputs(manifest).items():
        path = root / name
        actual = B.sha(path) if path.is_file() else None
        if actual != expected:
            result.append({"path": name, "expected": expected, "actual": actual})
    return result


def require_origin(root, manifest):
    changed = drift(root, manifest)
    if changed:
        raise ValueError("Source differs from upstream pre-run freeze: " + repr(changed))
