"""Disposable Coder compatibility probe that requires source search to locate a late symbol."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from stability_e2e import KIT, WORK, read_events, run_command, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=KIT / ".local-agents/config.json"
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--context-length", type=int, default=24576)
    args = parser.parse_args()
    root = WORK / f"coder-search-compat-{uuid.uuid4().hex[:12]}"
    root.mkdir(parents=True, exist_ok=False)

    sys.path.insert(0, str(KIT / "scripts"))
    from install_local_agents import inventory

    for relative in inventory(KIT):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((KIT / relative).read_bytes())
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / ".agent").mkdir()
    filler = "".join(
        f"# Stable unrelated declaration {number:03d}\n" for number in range(400)
    )
    (root / "src/late_rule.py").write_text(
        filler + "\n\ndef accept_code(value: str) -> bool:\n    return bool(value)\n",
        encoding="utf-8",
    )
    (root / "tests/test_late_rule.py").write_text(
        "from src.late_rule import accept_code\n\n\n"
        "def test_code_with_prefix_is_accepted():\n"
        '    assert accept_code("QA-123") is True\n\n\n'
        "def test_code_without_prefix_is_rejected():\n"
        '    assert accept_code("123") is False\n\n\n'
        "def test_empty_code_is_rejected():\n"
        '    assert accept_code("") is False\n',
        encoding="utf-8",
    )
    base_config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    context_lengths = dict(base_config.get("model_context_lengths", {}))
    context_lengths[args.model] = args.context_length
    config = {
        **base_config,
        "coder_model": args.model,
        "coder_context_length": args.context_length,
        "model_context_lengths": context_lengths,
        "python": sys.executable,
        "require_edit_targets": True,
        "validation_profiles": {
            "compat-strict": {
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
    config_path = root / ".local-agents/config.json"
    write_json(config_path, config)
    packet = {
        "schema_version": 2,
        "task_id": "coder-search-compat",
        "feature_id": "coder-search-compat",
        "unit_id": "late-prefix-rule",
        "run_id": "late-prefix-rule-a1",
        "attempt": 1,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": "Require a QA- prefix for nonempty accepted codes while preserving empty rejection.",
        "risk": {
            "feature": "small",
            "unit": "small",
            "integration": "small",
            "reasons": ["Disposable isolated pure-function compatibility fixture."],
        },
        "dependencies": [],
        "owned_contract_ids": ["prefix-rule"],
        "scope": {
            "read": ["src", "tests"],
            "readonly": ["tests/test_late_rule.py"],
            "modify": ["src/late_rule.py"],
            "create": [],
            "forbidden": [],
        },
        "edit_targets": [{"path": "src/late_rule.py", "anchor": "def accept_code"}],
        "required_behavior": [
            {
                "id": "prefix-rule",
                "text": "accept_code returns True only for nonempty strings beginning QA-; all other strings return False.",
                "risk_floor": "small",
            }
        ],
        "acceptance_criteria": [
            {"id": "focused-tests", "text": "All protected tests pass."},
            {"id": "static", "text": "Ruff format and lint pass."},
        ],
        "acceptance_scenarios": [
            {"id": "normal", "text": "QA-123 is accepted."},
            {"id": "boundary", "text": "123 and the empty string are rejected."},
        ],
        "implementation_guidance": [
            "The source file deliberately exceeds a normal READ_FILE window. SEARCH for the exact accept_code symbol, then read its current line range before editing; do not scan filler comments."
        ],
        "validation_profile": "compat-strict",
        "focused_tests": ["tests/test_late_rule.py"],
    }
    packet_path = root / ".agent/packet.json"
    write_json(packet_path, packet)
    baseline_format = run_command(
        root, [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"], 90
    )
    baseline_lint = run_command(
        root, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
    )
    if baseline_format.returncode != 0 or baseline_lint.returncode != 0:
        raise RuntimeError("compat fixture static baseline must pass")
    baseline = run_command(
        root, [sys.executable, "-m", "pytest", "tests/test_late_rule.py", "-q"], 90
    )
    if baseline.returncode == 0:
        raise RuntimeError("compat fixture baseline must fail")
    command = run_command(
        root,
        [
            sys.executable,
            str(root / ".local-agents/local-code.py"),
            "--packet",
            str(packet_path),
            "--config",
            str(config_path),
            "--report",
            str(root / ".agent/coder-report.json"),
        ],
        1200,
    )
    report_path = root / ".agent/coder-report.json"
    report = (
        json.loads(report_path.read_text(encoding="utf-8"))
        if report_path.is_file()
        else {}
    )
    events = read_events(
        root / ".agent/tasks/coder-search-compat/runs/late-prefix-rule-a1/events.jsonl"
    )
    actions = {
        event.get("facts", {}).get("action")
        for event in events
        if event.get("event") == "tool_action"
    }
    independent = {
        name: run_command(root, argv, 90)
        for name, argv in {
            "pytest": [sys.executable, "-m", "pytest", "tests/test_late_rule.py", "-q"],
            "format": [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "src",
                "tests",
            ],
            "lint": [sys.executable, "-m", "ruff", "check", "src", "tests"],
        }.items()
    }
    result = {
        "workspace": str(root),
        "model": args.model,
        "context_length": args.context_length,
        "coder_exit": command.returncode,
        "coder_status": report.get("status"),
        "failure_reason": report.get("failure_reason"),
        "observed_actions": sorted(
            action for action in actions if isinstance(action, str)
        ),
        "search_exercised": "SEARCH" in actions,
        "independent_checks": {
            name: check.returncode == 0 for name, check in independent.items()
        },
    }
    write_json(root / "compat-result.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return (
        0
        if result["search_exercised"] and all(result["independent_checks"].values())
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
