"""One frozen Explorer-to-Coder handoff without revealing source paths in the question."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

import stability_e2e as STABILITY

QUESTION = (
    "A regression makes the newest and oldest selection policies return the "
    "wrong rows. Start with the failing tests in tests/test_selection_order.py, "
    "then locate the implementation without an implementation path hint. "
    "In findings or call_flow, cite the full discovered source path with line N "
    "and the full discovered test path with line N for a relevant assertion. "
    "Explain which branch controls ordering and state any uncertainty."
)


def handoff_ready(report: dict, case: STABILITY.Case, test_path: str) -> bool:
    """Primary's mechanical minimum before reviewing a bounded Coder packet."""
    files = {
        item.get("path")
        for item in report.get("relevant_files", [])
        if isinstance(item, dict)
    }
    return bool(
        report.get("status") == "success"
        and STABILITY.explorer_has_line_evidence(report, case, test_path)
        and case.target in files
        and test_path in report.get("relevant_tests", [])
        and not report.get("uncertainties")
    )


def locator_inputs_unchanged(root: Path, report: dict) -> bool:
    if report.get("explorer_mode") != "locate":
        return True
    refs = report.get("source_refs")
    if not isinstance(refs, list) or not refs:
        return False
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
            return False
        path = (root / ref["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != ref.get("source_hash"):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=STABILITY.KIT / ".local-agents/config.json"
    )
    parser.add_argument(
        "--explorer-mode", choices=("investigate", "locate"), default="investigate"
    )
    args = parser.parse_args()
    case = next(item for item in STABILITY.CASES if item.name == "selection-order")
    root = STABILITY.WORK / f"handoff-{uuid.uuid4().hex[:12]}"
    source_config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    source_config["explorer_mode"] = args.explorer_mode
    question = QUESTION
    if args.explorer_mode == "locate":
        question = (
            "Locate the implementation controlling newest/oldest record selection, "
            "starting with tests/test_selection_order.py; the source location is unknown. "
            "Return source_refs for the implementation's ordering branch and the related "
            "test assertions, with implementation/test kinds. Read before citing. "
            "Do not predict execution results; state genuine unresolved location questions."
        )
    config_path, draft_path = STABILITY.prepare(
        case, root, source_config, packet_name="packet-draft.json"
    )
    test_path = "tests/test_selection_order.py"
    runtime_config = json.loads(config_path.read_text(encoding="utf-8"))
    runtime_config["explorer_required_citation_paths"] = [test_path]
    STABILITY.write_json(config_path, runtime_config)
    explorer_path = root / ".agent/explorer-report.json"
    explorer = STABILITY.run_command(
        root,
        [
            sys.executable,
            str(root / ".local-agents/local-explore.py"),
            "--task",
            question,
            "--task-id",
            "stability-selection-order",
            "--config",
            str(config_path),
            "--report",
            str(explorer_path),
        ],
        600,
    )
    compact = (
        json.loads(explorer_path.read_text(encoding="utf-8"))
        if explorer_path.is_file()
        else {}
    )
    full = STABILITY.full_explorer_report(root, compact)
    ready = (
        explorer.returncode == 0
        and handoff_ready(full, case, test_path)
        and locator_inputs_unchanged(root, full)
    )
    result = {
        "workspace": str(root),
        "case": case.name,
        "question": question,
        "explorer_status": full.get("status"),
        "explorer_evidence_gate": ready,
        "explorer_report": str(explorer_path),
        "coder_dispatched": False,
    }
    if not ready:
        STABILITY.write_json(root / "handoff-result.json", result)
        print(json.dumps(result, ensure_ascii=False))
        return 1

    packet_path = root / ".agent/packet.json"
    STABILITY.write_json(
        packet_path, json.loads(draft_path.read_text(encoding="utf-8"))
    )
    unit = STABILITY.run_command(
        root,
        [
            sys.executable,
            str(root / ".local-agents/local-unit.py"),
            "--packet",
            str(packet_path),
            "--config",
            str(config_path),
        ],
        1200,
    )
    result["coder_dispatched"] = True
    coder_path = root / ".agent/last-local-coder-report.json"
    coder = (
        json.loads(coder_path.read_text(encoding="utf-8"))
        if coder_path.is_file()
        else {}
    )
    try:
        handoff = json.loads(unit.stdout)
    except ValueError:
        handoff = {}
    checks = {
        "pytest": [sys.executable, "-m", "pytest", test_path, "-q"],
        "ruff_format": [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "src",
            "tests",
        ],
        "ruff_check": [sys.executable, "-m", "ruff", "check", "src", "tests"],
    }
    result.update(
        {
            "unit_exit": unit.returncode,
            "coder_status": coder.get("status"),
            "reviewer_decision": handoff.get("reviewer_decision"),
            "independent_checks": {
                name: STABILITY.run_command(root, argv, 90).returncode == 0
                for name, argv in checks.items()
            },
        }
    )
    result["passed"] = bool(
        unit.returncode == 0
        and result["coder_status"] == "ready_for_review"
        and result["reviewer_decision"] == "pass_to_primary"
        and all(result["independent_checks"].values())
    )
    STABILITY.write_json(root / "handoff-result.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
