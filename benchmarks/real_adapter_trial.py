"""Freeze real read-only sibling code and preflight explicitly injected faults.

Only the kit receives copies and generated workspaces. No local model invocation,
dependency installation or sibling project test execution is performed here.
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command

SOURCE = KIT.parent / "agent-evaluation-harness"
FROZEN = KIT / "benchmarks/fixtures/real-adapter-datetime-v1"
BASE = WORK / "real-adapter-datetime-trial-1"
COMMON = "src/evaluation_harness/adapters/common.py"
EXTRA = KIT / "benchmarks/fixtures/real-adapter-datetime-extra/test_datetime_trial.py"
PATHS = (
    "LICENSE",
    "pyproject.toml",
    "src/evaluation_harness/__init__.py",
    "src/evaluation_harness/contracts.py",
    "src/evaluation_harness/adapters/__init__.py",
    "src/evaluation_harness/adapters/base.py",
    COMMON,
    "src/evaluation_harness/adapters/generic_otel.py",
    "src/evaluation_harness/adapters/agent_runtime_kit.py",
    "src/evaluation_harness/canonical/__init__.py",
    "src/evaluation_harness/canonical/models.py",
    "src/evaluation_harness/canonical/fingerprint.py",
    "src/evaluation_harness/trace_sources/__init__.py",
    "src/evaluation_harness/trace_sources/base.py",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/unit/test_adapters.py",
    "tests/fixtures/synthetic_traces/generic_multi_turn.json",
    "tests/fixtures/synthetic_traces/runtime_kit.json",
)


def git_info(root):
    return {
        key: subprocess.check_output(["git", "-C", str(root), *argv], text=True).strip()
        for key, argv in {
            "head": ["rev-parse", "HEAD"],
            "status": ["status", "--short"],
        }.items()
    }


def mutate(source, mode):
    """Replace only the real private helper, keeping every other byte of text."""
    if mode == "reference":
        return source
    tree = ast.parse(source)
    node = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_datetime"
    )
    lines = source.splitlines(keepends=True)
    body = "".join(lines[node.lineno - 1 : node.end_lineno])
    expected = "        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)"
    if expected not in body:
        raise ValueError(
            "source changed: inspect helper contract before injecting faults"
        )
    if mode in {"naive", "combined"}:
        body = body.replace(expected, "        return parsed")
    if mode in {"swallow", "combined"}:
        parse = '        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))'
        body = body.replace(
            parse,
            "        try:\n    "
            + parse
            + "\n        except ValueError:\n            return default",
        )
    if mode not in {"naive", "swallow", "combined"}:
        raise ValueError("unknown mutant")
    result = (
        "".join(lines[: node.lineno - 1])
        + body
        + "\n"
        + "".join(lines[node.end_lineno :])
    )
    original_others = [ast.dump(n) for n in tree.body if n is not node]
    actual_others = [
        ast.dump(n)
        for n in ast.parse(result).body
        if not (isinstance(n, ast.FunctionDef) and n.name == "_datetime")
    ]
    if original_others != actual_others:
        raise ValueError("mutation escaped private helper")
    return result


def freeze():
    if FROZEN.exists():
        raise FileExistsError("freeze is immutable; register a new version")
    before = git_info(SOURCE)
    hashes = {}
    for relative in PATHS:
        path = SOURCE / relative
        path.resolve().relative_to(SOURCE.resolve())
        if path.is_symlink() or path.stat().st_file_attributes & 0x400:
            raise ValueError("source reparse path is not allowed")
        hashes[relative] = digest(path)
    FROZEN.mkdir(parents=True)
    for relative, sha in hashes.items():
        target = FROZEN / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, target)
        if digest(target) != sha or digest(SOURCE / relative) != sha:
            raise ValueError("source changed during freeze")
    shutil.copyfile(EXTRA, FROZEN / "tests/test_datetime_trial.py")
    if git_info(SOURCE) != before:
        raise ValueError("sibling changed during freeze; do not mislabel provenance")
    write(
        FROZEN / "provenance.json",
        {
            "source_root": str(SOURCE),
            "source_git": before,
            "copied_original_files": hashes,
            "primary_added_test": {
                "path": "tests/test_datetime_trial.py",
                "sha256": digest(EXTRA),
            },
            "driver_sha256": digest(Path(__file__)),
            "classification": "Exact current working-tree module/test copies plus Primary supplemental acceptance; original dirty contracts recorded, not claimed as pristine HEAD",
            "real_call_chain": "GenericOtelAdapter.normalize -> build_samples -> _datetime -> CanonicalSample",
            "excluded": "PostgreSQL, MLflow, jobs, real project deployment and new public compatibility behavior",
            "sibling_writes": False,
        },
    )
    print(json.dumps({"frozen": str(FROZEN), "original_files": len(hashes)}))


def verify():
    frozen = read(FROZEN / "provenance.json")
    for relative, sha in frozen["copied_original_files"].items():
        if digest(FROZEN / relative) != sha:
            raise ValueError("frozen source drift: " + relative)
    added = frozen["primary_added_test"]
    if digest(FROZEN / added["path"]) != added["sha256"]:
        raise ValueError("protected acceptance drift")
    if digest(Path(__file__)) != frozen["driver_sha256"]:
        raise ValueError("frozen driver drift")
    return frozen


def preflight():
    verify()
    BASE.mkdir(parents=True, exist_ok=False)
    source = (FROZEN / COMMON).read_text(encoding="utf-8")
    rows = []
    for mode in ("reference", "naive", "swallow", "combined"):
        root = BASE / mode
        shutil.copytree(FROZEN, root)
        if mode != "reference":
            # Generated benchmark candidate, never the frozen source or sibling.
            (root / COMMON).write_text(mutate(source, mode), encoding="utf-8")
        junit = root / "trial.xml"
        observed = command(
            root,
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(root / "pytest-temp"),
                "--junitxml=" + str(junit),
            ],
            timeout=180,
        )
        nodes = list(ET.parse(junit).getroot().iter("testcase"))
        failures = [n.get("name") for n in nodes if n.find("failure") is not None]
        errors = [n.get("name") for n in nodes if n.find("error") is not None]
        skipped = [n.get("name") for n in nodes if n.find("skipped") is not None]
        static = [
            command(root, [sys.executable, "-m", "ruff", "check", "src", "tests"]),
            command(
                root,
                [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"],
            ),
        ]
        # No formatting of frozen original copies. Synthetic mutants may need
        # formatting; their expected failure must still be semantic, not collection.
        expected = (
            set()
            if mode == "reference"
            else {
                "test_real_adapter_roundtrip",
                *(
                    ["test_naive_string_utc"]
                    if mode == "naive"
                    else ["test_invalid_string"]
                    if mode == "swallow"
                    else ["test_naive_string_utc", "test_invalid_string"]
                ),
            }
        )
        passed = (
            len(nodes) == 10
            and not errors
            and not skipped
            and set(failures) == expected
        )
        passed = passed and observed["exit"] == (0 if mode == "reference" else 1)
        if mode == "reference":
            passed = passed and all(c["exit"] == 0 for c in static)
        rows.append(
            {
                "mode": mode,
                "tests": len(nodes),
                "failures": failures,
                "errors": errors,
                "skipped": skipped,
                "expected_failures": sorted(expected),
                "passed": passed,
                "pytest": observed,
                "static": static,
            }
        )
    verify()
    write(
        BASE / "preflight.json",
        {
            "rows": rows,
            "passed": all(r["passed"] for r in rows),
            "model_calls": 0,
            "primary_implementation_trial": False,
        },
    )
    write(
        BASE / "task-contract.json",
        {
            "feature_id": "real-adapter-datetime-trial-1",
            "unit_id": "private-time-normalization",
            "feature_risk": "medium",
            "unit_risk": "medium",
            "integration_risk": "medium",
            "risk_rationale": "Restore an existing private normalization invariant; no adapter/version/schema/public interface or network/storage changes",
            "owned_contract_ids": ["existing-datetime-normalization"],
            "dependencies": [],
            "candidate": str(BASE / "combined"),
            "writable": [COMMON],
            "edit_anchor": "_datetime",
            "readonly": "All other source, original three adapter tests, seven Primary tests and project checks",
            "required_behavior": "Preserve datetime object identity, Z and offsets; naive strings become UTC; invalid strings raise ValueError; non-string fallback preserves default identity; real trace/turn adapters retain messages/IDs and reject invalid timestamps without mutating inputs",
            "validation": "Ten tests plus original project Ruff check/format. Protected acceptance read-only. Public models, sample identity and call-chain functions must not change.",
            "reference_visibility": "Frozen original helper/original copies and preflight reference are Primary-only; exclude these roots from any worker packet",
            "live_worker_status": "not_started",
            "deployment_status": "not_attempted",
            "coordinator": "Optional one-unit supervised proposal, not forced broad decomposition",
            "dependency_note": "Copied original pyproject pytest>=8.3,<9; diagnostic runner uses pytest9.1.1, so this does not establish original project environment equivalence. Pyright not available/not run. No dependency install.",
        },
    )
    print(
        json.dumps(
            {
                "base": str(BASE),
                "passed": all(r["passed"] for r in rows),
                "rows": [
                    {k: r[k] for k in ("mode", "tests", "failures", "passed")}
                    for r in rows
                ],
            }
        )
    )
    if not all(r["passed"] for r in rows):
        raise ValueError(
            "preflight failed; inspect retained logs before live delegation"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "preflight"))
    args = parser.parse_args()
    freeze() if args.action == "freeze" else preflight()
