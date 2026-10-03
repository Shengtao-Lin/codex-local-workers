"""Frozen real-source Reviewer challenge: an untested seed-zero selection bypass."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from reviewer_challenge import KIT, file_fact, write_json

SOURCE = Path("F:/ChatGPT/agent-evaluation-harness")
WORK = KIT / "benchmarks" / "work" / "stability-v1"
PINNED = {
    "src/evaluation_harness/contracts.py": "cd14b79ba672c367ad513c5ed81ea31996f592a62cee0846940d8c66c209f213",
    "src/evaluation_harness/datasets/selection.py": "4c337d46d8a1c82b5ad7954f482545282477195c20eae7fd5de2a922b431a0ab",
}
TARGET = "src/evaluation_harness/datasets/selection.py"
TEST = "tests/test_selection_review.py"
ANCHOR = "        random.Random(policy.seed).shuffle(ordered)\n"
BUG = "        if policy.seed == 0:\n            return ordered[: policy.limit]\n"
FOCUSED_TEST = """from datetime import datetime, timezone
from random import Random

from evaluation_harness.contracts import SelectionPolicy
from evaluation_harness.datasets.selection import select_records


def choose(records, seed):
    return select_records(
        records,
        SelectionPolicy(strategy="random", seed=seed, limit=3),
        identity=lambda item: item,
        timestamp=lambda item: datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def test_nonzero_seed_uses_seeded_shuffle():
    expected = list("abcdef")
    Random(7).shuffle(expected)
    assert choose(list("fedcba"), 7) == expected[:3]


def test_nonzero_seed_is_input_order_independent():
    assert choose(list("abcdef"), 7) == choose(list("fedcba"), 7)
"""
ORACLE_TEST = """from datetime import datetime, timezone
from random import Random

from evaluation_harness.contracts import SelectionPolicy
from evaluation_harness.datasets.selection import select_records


def test_default_seed_still_shuffles():
    rows = list("fedcba")
    expected = sorted(rows)
    Random(0).shuffle(expected)
    actual = select_records(
        rows,
        SelectionPolicy(strategy="random", limit=3),
        identity=lambda item: item,
        timestamp=lambda item: datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    assert actual == expected[:3]
"""
RUNTIME_SOURCE = Path("F:/ChatGPT/agent-runtime-kit")
RUNTIME_PINNED = {
    "src/agent_runtime/models.py": "608a31dd2a09692a380dfe5ba0d9eb97accb1f7420f6d47d1e96d454b7666577"
}
RUNTIME_TARGET = "src/agent_runtime/models.py"
RUNTIME_TEST = "tests/test_metadata_review.py"
RUNTIME_ANCHOR = "    for key in value:\n"
RUNTIME_BUG = '        if key.startswith("x-"):\n            continue\n'
RUNTIME_CONTROL_BEFORE = "        if not key or len(key) > 128:\n"
RUNTIME_CONTROL_AFTER = "        if not key or 128 < len(key):\n"
RUNTIME_FOCUSED_TEST = """import pytest

from agent_runtime.models import validate_metadata


def test_regular_oversized_key_rejected():
    with pytest.raises(ValueError, match="128"):
        validate_metadata({"a" * 129: 1})


def test_boundary_and_json_checks_remain_valid():
    assert validate_metadata({"a" * 128: True}) == {"a" * 128: True}
    with pytest.raises(ValueError, match="JSON-compatible"):
        validate_metadata({"valid": object()})
"""
RUNTIME_ORACLE_TEST = """from agent_runtime.models import validate_metadata


def test_prefixed_oversized_key_is_rejected():
    try:
        validate_metadata({"x-" + "a" * 127: 1})
    except ValueError:
        return
    assert False, "oversized prefixed metadata key was accepted"
"""


def run_command(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )


def caught_bug(report: dict, source: Path, variant: str = "selection") -> bool:
    target = RUNTIME_TARGET if variant == "metadata" else TARGET
    contract_id = "metadata-key-bounds" if variant == "metadata" else "random-seed"
    branch_text = (
        'if key.startswith("x-"):' if variant == "metadata" else "if policy.seed == 0:"
    )
    keywords = (
        ("key", "128", "prefix")
        if variant == "metadata"
        else ("seed", "shuffle", "zero")
    )
    lines = source.read_text(encoding="utf-8").splitlines()
    branch = next(
        (index for index, line in enumerate(lines, 1) if line.strip() == branch_text),
        None,
    )
    return report.get("decision") in {"rework", "escalate"} and any(
        isinstance(finding, dict)
        and finding.get("path") == target
        and finding.get("contract_id") == contract_id
        and finding.get("line") in {branch, branch + 1 if branch else None}
        and any(
            word
            in str(finding.get("evidence", "")).lower()
            + " "
            + str(finding.get("suggested_fix", "")).lower()
            for word in keywords
        )
        for finding in (report.get("findings") or [])
    )


def clean_control_passed(report: dict) -> bool:
    """A semantically equivalent edit must not trigger contract rework."""
    return report.get("decision") == "pass_to_primary" and not report.get("findings")


def run(
    config_path: Path,
    variant: str = "selection",
    reviewer_model: str | None = None,
    reasoning_strength: str | None = None,
) -> dict:
    if variant not in {"selection", "metadata", "metadata-control"}:
        raise ValueError(f"unknown challenge variant: {variant}")
    metadata = variant.startswith("metadata")
    clean_control = variant == "metadata-control"
    source_root = RUNTIME_SOURCE if metadata else SOURCE
    pinned = RUNTIME_PINNED if metadata else PINNED
    target = RUNTIME_TARGET if metadata else TARGET
    test_relative = RUNTIME_TEST if metadata else TEST
    anchor = RUNTIME_ANCHOR if metadata else ANCHOR
    bug = RUNTIME_BUG if metadata else BUG
    focused_test = RUNTIME_FOCUSED_TEST if metadata else FOCUSED_TEST
    oracle_test = RUNTIME_ORACLE_TEST if metadata else ORACLE_TEST
    contract_id = "metadata-key-bounds" if metadata else "random-seed"
    run_id = f"{variant}-{uuid.uuid4().hex[:8]}"
    root = WORK / f"reviewer-real-{run_id}"
    root.mkdir(parents=True, exist_ok=False)
    for relative, expected in pinned.items():
        origin = source_root / relative
        actual = hashlib.sha256(origin.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"pinned source changed: {relative}: {actual}")
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, destination)
    # The upstream pinned snapshot predates this kit's Ruff format version.
    # Normalize the disposable copy before defining the Coder delta.
    normalized = run_command(root, "ruff", "format", "src")
    if normalized.returncode:
        raise ValueError(f"could not format copied source: {normalized.stdout}")
    source = root / target
    original = source.read_text(encoding="utf-8")
    if original.count(anchor) != 1:
        raise ValueError("mutation anchor is not unique")
    if clean_control:
        if original.count(RUNTIME_CONTROL_BEFORE) != 1:
            raise ValueError("control mutation anchor is not unique")
        buggy = original.replace(RUNTIME_CONTROL_BEFORE, RUNTIME_CONTROL_AFTER, 1)
    else:
        buggy = (
            original.replace(anchor, anchor + bug, 1)
            if metadata
            else original.replace(anchor, bug + anchor, 1)
        )
    source.write_text(buggy, encoding="utf-8")
    test = root / test_relative
    test.parent.mkdir(parents=True)
    test.write_text(focused_test, encoding="utf-8")
    oracle = root / (
        "oracle/test_prefixed_key.py" if metadata else "oracle/test_seed_zero.py"
    )
    oracle.parent.mkdir(parents=True)
    oracle.write_text(oracle_test, encoding="utf-8")
    for directory in (root / "src").rglob("*"):
        if directory.is_dir() and not (directory / "__init__.py").exists():
            (directory / "__init__.py").touch()
    # Import directly from the copied source rather than the installed sibling repository.
    (root / "pytest.ini").write_text("[pytest]\npythonpath = src\n", encoding="utf-8")
    write_json(
        root / "fixture-source.json",
        {
            "repository": str(source_root),
            "files": pinned,
            "mutation": RUNTIME_CONTROL_AFTER if clean_control else bug,
        },
    )
    junit = root / "junit.xml"
    pytest = run_command(root, "pytest", test_relative, "-q", f"--junitxml={junit}")
    formatting = run_command(root, "ruff", "format", "--check", "src", "tests")
    lint = run_command(root, "ruff", "check", "src", "tests")
    hidden = run_command(root, "pytest", oracle.relative_to(root).as_posix(), "-q")
    if (
        any(result.returncode for result in (pytest, formatting, lint))
        or hidden.returncode != (0 if clean_control else 1)
        or (not clean_control and "AssertionError" not in hidden.stdout)
    ):
        return {
            "workspace": str(root),
            "status": "fixture_invalid",
            "pytest": pytest.stdout[-1500:] + pytest.stderr[-1500:],
            "format": formatting.stdout[-1500:] + formatting.stderr[-1500:],
            "lint": lint.stdout[-1500:] + lint.stderr[-1500:],
            "hidden_oracle": hidden.stdout[-1500:] + hidden.stderr[-1500:],
        }
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if reviewer_model is not None:
        config["reviewer_model"] = reviewer_model
    if reasoning_strength is not None:
        config["reviewer_reasoning_strength"] = reasoning_strength
    config.update(
        {
            "python": sys.executable,
            "reviewer_require_approved_execution": True,
            "validation_profiles": {
                "real-review-strict": {
                    "python": sys.executable,
                    "compile": True,
                    "pytest_argv": ["-B", "-m", "pytest"],
                    "commands": [
                        {
                            "id": "ruff-format",
                            "argv": [
                                "{python}",
                                "-m",
                                "ruff",
                                "format",
                                "--check",
                                "src",
                                "tests",
                            ],
                        },
                        {
                            "id": "ruff-check",
                            "argv": ["{python}", "-m", "ruff", "check", "src", "tests"],
                        },
                    ],
                }
            },
        }
    )
    config_path_copy = root / "reviewer-config.json"
    write_json(config_path_copy, config)
    packet = {
        "schema_version": 2,
        "task_id": f"reviewer-real-{variant}",
        "feature_id": f"reviewer-real-{variant}",
        "unit_id": contract_id,
        "run_id": run_id,
        "attempt": 1,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": (
            "Reject every metadata key longer than 128 characters regardless of prefix."
            if metadata
            else "Keep random selection deterministic and seeded for every valid integer seed."
        ),
        "risk": {
            "feature": "high",
            "unit": "high",
            "integration": "high",
            "reasons": (
                ["Public metadata bounds must apply to all key prefixes."]
                if metadata
                else [
                    "Selection semantics are public and seed zero is the model's valid default."
                ]
            ),
        },
        "dependencies": [],
        "owned_contract_ids": [contract_id],
        "scope": {
            "read": ["src", "tests"],
            "readonly": [test_relative],
            "modify": [target],
            "create": [],
            "forbidden": [],
        },
        "edit_targets": [
            {
                "path": target,
                "anchor": "def validate_metadata" if metadata else "def select_records",
            }
        ],
        "required_behavior": [
            {
                "id": contract_id,
                "text": (
                    "Every metadata key, including keys starting with x-, must contain 1–128 characters. No prefix exempts a key from length validation; valid JSON-compatible metadata and the encoded-byte limit remain unchanged."
                    if metadata
                    else "For every valid integer seed, including the default seed 0, random strategy sorts eligible records by identity, applies random.Random(policy.seed).shuffle to that entire ordered list, then returns the first policy.limit records. Input order must not affect the result; no seed bypasses shuffle."
                ),
                "risk_floor": "high",
            }
        ],
        "acceptance_criteria": [
            {"id": "focused-tests", "text": "Protected focused tests pass."},
            {"id": "static", "text": "Ruff format and lint pass."},
        ],
        "acceptance_scenarios": (
            [
                {"id": "normal", "text": "A 129-character ordinary key is rejected."},
                {
                    "id": "boundary",
                    "text": "A 129-character x- prefixed key is also rejected.",
                },
            ]
            if metadata
            else [
                {"id": "normal", "text": "Nonzero seed uses seeded shuffle."},
                {
                    "id": "boundary",
                    "text": "Default seed zero also uses seeded shuffle.",
                },
            ]
        ),
        "implementation_guidance": [],
        "validation_profile": "real-review-strict",
        "focused_tests": [test_relative],
    }
    archive = root / ".agent" / "tasks" / packet["task_id"] / "runs" / run_id
    archive.mkdir(parents=True)
    write_json(archive / "packet.json", packet)
    write_json(
        archive / "validation.json",
        {
            "status": "passed",
            "focused_tests": {
                "status": "passed",
                "inputs_unchanged": True,
                "junit": {"available": True, "executed": 2},
            },
            "configured_checks": [
                {"id": "ruff-format", "status": "passed", "exit_code": 0},
                {"id": "ruff-check", "status": "passed", "exit_code": 0},
            ],
        },
    )
    write_json(
        archive / "post-state.json",
        {
            "validation_inputs": {
                relative: file_fact(root / relative, relative)
                for relative in (*pinned, test_relative)
            }
        },
    )
    write_json(archive / "handoff.json", {"status": "ready_for_review"})
    write_json(archive / "completed.json", {"status": "ready_for_review"})
    (archive / "cumulative.diff").write_text(
        "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                buggy.splitlines(keepends=True),
                fromfile=f"a/{target}",
                tofile=f"b/{target}",
            )
        ),
        encoding="utf-8",
    )
    request = {
        "schema_version": 1,
        "task_id": packet["task_id"],
        "unit_id": packet["unit_id"],
        "run_id": run_id,
        "review_id": "muse-review",
    }
    request_path = root / "review-request.json"
    report_path = root / "review-report.json"
    write_json(request_path, request)
    reviewer = subprocess.run(
        [
            sys.executable,
            str(KIT / ".local-agents/local-review.py"),
            "--request",
            str(request_path),
            "--config",
            str(config_path_copy),
            "--report",
            str(report_path),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=720,
        check=False,
    )
    report = (
        json.loads(report_path.read_text(encoding="utf-8"))
        if report_path.is_file()
        else {}
    )
    result = {
        "workspace": str(root),
        "status": "reviewed" if reviewer.returncode == 0 else "reviewer_failed",
        "reviewer_model": config["reviewer_model"],
        "reasoning_strength": config.get("reviewer_reasoning_strength"),
        "focused_tests_passed": True,
        "ruff_passed": True,
        "hidden_oracle_failed_as_expected": not clean_control,
        "hidden_oracle_passed_as_expected": clean_control,
        "reviewer_decision": report.get("decision"),
        "findings": report.get("findings"),
        "caught_hidden_bug": (
            caught_bug(report, source, variant) if not clean_control else False
        ),
        "clean_control_passed": clean_control_passed(report) if clean_control else None,
        "read_paths": report.get("runtime_facts", {}).get("read_paths"),
        "protocol_errors": report.get("runtime_facts", {}).get("protocol_error_count"),
        "reviewer_output_tail": (reviewer.stdout + reviewer.stderr)[-1000:],
    }
    write_json(root / "challenge-result.json", result)
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=KIT / ".local-agents/config.json"
    )
    parser.add_argument(
        "--variant",
        choices=["selection", "metadata", "metadata-control"],
        default="selection",
    )
    parser.add_argument("--reviewer-model", help="Disposable Reviewer candidate model")
    parser.add_argument(
        "--reasoning-strength", choices=("low", "medium", "high", "xhigh")
    )
    args = parser.parse_args()
    result = run(
        args.config, args.variant, args.reviewer_model, args.reasoning_strength
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return (
        0
        if result.get("caught_hidden_bug") or result.get("clean_control_passed")
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
