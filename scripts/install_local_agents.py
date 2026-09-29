"""Conservatively install this kit into another repository.

Only the distributable project-local files are copied. Existing differing files
are conflicts, never overwritten. The default mode is a read-only preview.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


class InstallError(ValueError):
    pass


LEGACY_KIT_TESTS = (
    "test_codex_usage.py",
    "test_real_task_eval.py",
    "test_install_local_agents.py",
)

BENCHMARK_ONLY_KIT_TESTS = {
    "test_capability_matrix_fixture.py",
    "test_role_compat.py",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _distributable(relative: Path) -> bool:
    if relative.parts[0] != ".local-agents":
        return relative == Path("AGENTS.md")
    if any(
        part.lower() in {".agent", "__pycache__", ".pytest_cache", ".venv"}
        for part in relative.parts
    ):
        return False
    if (
        relative.parts[:2] == (".local-agents", "tests")
        and relative.name in BENCHMARK_ONLY_KIT_TESTS
    ):
        return False
    if relative.name.lower() == "config.json":
        return False
    return relative.suffix in {".py", ".ps1", ".md", ".json", ".toml"}


def inventory(source: Path) -> list[Path]:
    if not (source / "AGENTS.md").is_file() or not (source / ".local-agents").is_dir():
        raise InstallError("source must contain AGENTS.md and .local-agents")
    candidates = [Path("AGENTS.md")]
    candidates.extend(
        path.relative_to(source)
        for path in (source / ".local-agents").rglob("*")
        if _distributable(path.relative_to(source))
    )
    for relative in candidates:
        path = source / relative
        if not path.is_file() or path.is_symlink():
            raise InstallError(f"source is not a regular file: {relative}")
    return sorted(candidates, key=str)


def plan(source: Path, target: Path) -> dict[str, list[str]]:
    source = source.resolve(strict=True)
    if not target.is_dir() or target.is_symlink():
        raise InstallError("target must be an existing ordinary directory")
    target = target.resolve(strict=True)
    if source == target or source in target.parents or target in source.parents:
        raise InstallError("source and target must be separate directories")
    source_files = inventory(source)
    result: dict[str, list[str]] = {
        "copy": [],
        "identical": [],
        "conflict": [],
        "legacy_kit_tests": [],
    }
    for relative in source_files:
        destination = target / relative
        if (
            any(
                parent.is_symlink()
                for parent in destination.parents
                if parent != target and target in parent.parents
            )
            or destination.is_symlink()
            or (destination.exists() and not destination.is_file())
        ):
            result["conflict"].append(str(relative))
        elif not destination.exists():
            result["copy"].append(str(relative))
        elif _digest(source / relative) == _digest(destination):
            result["identical"].append(str(relative))
        else:
            result["conflict"].append(str(relative))
    for name in LEGACY_KIT_TESTS:
        relative = Path(".local-agents") / "tests" / name
        if relative not in source_files and (target / relative).is_file():
            result["legacy_kit_tests"].append(str(relative))
    return result


def install(source: Path, target: Path, *, apply: bool = False) -> dict[str, object]:
    actions = plan(source, target)
    if apply and actions["conflict"]:
        raise InstallError(
            "conflicting files require manual review: " + ", ".join(actions["conflict"])
        )
    if apply:
        for name in actions["copy"]:
            relative = Path(name)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, destination)
    return {
        "applied": apply,
        **actions,
        "config_action": "preserved; configure manually",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview or install local workers without overwrites"
    )
    parser.add_argument(
        "--target", type=Path, required=True, help="existing target repository root"
    )
    parser.add_argument(
        "--source", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--apply", action="store_true", help="copy files after conflict preflight"
    )
    args = parser.parse_args()
    try:
        report = install(args.source, args.target, apply=args.apply)
    except (OSError, InstallError) as exc:
        print(f"install error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
