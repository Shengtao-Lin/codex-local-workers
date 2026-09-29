"""Disposable live Reviewer challenge with an untested, contract-breaking branch.

The Coder archive is synthesized for this benchmark, but its focused pytest and Ruff
evidence are executed on the exact buggy source before Reviewer sees it.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def file_fact(path: Path, relative: str) -> dict:
    raw = path.read_bytes()
    return {
        "path": relative,
        "exists": True,
        "kind": "file",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }


def caught_hidden_bug(report: dict, source: Path) -> bool:
    injected_lines = {
        number
        for number, line in enumerate(
            source.read_text(encoding="utf-8").splitlines(), 1
        )
        if "len(value) > 100" in line or line.strip() == "return value"
    }
    findings = report.get("findings")
    if not isinstance(findings, list):
        findings = []
    return report.get("decision") in {"rework", "escalate"} and any(
        isinstance(finding, dict)
        and finding.get("path") == "src/slug.py"
        and finding.get("line") in injected_lines
        and "100" in str(finding.get("evidence", ""))
        for finding in findings
    )


def run(
    config_path: Path,
    source_workspace: Path,
    reviewer_model: str | None = None,
    reviewer_temperature: float | None = None,
    risk: str = "medium",
    reviewer_native_tools: bool = False,
) -> dict:
    source_workspace = source_workspace.resolve()
    prior_run = (
        source_workspace / ".agent" / "tasks" / "live-slug" / "runs" / "normalize-a1"
    )
    source_packet = json.loads((prior_run / "packet.json").read_text(encoding="utf-8"))
    original = (source_workspace / "src" / "slug.py").read_text(encoding="utf-8")
    if "def normalize_tag(value):\n" not in original:
        raise ValueError("source smoke fixture has no normalize_tag anchor")
    buggy = original.replace(
        "def normalize_tag(value):\n",
        "def normalize_tag(value):\n"
        "    if isinstance(value, str) and len(value) > 100:\n"
        "        return value\n",
        1,
    )
    root = (
        Path(tempfile.gettempdir()) / f"local-review-challenge-{uuid.uuid4().hex[:12]}"
    )
    root.mkdir(parents=True, exist_ok=False)
    review_config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    source_config_path = source_workspace / ".local-agents" / "config.json"
    source_config = json.loads(source_config_path.read_text(encoding="utf-8-sig"))
    profile_id = source_packet["validation_profile"]
    review_config.setdefault("validation_profiles", {})[profile_id] = source_config[
        "validation_profiles"
    ][profile_id]
    review_config["python"] = sys.executable
    if reviewer_model is not None:
        review_config["reviewer_model"] = reviewer_model
    if reviewer_temperature is not None:
        review_config["reviewer_temperature"] = reviewer_temperature
    if reviewer_native_tools:
        review_config["reviewer_native_tools"] = True
    for profile in review_config.get("validation_profiles", {}).values():
        profile["python"] = sys.executable
    review_config_path = root / "reviewer-config.json"
    write_json(review_config_path, review_config)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    source = root / "src" / "slug.py"
    test = root / "tests" / "test_slug.py"
    source.write_text(buggy, encoding="utf-8")
    test.write_bytes((source_workspace / "tests" / "test_slug.py").read_bytes())
    helper = source_workspace / "src" / "tag_rules.py"
    if helper.is_file():
        shutil.copy2(helper, root / "src" / "tag_rules.py")
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--select", "I", "--fix", "tests"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    packet = dict(source_packet)
    packet.update(
        {
            "task_id": "review-challenge",
            "feature_id": "review-challenge",
            "unit_id": "normalize-tag",
            "run_id": "buggy-a1",
            "risk": {
                "feature": risk,
                "unit": risk,
                "integration": risk,
                "reasons": [
                    "Review an isolated normalization change and its focused tests."
                ],
            },
        }
    )
    run_root = root / ".agent" / "tasks" / "review-challenge" / "runs" / "buggy-a1"
    run_root.mkdir(parents=True)
    write_json(run_root / "packet.json", packet)
    junit_path = root / "junit.xml"
    pytest = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_slug.py",
            "-q",
            f"--junitxml={junit_path}",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    format_check = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    lint = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if any(item.returncode != 0 for item in (pytest, format_check, lint)):
        return {
            "workspace": str(root),
            "status": "fixture_invalid",
            "pytest": pytest.stdout[-800:] + pytest.stderr[-800:],
            "format": format_check.stdout[-800:] + format_check.stderr[-800:],
            "lint": lint.stdout[-800:] + lint.stderr[-800:],
        }
    write_json(
        run_root / "validation.json",
        {
            "status": "passed",
            "focused_tests": {
                "status": "passed",
                "inputs_unchanged": True,
                "junit": {"available": junit_path.is_file(), "executed": 4},
            },
            "configured_checks": [
                {
                    "id": "ruff-format",
                    "status": "passed",
                    "exit_code": format_check.returncode,
                },
                {"id": "ruff-check", "status": "passed", "exit_code": lint.returncode},
            ],
        },
    )
    validation_inputs = {
        "src/slug.py": file_fact(source, "src/slug.py"),
        "tests/test_slug.py": file_fact(test, "tests/test_slug.py"),
    }
    copied_helper = root / "src" / "tag_rules.py"
    if copied_helper.is_file():
        validation_inputs["src/tag_rules.py"] = file_fact(
            copied_helper, "src/tag_rules.py"
        )
    write_json(run_root / "post-state.json", {"validation_inputs": validation_inputs})
    write_json(run_root / "handoff.json", {"status": "ready_for_review"})
    write_json(run_root / "completed.json", {"status": "ready_for_review"})
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            buggy.splitlines(keepends=True),
            fromfile="a/src/slug.py",
            tofile="b/src/slug.py",
        )
    )
    (run_root / "cumulative.diff").write_text(diff, encoding="utf-8")
    request = {
        "schema_version": 1,
        "task_id": "review-challenge",
        "unit_id": "normalize-tag",
        "run_id": "buggy-a1",
        "review_id": "muse-review",
    }
    request_path = root / "review-request.json"
    write_json(request_path, request)
    report_path = root / "review-report.json"
    reviewer = subprocess.run(
        [
            sys.executable,
            str(KIT / ".local-agents" / "local-review.py"),
            "--request",
            str(request_path),
            "--config",
            str(review_config_path),
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
    findings = (
        report.get("findings") if isinstance(report.get("findings"), list) else []
    )
    caught = caught_hidden_bug(report, source)
    return {
        "workspace": str(root),
        "reviewer_model": review_config["reviewer_model"],
        "reviewer_temperature": review_config["reviewer_temperature"],
        "risk": risk,
        "reviewer_native_tools": reviewer_native_tools,
        "status": "reviewed" if reviewer.returncode == 0 else "reviewer_failed",
        "focused_tests_passed": True,
        "ruff_passed": True,
        "hidden_contract_bug": "Long strings are returned unchanged instead of normalized.",
        "reviewer_decision": report.get("decision"),
        "findings": findings,
        "caught_hidden_bug": caught,
        "read_paths": report.get("runtime_facts", {}).get("read_paths"),
        "protocol_errors": report.get("runtime_facts", {}).get("protocol_error_count"),
        "reviewer_output_tail": (reviewer.stdout + reviewer.stderr)[-800:],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-workspace", required=True, type=Path)
    parser.add_argument(
        "--config", default=KIT / ".local-agents" / "config.json", type=Path
    )
    parser.add_argument("--reviewer-model", help="Disposable Reviewer model override")
    parser.add_argument("--reviewer-temperature", type=float)
    parser.add_argument("--risk", choices=["medium", "high"], default="medium")
    parser.add_argument("--reviewer-native-tools", action="store_true")
    args = parser.parse_args()
    result = run(
        args.config,
        args.source_workspace,
        args.reviewer_model,
        args.reviewer_temperature,
        args.risk,
        args.reviewer_native_tools,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("caught_hidden_bug") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
