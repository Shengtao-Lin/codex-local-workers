"""Opt-in disposable live LM Studio Explorer -> Coder -> Reviewer smoke test.

Creates a fresh workspace under the system temporary directory and retains its reports.
It never edits the source kit or a user project.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
INSTALL_DIR = KIT / "scripts"
if str(INSTALL_DIR) not in sys.path:
    sys.path.insert(0, str(INSTALL_DIR))
from install_local_agents import install

SOURCE = "def normalize_tag(value):\n    return value.strip().lower()\n"
TESTS = """import pytest

from src.slug import normalize_tag
from src.tag_rules import normalize_words


def test_normal():
    assert normalize_tag("  Hello World  ") == "hello-world"


def test_whitespace_boundary():
    assert normalize_tag("A\\t  B\\nC") == "a-b-c"


def test_empty_rejected():
    with pytest.raises(ValueError):
        normalize_tag("   ")


def test_non_string_rejected():
    with pytest.raises(TypeError):
        normalize_tag(123)


def test_helper_collapses_whitespace():
    assert normalize_words("A\\t  B\\nC") == ["A", "B", "C"]
"""


def _run(
    root: Path, entry: str, args: list[str], *, report_name: str | None = None
) -> tuple[int, dict]:
    report = root / ".agent" / (report_name or f"{entry}.report.json")
    completed = subprocess.run(
        [
            sys.executable,
            str(root / ".local-agents" / entry),
            *args,
            "--report",
            str(report),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1000,
        check=False,
    )
    data = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
    return completed.returncode, data


def inherit_lifecycle_config(source: dict, target: dict) -> None:
    """Keep diagnostic role launches on the active model lifecycle policy."""
    for key in (
        "single_model_residency",
        "model_switch_timeout_seconds",
        "reviewer_preload_model",
        "reviewer_model_load_timeout_seconds",
        "reviewer_reasoning_strength",
    ):
        if key in source:
            target[key] = source[key]


def run(
    config_path: Path,
    *,
    explorer_mode: str | None = None,
    existing_python: Path | None = None,
    workspace_parent: Path | None = None,
) -> dict:
    source_config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if existing_python is not None:
        existing_python = existing_python.resolve(strict=True)
        subprocess.run(
            [str(existing_python), "-c", "import pytest, ruff"],
            check=True,
            capture_output=True,
            text=True,
        )
    root = (
        workspace_parent.resolve()
        if workspace_parent is not None
        else Path(tempfile.gettempdir())
    ) / f"local-worker-live-smoke-{uuid.uuid4().hex[:12]}"
    root.mkdir(parents=True, exist_ok=False)
    install(KIT, root, apply=True)
    venv_python = existing_python
    if venv_python is None:
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError(
                "uv is required to create the replayable smoke environment"
            )
        venv_python = root / ".venv" / "Scripts" / "python.exe"
        subprocess.run(
            [uv, "venv", str(root / ".venv")],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [uv, "pip", "install", "--python", str(venv_python), "pytest", "ruff"],
            check=True,
            capture_output=True,
            text=True,
        )
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / ".agent").mkdir()
    (root / "src" / "slug.py").write_text(SOURCE, encoding="utf-8")
    (root / "tests" / "test_slug.py").write_text(TESTS, encoding="utf-8")
    config = {
        "lmstudio_base_url": source_config["lmstudio_base_url"],
        "explorer_model": source_config["explorer_model"],
        "explorer_mode": explorer_mode
        or source_config.get("explorer_mode", "investigate"),
        "explorer_context_length": source_config.get("explorer_context_length"),
        "coder_model": source_config["coder_model"],
        "coder_context_length": source_config.get("coder_context_length"),
        "reviewer_model": source_config.get(
            "reviewer_model", source_config["coder_model"]
        ),
        "reviewer_context_length": source_config.get("reviewer_context_length"),
        "model_context_safety_margin": source_config.get(
            "model_context_safety_margin", 1024
        ),
        "coder_structured_output": source_config.get("coder_structured_output", True),
        "reviewer_structured_output": source_config.get(
            "reviewer_structured_output", True
        ),
        "reviewer_native_tools": source_config.get("reviewer_native_tools", False),
        "explorer_reasoning_effort": source_config.get(
            "explorer_reasoning_effort", "low"
        ),
        "coder_temperature": source_config.get("coder_temperature", 0.1),
        "reviewer_temperature": source_config.get("reviewer_temperature", 0.1),
        "reviewer_top_p": source_config.get("reviewer_top_p", 0.95),
        "reviewer_top_k": source_config.get("reviewer_top_k", 64),
        "reviewer_max_tokens": source_config.get("reviewer_max_tokens", 8192),
        "reviewer_require_source_and_test_reads": source_config.get(
            "reviewer_require_source_and_test_reads", True
        ),
        "reviewer_require_approved_execution": True,
        "reviewer_require_search": True,
        "python": str(venv_python),
        "validation_profiles": {
            "smoke-strict": {
                "python": str(venv_python),
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
        "require_edit_targets": True,
        "max_model_turns": 28,
        "max_reviewer_turns": 16,
        "invocation_timeout_seconds": 900,
        "reviewer_invocation_timeout_seconds": 600,
        "explorer_invocation_timeout_seconds": 600,
        "diagnostic_logging": True,
    }
    inherit_lifecycle_config(source_config, config)
    local_config = root / ".local-agents" / "config.json"
    local_config.write_text(json.dumps(config, indent=2), encoding="utf-8")
    explorer_compat_config = root / ".local-agents" / "config-explorer-compat.json"
    explorer_compat_config.write_text(
        json.dumps(
            {
                **config,
                "explorer_require_regex_search": True,
                "explorer_require_trace_symbol": "normalize_tag",
                "max_explorer_no_progress_streak": 5,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    packet = {
        "schema_version": 2,
        "task_id": "live-slug",
        "feature_id": "live-slug",
        "unit_id": "normalize-tag",
        "run_id": "normalize-a1",
        "attempt": 1,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": "Implement normalize_tag so all five focused tests pass without changing tests.",
        "risk": {
            "feature": "small",
            "unit": "small",
            "integration": "small",
            "reasons": ["Isolated pure function in a disposable fixture."],
        },
        "dependencies": [],
        "owned_contract_ids": ["tag-normalization"],
        "scope": {
            "read": ["src", "tests"],
            "readonly": ["tests/test_slug.py"],
            "modify": ["src/slug.py"],
            "create": ["src/tag_rules.py"],
            "forbidden": [],
        },
        "edit_targets": [
            {"path": "src/slug.py", "anchor": "def normalize_tag", "line_hint": 1}
        ],
        "required_behavior": [
            {
                "id": "tag-normalization",
                "text": "For nonempty strings, lowercase and join whitespace-separated words with one hyphen; reject blank strings with ValueError and non-strings with TypeError. Create src/tag_rules.py with normalize_words(value), and use it to collapse all whitespace into a list of words.",
                "risk_floor": "small",
            }
        ],
        "acceptance_criteria": [
            {"id": "focused-tests", "text": "All five tests pass."},
            {"id": "style", "text": "Ruff format and lint pass."},
        ],
        "acceptance_scenarios": [
            {"id": "normal", "text": "Trim and join two words."},
            {"id": "boundary", "text": "Collapse tabs, repeated spaces, and newlines."},
            {"id": "error", "text": "Reject blank and non-string inputs."},
        ],
        "implementation_guidance": [
            'SEARCH for normalize_tag before editing. Cover all five focused tests, including distinct blank-string ValueError and non-string TypeError branches, in the first implementation. Create src/tag_rules.py with a final newline and no trailing whitespace. Update src/slug.py to import normalize_words using exactly `from src.tag_rules import normalize_words`; the successful return expression should be exactly `return "-".join(normalize_words(value)).lower()`. Do not leave whitespace-only lines.'
        ],
        "validation_profile": "smoke-strict",
        "focused_tests": ["tests/test_slug.py"],
    }
    packet_path = root / ".agent" / "packet.json"
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    explorer_code, explorer = _run(
        root,
        "local-explore.py",
        [
            "--task",
            (
                "Locate normalize_tag and its test assertions in src/slug.py and tests/test_slug.py. Read them and return implementation/test source_refs, not execution predictions."
                if config["explorer_mode"] == "locate"
                else "Find normalize_tag and the exact focused tests in src/slug.py and tests/test_slug.py. A confirmed implementation gap is a successful investigation: cite the real files and lines, then FINISH_SUCCESS with the gap as a finding."
            ),
            "--task-id",
            "live-slug",
            "--config",
            str(local_config),
        ],
    )
    explorer_compat_code, explorer_compat = _run(
        root,
        "local-explore.py",
        [
            "--task",
            "Use regex SEARCH with mode regex for normalize_.*, then TRACE normalize_tag and finish with the observed definition/call evidence. Do not repeat either action.",
            "--task-id",
            "live-slug-compat",
            "--config",
            str(explorer_compat_config),
            "--full-report",
        ],
        report_name="explorer-compat.report.json",
    )
    unit = subprocess.run(
        [
            sys.executable,
            str(root / ".local-agents" / "local-unit.py"),
            "--packet",
            str(packet_path),
            "--config",
            str(local_config),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1000,
        check=False,
    )
    handoff = json.loads(unit.stdout) if unit.stdout.strip() else {}
    coder_report = root / ".agent" / "last-local-coder-report.json"
    coder = (
        json.loads(coder_report.read_text(encoding="utf-8"))
        if coder_report.is_file()
        else {}
    )
    coder_code = unit.returncode
    result = {
        "workspace": str(root),
        "explorer_exit": explorer_code,
        "explorer_mode": config["explorer_mode"],
        "explorer_status": explorer.get("status"),
        "explorer_compat_exit": explorer_compat_code,
        "explorer_compat_status": explorer_compat.get("status"),
        "explorer_compat_report": str(root / ".agent" / "explorer-compat.report.json"),
        "coder_exit": coder_code,
        "coder_status": coder.get("status"),
        "reviewer_decision": handoff.get("reviewer_decision"),
        "review_attempts": handoff.get("review_attempts", []),
        "handoff_stage": handoff.get("stage"),
        "handoff_reason": handoff.get("reason"),
    }
    if handoff.get("review_report"):
        result["review_report"] = handoff["review_report"]
    checks = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_slug.py", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    result["independent_pytest_exit"] = checks.returncode
    result["independent_pytest_tail"] = checks.stdout[-500:]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a disposable live LM Studio worker smoke"
    )
    parser.add_argument(
        "--config", type=Path, default=KIT / ".local-agents" / "config.json"
    )
    parser.add_argument("--existing-python", type=Path)
    parser.add_argument("--workspace-parent", type=Path)
    args = parser.parse_args()
    result = run(
        args.config,
        existing_python=args.existing_python,
        workspace_parent=args.workspace_parent,
    )
    print(json.dumps(result, indent=2))
    return (
        0
        if result.get("coder_status") == "ready_for_review"
        and result.get("reviewer_decision") == "pass_to_primary"
        and result["independent_pytest_exit"] == 0
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
