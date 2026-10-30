"""Freeze four exposed-draft diagnostics and launch the explicit unit CLI directly."""

import argparse
import json
import os
import signal
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_readiness as READY
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import consolidated_harness as H

BATCH = S.KIT / "benchmarks/work/harness-convergence/consolidated-harness-20261018-1"
ORIGINAL = S.BATCH
STARTS = S.KIT / "benchmarks/work/harness-convergence/behavior-unit-20261018-3"
ORDER = ["T1-1", "T2-1", "T2-2", "T1-2"]


def command(row):
    root = Path(row["root"])
    return [
        str(S.PYTHON),
        "-B",
        str(S.KIT / "benchmarks/consolidated_entry.py"),
        "--mode",
        "unit",
        "--runtime-dir",
        str(root / ".local-agents"),
        "--packet",
        str(root / ".agent/packet.json"),
        "--config",
        str(root / ".agent/config.json"),
        "--report",
        str(root / ".agent/report.json"),
        "--review-report",
        str(root / ".agent/reviewer-report.json"),
        "--summary",
        str(root / ".agent/unit-summary.json"),
    ]


def prepare(used):
    controls = list(ET.parse(BATCH / "controls-v4.xml").getroot().iter("testsuite"))
    if not controls or any(
        int(c.get("errors", 0)) or int(c.get("failures", 0)) for c in controls
    ):
        raise ValueError("Offline controls must pass first")
    source_cells = S.read(STARTS / "cells.json")
    names = (
        subprocess.check_output(
            ["git", "ls-files", "-m", "-o", "--exclude-standard", "-z"], cwd=S.KIT
        )
        .decode()
        .split("\0")
    )
    S.save(
        BATCH / "baseline.json",
        {
            "weekly_used": used,
            "stop_used": 20,
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
            .decode()
            .strip(),
            "files": {
                p: S.sha(S.KIT / p) for p in names if p and (S.KIT / p).is_file()
            },
            "timing": "Preparation checkpoint after creating new experimental source; existing files unchanged during this stage before this point",
        },
    )
    pins = dict(S.read(ORIGINAL / "registration-v2-draft.json")["pins"])
    for name in (
        "benchmarks/harness_protocol.py",
        "benchmarks/consolidated_harness.py",
        "benchmarks/consolidated_entry.py",
        "benchmarks/consolidated_trial.py",
        "tests/test_consolidated_harness.py",
        "docs/consolidated-harness-stage.md",
    ):
        pins[str(S.KIT / name)] = S.sha(S.KIT / name)
    assert all(S.sha(p) == sha for p, sha in pins.items())
    rows = {}
    for cell in ORDER:
        topic = cell.split("-")[0]
        root = READY.clone(source_cells[topic + "-A1"], BATCH / "cells" / cell)
        identity = {
            "task_id": "consolidated-" + topic,
            "unit_id": "consolidated-" + topic,
            "run_id": "consolidated-20261018-" + cell,
        }
        packet_path, policy_path = root / ".agent/packet.json", root / F.POLICY_PATH
        packet, policy = S.read(packet_path), S.read(policy_path)
        packet.update(identity)
        packet["feature_id"] = "consolidated-recovery-" + topic
        packet["primary_plan_sha256"] = S.sha(
            S.KIT / "docs/consolidated-harness-stage.md"
        )
        policy["identity"] = identity
        packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        config = {
            k: v
            for k, v in S.read(root / ".agent/config.json").items()
            if not k.startswith("experimental_")
        }
        config.update(
            experimental_consolidated_harness=True,
            experimental_capture_policy_sha256=S.sha(policy_path),
            experimental_approved_imports=[
                ["collections.abc", "Iterator", None],
                ["collections.abc", "Sequence", None],
                ["typing", "cast", None],
            ]
            if topic == "T2"
            else [],
            coordinator_enabled=False,
            autoformat_on_ruff_failure=False,
        )
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        row = {
            "root": str(root),
            "topic": topic,
            "private_tests": source_cells[topic + "-A1"]["private_tests"],
            "identity": identity,
        }
        preflight = command(row)
        preflight[preflight.index("unit")] = "preflight"
        # No archive or model lease; this output is outside the future run archive.
        preflight[preflight.index("--report") + 1] = str(root / ".agent/preflight.json")
        checked = T.run(preflight, root)
        S.save(BATCH / "preflight" / (cell + ".json"), checked)
        assert checked["exit_code"] == 0, checked
        row["files"] = {
            p.relative_to(root).as_posix(): S.sha(p)
            for p in root.rglob("*")
            if p.is_file()
        }
        rows[cell] = row
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 4,
            "pins": pins,
            "cells_sha256": S.sha(BATCH / "cells.json"),
            "controls_sha256": S.sha(BATCH / "controls-v4.xml"),
            "budget": H.BUDGET,
            "mode": "exposed repair diagnostic, not holdout, not concurrent A/B",
            "gate": "4/4 final independent complete-chain accept; diagnostic progression only, notR4/production",
            "historical_comparison": "Older same-task results retained, not pooled or a controlled estimate of benefit; preparation budget changed1to12",
            "continue_rule": "ordinary failures finish fixed order; stop on infrastructure/scope/protected drift/time/20%used; never replace a failed cell",
            "unit_seconds": 2220,
            "batch_seconds": 10800,
            "weekly_stop": 20,
            "authority": "User approved experiment Harness consolidation and autonomous iteration under20%; production runtime/defaults unchanged",
            "model": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "single_resident": True,
            },
        },
    )


