"""Copy every frozen project input, never overwrite pre-existing differing bytes."""

import hashlib
import shutil
import stat
from pathlib import Path

EXCLUDED = {
    ".agent",
    ".local-agents",
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(root):
    root = Path(root).resolve()
    result = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if set(relative.parts) & EXCLUDED or path.suffix == ".pyc":
            continue
        if (
            path.is_symlink()
            or getattr(path.lstat(), "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ValueError("Project input reparse point")
        if path.is_file() and relative.as_posix() != "AGENTS.md":
            result[relative.as_posix()] = digest(path)
    return result


def complete(template, destination, *, accepted_overrides=None):
    template, destination = Path(template).resolve(), Path(destination).resolve()
    if (
        template == destination
        or template in destination.parents
        or destination in template.parents
    ):
        raise ValueError("Distinct snapshot roots required")
    overrides = accepted_overrides or {}
    expected = inventory(template)
    if not set(overrides) <= set(expected):
        raise ValueError("Override outside frozen project")
    expected.update(overrides)
    # Check all conflicts before copying anything; an override never authorizes writing it.
    for relative, sha in expected.items():
        target = destination / relative
        if not target.resolve().is_relative_to(destination):
            raise ValueError("Snapshot path escape")
        if any(
            p.exists()
            and (
                p.is_symlink()
                or getattr(p.lstat(), "st_file_attributes", 0)
                & stat.FILE_ATTRIBUTE_REPARSE_POINT
            )
            for p in (target, *target.parents)
            if p.is_relative_to(destination)
        ):
            raise ValueError("Snapshot reparse point")
        if target.exists() and (not target.is_file() or digest(target) != sha):
            raise ValueError("Existing snapshot input differs: " + relative)
        if relative in overrides and not target.exists():
            raise ValueError("Accepted producer transfer missing: " + relative)
    for relative in expected:
        target = destination / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template / relative, target)
    assert all(digest(destination / path) == sha for path, sha in expected.items())
    return expected
