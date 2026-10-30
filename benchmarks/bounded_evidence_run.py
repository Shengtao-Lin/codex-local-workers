"""One enrolled live cell, gated by explicit approval and fresh Primary usage observation.

No approval is created here. No retry, replacement cell or automatic acceptance.
"""

import argparse
import os
import signal
import subprocess
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T

REGISTRATION = S.BATCH / "registration-v2-draft.json"


def authorize(approval_path, used, observed_at):
    if not approval_path.is_file():
        raise ValueError("New consolidated human live approval is required")
    approval = S.read(approval_path)
    if approval != {
        "registration_sha256": S.sha(REGISTRATION),
        "human_approved_live": True,
    }:
        raise ValueError("Approval does not bind this exact registration")
    if not 0 <= used < 15 or not 0 <= time.time() - observed_at <= 120:
        raise ValueError("Fresh actual weekly-used observation below 15% required")


def verify(row, registration):
    for name, digest in registration["pins"].items():
        if S.sha(name) != digest:
            raise ValueError("Frozen experiment dependency changed: " + name)
    root = Path(row["root"])
    if any(S.sha(root / p) != digest for p, digest in row["files"].items()):
        raise ValueError("Prepared cell changed or was already used")
    return root


def run_cell(cell, approval_path, used, observed_at):
    authorize(approval_path, used, observed_at)
    registration = S.read(REGISTRATION)
    cells = S.read(S.BATCH / "cells-v4.json")
    if cell not in registration["order"]:
        raise ValueError("Cell is not enrolled")
    records = S.BATCH / "live-results"
    index = registration["order"].index(cell)
    for previous in registration["order"][:index]:
        path = records / previous / "result.json"
        if not path.exists():
            raise ValueError(
                "Earlier cell incomplete; inspect its process/archive, do not restart"
            )
        if S.read(path)["stop_batch"]:
            raise ValueError("Earlier cell requires batch stop")
    directory = records / cell
    if (directory / "start.json").exists():
        raise ValueError("Cell already started; no replacement or silent restart")
    root = verify(cells[cell], registration)
    clock = records / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = S.read(clock)["epoch"] + 10800 - time.time()
    if remaining <= 0:
        raise ValueError("Batch time exhausted; remaining cells NOT_RUN")
    command = [
        str(S.PYTHON),
        "-B",
        str(S.KIT / "benchmarks/bounded_evidence_unit.py"),
        "--coder-runtime-dir",
        str(root / ".local-agents"),
        "--capture-policy-sha256",
        cells[cell]["capture_policy_sha256"],
        "--packet",
        str(root / ".agent/packet.json"),
        "--config",
        str(root / ".agent/config.json"),
        "--coder-report",
        str(root / ".agent/coder-report.json"),
        "--review-report",
        str(root / ".agent/reviewer-report.json"),
        "--summary",
        str(root / ".agent/unit-summary.json"),
    ]
    S.save(
        directory / "start.json",
        {
            "epoch": time.time(),
            "cell": cell,
            "weekly_used": used,
            "usage_observed_at": observed_at,
            "usage_source": "Primary attests fresh get_usage_limits; runner cannot query account itself",
            "argv": command,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    interrupted = False
    started = time.monotonic()
    with (
        (directory / "stdout.log").open("x", encoding="utf-8") as out,
        (directory / "stderr.log").open("x", encoding="utf-8") as err,
    ):
        child = subprocess.Popen(
            command,
            cwd=root,
            stdout=out,
            stderr=err,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=os.name != "nt",
        )
        S.save(
            directory / "process.json", {"pid": child.pid, "started_epoch": time.time()}
        )
        try:
            child.wait(timeout=min(2220, remaining))
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            interrupted = True
            # Only the process tree this invocation just created is in scope.
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                )
            else:
                os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
    summary_path = root / ".agent/unit-summary.json"
    summary = S.read(summary_path) if summary_path.exists() else {}
    report_path = root / ".agent/coder-report.json"
    coder = S.read(report_path) if report_path.exists() else {}
    packet = S.read(root / ".agent/packet.json")
    canonical = (
        root
        / ".agent/tasks"
        / packet["task_id"]
        / "runs"
        / packet["run_id"]
        / "handoff.json"
    )
    canonical_present = canonical.exists()
    if canonical_present:
        coder = S.read(canonical)
    # Independent checks never become a later Worker repair prompt.
    checks = []
    if not interrupted:
        commands = [
            [
                S.PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "tests",
                cells[cell]["private_tests"],
            ],
            [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
        ]
        for argv in commands:
            available = min(
                2220 - (time.monotonic() - started),
                S.read(clock)["epoch"] + 10800 - time.time(),
            )
            if available <= 0:
                interrupted = True
                break
            try:
                checks.append(T.run(argv, root, timeout=min(120, available)))
            except subprocess.TimeoutExpired:
                checks.append(
                    {
                        "argv": [str(x) for x in argv],
                        "exit_code": None,
                        "status": "TIMEOUT",
                    }
                )
                interrupted = True
                break
    protected_drift = [
        p
        for p, digest in cells[cell]["files"].items()
        if p != "src/product/code.py"
        and (not (root / p).is_file() or S.sha(root / p) != digest)
    ]
    infra = bool(coder.get("infra_failure")) or coder.get("status") in {
        "policy_violation",
        "interrupted",
    }
    result = {
        "cell": cell,
        "unit_seconds": round(time.monotonic() - started, 3),
        "exit": child.returncode,
        "interrupted": interrupted,
        "summary": summary,
        "independent_checks": checks,
        "final_source_sha256": S.sha(root / "src/product/code.py"),
        "protected_drift": protected_drift,
        "stop_batch": interrupted
        or infra
        or bool(protected_drift)
        or not summary
        or not canonical_present,
        "coder_status": coder.get("status"),
        "coder_ledger": coder.get("bounded_evidence"),
        "infra_failure": coder.get("infra_failure"),
        "independent_all_checks_passed": len(checks) == 4
        and all(c["exit_code"] == 0 for c in checks),
        "primary_decision": "PENDING_PRIMARY",
        "assisted": None,
        "primary_actions": {
            k: None
            for k in (
                "specific_fix_given",
                "new_boundary_added",
                "dependency_located",
                "code_written",
                "active_seconds",
                "cloud_tokens",
            )
        },
        "reviewer_false_pass": None,
        "reviewer_false_reject": None,
        "note": "Primary must inspect actual high-risk diff and contract before recording canonical review. No semantic Reviewer resampling.",
    }
    if (
        coder.get("status") == "blocked"
        and coder.get("blocked", {}).get("reason_code") != "proposal_blocked"
    ):
        result["stop_batch"] = True
    S.save(directory / "result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--usage-observed-at", type=float, required=True)
    args = parser.parse_args()
    result = run_cell(
        args.cell, args.approval, args.weekly_used, args.usage_observed_at
    )
    print(
        result["cell"],
        "pending Primary review; stop_batch=" + str(result["stop_batch"]),
    )
