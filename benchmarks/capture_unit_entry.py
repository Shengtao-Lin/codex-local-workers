"""One bounded Coder run then automatic qualified Reviewer, no model relaying."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import capture_fixture_support as F


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--coder-runtime-dir", required=True)
    parser.add_argument("--capture-policy-sha256", required=True)
    for field in ("packet", "config", "coder-report", "review-report", "summary"):
        parser.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    common = [
        "--capture-policy",
        F.POLICY_PATH,
        "--capture-policy-sha256",
        args.capture_policy_sha256,
    ]
    coder = subprocess.run(
        [
            sys.executable,
            "-B",
            str(F.KIT / "benchmarks/capture_coder_entry.py"),
            "--runtime-dir",
            args.coder_runtime_dir,
            *common,
            "--packet",
            str(args.packet),
            "--config",
            str(args.config),
            "--report",
            str(args.coder_report),
        ],
        cwd=root,
        check=False,
    )
    if not args.coder_report.is_file():
        raise ValueError("Coder did not produce its report")
    report = json.loads(args.coder_report.read_text(encoding="utf-8"))
    summary = {
        "coder_exit": coder.returncode,
        "coder_status": report.get("status"),
        "reviewer_started": False,
        "automatic_coder_rework": False,
    }
    if coder.returncode == 0 and report.get("status") in {
        "ready_for_review",
        "validation_passed_pending_review",
    }:
        gate = F.load(root / ".local-agents/local-unit.py", "uniform_capture_unit_gate")
        config = json.loads(args.config.read_text(encoding="utf-8"))
        identity = gate.verify_handoff(root, report, config=config)
        request = {
            "schema_version": 1,
            **identity,
            "review_id": "auto-" + identity["run_id"],
        }
        if report.get("execution_protocol"):
            request["execution_protocol"] = report["execution_protocol"]
        run_root = (
            root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
        )
        request_path = run_root / "capture-auto-review-request.json"
        with request_path.open("x", encoding="utf-8") as stream:
            json.dump(request, stream, indent=2)
        review_config = {
            **config,
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
        }
        review_config_path = run_root / "capture-review-config.json"
        with review_config_path.open("x", encoding="utf-8") as stream:
            json.dump(review_config, stream, indent=2)
        summary["reviewer_started"] = True
        reviewer = subprocess.run(
            [
                sys.executable,
                "-B",
                str(F.KIT / "benchmarks/reviewer_capture_entry.py"),
                "--runtime-dir",
                str(root / ".local-agents"),
                *common,
                "--request",
                str(request_path),
                "--config",
                str(review_config_path),
                "--report",
                str(args.review_report),
            ],
            cwd=root,
            check=False,
        )
        summary["reviewer_exit"] = reviewer.returncode
        if args.review_report.exists():
            summary["reviewer_decision"] = json.loads(
                args.review_report.read_text(encoding="utf-8")
            ).get("decision")
    with args.summary.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
    return 0 if summary.get("reviewer_decision") == "pass_to_primary" else 2


if __name__ == "__main__":
    raise SystemExit(main())
