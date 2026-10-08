"""Fresh review of unchanged successful Coder archive under ownership guidance."""

import json
import subprocess
import sys
from pathlib import Path

from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "reviewer-unit-ownership-probe-1"
SNAPSHOT = WORK / "coordinator-unit-ownership-baseline-1"


def main():
    BASE.mkdir(exist_ok=False)
    manifest = read(WORK / "coordinator-limited-retention-1/manifest.json")
    root = Path(next(c for c in manifest["cells"] if c["id"] == "control-r1")["root"])
    packet = read(root / ".agent/collect-unit-bound.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    request = read(archive / "auto-review-request.json")
    request["review_id"] = "unit-ownership-probe-1"
    request_path = root / ".agent/unit-ownership-review-request.json"
    write(request_path, request)
    write(
        BASE / "registration.json",
        {
            "snapshot": str(SNAPSHOT),
            "root": str(root),
            "original_reviewer": read(root / ".agent/collect-unit-reviewer.json")[
                "decision"
            ],
            "coder_archive_sha256": digest(archive / "handoff.json"),
            "request_sha256": digest(request_path),
            "changed_axis": "Reviewer prompt: distinguish explicitly pending ownership from current-unit regression; same actual Coder source/tests/contract/validation",
            "actual_diff_sha256": digest(archive / "cumulative.diff"),
            "primary_acceptance": False,
        },
    )
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SNAPSHOT / ".local-agents/local-review.py"),
            "--request",
            str(request_path),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/unit-ownership-reviewer.json"),
        ],
        cwd=root,
        check=False,
    )
    if (
        digest(archive / "handoff.json")
        != read(BASE / "registration.json")["coder_archive_sha256"]
    ):
        raise ValueError("Coder archive changed")
    report = read(root / ".agent/unit-ownership-reviewer.json")
    write(
        BASE / "result-1.json",
        {
            "exit": process.returncode,
            "decision": report["decision"],
            "findings": report["findings"],
            "unverified_claims": report.get("unverified_claims"),
            "runtime_facts": report["runtime_facts"],
            "primary_accepted": False,
            "classification": "One targeted diagnostic, not fresh full-chain qualification",
        },
    )
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "findings": report["findings"],
                "unverified_claims": report.get("unverified_claims"),
            }
        )
    )


if __name__ == "__main__":
    main()