def run(cell, used, observed_at):
    if not 0 <= used < 20 or not 0 <= time.time() - observed_at <= 120:
        raise ValueError("Fresh actual weekly-used below20% required")
    registration = S.read(BATCH / "registration.json")
    if not all(S.sha(p) == sha for p, sha in registration["pins"].items()):
        raise ValueError("Candidate drift")
    if (
        S.sha(BATCH / "cells.json") != registration["cells_sha256"]
        or S.sha(BATCH / "controls-v4.xml") != registration["controls_sha256"]
    ):
        raise ValueError("Input/control drift")
    if cell not in ORDER:
        raise ValueError("Unregistered cell")
    for earlier in ORDER[: ORDER.index(cell)]:
        previous = S.read(BATCH / "live-results" / earlier / "result.json")
        if previous["stop_batch"]:
            raise ValueError("Earlier cell stopped batch")
    row = S.read(BATCH / "cells.json")[cell]
    root = Path(row["root"])
    if any(S.sha(root / p) != sha for p, sha in row["files"].items()):
        raise ValueError("Used or altered cell")
    record = BATCH / "live-results" / cell
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = S.read(clock)["epoch"] + 10800 - time.time()
    if remaining <= 0:
        raise ValueError("Batch time exhausted")
    argv = command(row)
    S.save(
        record / "start.json",
        {
            "epoch": time.time(),
            "weekly_used": used,
            "usage_observed_at": observed_at,
            "argv": argv,
        },
    )
    started = time.monotonic()
    interrupted = False
    with (
        (record / "stdout.log").open("x", encoding="utf-8") as out,
        (record / "stderr.log").open("x", encoding="utf-8") as err,
    ):
        child = subprocess.Popen(
            argv,
            cwd=root,
            stdout=out,
            stderr=err,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=os.name != "nt",
        )
        S.save(record / "process.json", {"pid": child.pid})
        try:
            child.wait(timeout=min(2220, remaining))
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            interrupted = True
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                )
            else:
                os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
    execution = {
        "argv": argv,
        "exit_code": child.returncode,
        "interrupted": interrupted,
    }
    S.save(record / "execution.json", execution)
    if interrupted:
        S.save(
            record / "result.json",
            {"cell": cell, "stop_batch": True, "status": "INTERRUPTED"},
        )
        return
    summary = (
        S.read(root / ".agent/unit-summary.json")
        if (root / ".agent/unit-summary.json").exists()
        else {}
    )
    report = (
        S.read(root / ".agent/report.json")
        if (root / ".agent/report.json").exists()
        else {}
    )
    checks = []
    for cmd in (
        [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", row["private_tests"]],
        [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
        [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
        [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
    ):
        available = min(
            started + 2220 - time.monotonic(),
            S.read(clock)["epoch"] + 10800 - time.time(),
        )
        if available <= 0:
            interrupted = True
            break
        try:
            checks.append(T.run(cmd, root, timeout=min(120, available)))
        except subprocess.TimeoutExpired:
            interrupted = True
            break
    drift = [
        p
        for p, sha in row["files"].items()
        if p != "src/product/code.py" and S.sha(root / p) != sha
    ]
    S.save(
        record / "result.json",
        {
            "cell": cell,
            "seconds": round(time.monotonic() - started, 3),
            "summary": summary,
            "coder_status": report.get("status"),
            "ledger": report.get("consolidated_harness"),
            "independent_checks": checks,
            "independent_all_checks_passed": len(checks) == 4
            and all(c["exit_code"] == 0 for c in checks),
            "protected_drift": drift,
            "final_source_sha256": S.sha(root / "src/product/code.py"),
            "Primary_decision": "PENDING_PRIMARY",
            "stop_batch": interrupted
            or bool(drift)
            or not summary
            or bool(report.get("infra_failure"))
            or report.get("status") in {"interrupted", "policy_violation"},
            "assisted": False,
            "Primary_takeover": False,
        },
    )
    print(cell, "completed; Primary review required")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("--cell")
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--usage-observed-at", type=float)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
        print("Four inputs frozen; no live yet")
    else:
        run(args.cell, args.weekly_used, args.usage_observed_at)
