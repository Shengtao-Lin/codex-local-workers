"""Opt-in normal-task repeat preparation and bounded explicit entry execution."""

import argparse
import json
import os
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import consolidated_harness as H

BATCH = S.KIT / "benchmarks/work/harness-convergence/normal-task-repeat-20261019-1"
OLD = S.KIT / "benchmarks/work/harness-convergence/unified-transfer-20261018-1"
PARENT = S.KIT / "benchmarks/work/harness-convergence/consolidated-harness-20261018-1"
ORDER = ["request_keys-1", "single_content-1", "single_content-2", "request_keys-2"]


def reviewer_failed(summary, report):
    if summary.get("reviewer_started") is not True:
        return False
    return (
        not report
        or report.get("decision") == "failed"
        or bool(report.get("infra_failure"))
    )


def checkpoint():
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
            "files": {
                p: S.sha(S.KIT / p) for p in names if p and (S.KIT / p).is_file()
            },
            "tracked_diff_sha256": __import__("hashlib")
            .sha256(subprocess.check_output(["git", "diff", "--binary"], cwd=S.KIT))
            .hexdigest(),
            "authorization": "User approved autonomous narrow integration and conditional four-cell trial under20%",
        },
    )
    for name in (
        "consolidated_harness.py",
        "consolidated_entry.py",
        "preserved_import_guard.py",
    ):
        destination = BATCH / "candidate-preimages" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write((S.KIT / "benchmarks" / name).read_bytes())


def command(root, mode="unit", replay=None):
    args = [
        str(S.PYTHON),
        "-B",
        str(S.KIT / "benchmarks/consolidated_entry.py"),
        "--preserve-existing-imports",
        "--mode",
        mode,
        "--runtime-dir",
        str(root / ".local-agents"),
        "--packet",
        str(root / ".agent/packet.json"),
        "--config",
        str(root / ".agent/config.json"),
        "--report",
        str(root / f".agent/{mode}-report.json"),
    ]
    if mode == "unit":
        args += [
            "--review-report",
            str(root / ".agent/reviewer-report.json"),
            "--summary",
            str(root / ".agent/unit-summary.json"),
        ]
    if replay:
        args += ["--replay", str(replay)]
    return args


def prepare_cell(topic, destination, label):
    """Reconstruct registered pre-run bytes, never copy an accepted final patch."""
    row = S.read(OLD / "cells.json")[topic + "-candidate-1"]
    historical = Path(row["root"])
    packet = S.read(historical / ".agent/packet.json")
    target = packet["scope"]["modify"][0]
    root = destination / "isolated"
    root.mkdir(parents=True, exist_ok=False)
    for path, digest in row["files"].items():
        if path.startswith((".local-agents/", ".baseline-agents/")):
            continue
        source = historical / path
        if S.sha(source) != digest:
            if path != target:
                raise ValueError("Historical non-source drift: " + path)
            source = OLD / "fixtures" / topic / path
        if S.sha(source) != digest:
            raise ValueError("Registered start mismatch: " + path)
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    parent = S.read(PARENT / "cells.json")["T1-1"]
    for path, digest in parent["files"].items():
        if path.startswith(".local-agents/"):
            source = Path(parent["root"]) / path
            if S.sha(source) != digest:
                raise ValueError("Frozen runtime drift")
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
    old_config = S.read(root / ".agent/config.json")
    config = S.read(Path(parent["root"]) / ".agent/config.json")
    config["coder_single_function"] = old_config["coder_single_function"]
    config["validation_profiles"] = old_config["validation_profiles"]
    config["experimental_approved_imports"] = []
    identity = {k: "normal-" + label for k in ("task_id", "unit_id", "run_id")}
    packet.update(identity)
    packet["feature_id"] = "normal-repeat-" + topic
    packet["primary_plan_sha256"] = S.sha(
        S.KIT / "docs/normal-task-candidate-readiness.md"
    )
    packet["limits"].update(max_model_turns=12, hard_max_model_turns=12)
    policy = S.read(root / F.POLICY_PATH)
    policy["identity"] = identity
    for path, value in ((".agent/packet.json", packet), (F.POLICY_PATH, policy)):
        (root / path).write_text(json.dumps(value, indent=2), encoding="utf-8")
    config["experimental_capture_policy_sha256"] = S.sha(root / F.POLICY_PATH)
    (root / ".agent/config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
    return {
        "root": str(root),
        "topic": topic,
        "identity": identity,
        "target": target,
        "private_tests": str(OLD / "private" / topic / f"test_private_{topic}.py"),
        "files": {
            p.relative_to(root).as_posix(): S.sha(p)
            for p in root.rglob("*")
            if p.is_file()
        },
    }


def prepare(used):
    if not 0 <= used < 20:
        raise ValueError("Weekly stop reached")
    cells = {
        cell: prepare_cell(cell.rsplit("-", 1)[0], BATCH / "cells" / cell, cell)
        for cell in ORDER
    }
    S.save(BATCH / "cells.json", cells)
    preflights()
    print("Four starts prepared; not frozen and no live yet")


def preflights():
    cells = S.read(BATCH / "cells.json")
    for cell, row in cells.items():
        result = T.run(
            command(Path(row["root"]), "preflight"), Path(row["root"]), timeout=120
        )
        S.save(BATCH / "preflight" / (cell + ".json"), result)
        if result["exit_code"]:
            raise ValueError(result)
    print("Four no-model preflights passed")


def freeze(used):
    cases = list(ET.parse(BATCH / "controls-v2.xml").iter("testcase"))
    if len(cases) != 36 or any(
        c.find(tag) is not None
        for c in cases
        for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("All 36 entry/default/guard controls required")
    pins = dict(S.read(PARENT / "registration.json")["pins"])
    lineage = {}
    for name in ("consolidated_harness.py", "consolidated_entry.py"):
        path = str(S.KIT / "benchmarks" / name)
        archived = BATCH / "candidate-preimages" / name
        if S.sha(archived) != pins[path]:
            raise ValueError("Frozen ancestor source not preserved exactly")
        lineage[path] = {
            "old_sha256": pins[path],
            "preserved_at": str(archived),
            "new_sha256": S.sha(path),
        }
        pins[str(archived)] = pins[path]
        pins[path] = S.sha(path)
    for name in (
        "benchmarks/preserved_import_guard.py",
        "benchmarks/normal_task_trial.py",
        "tests/test_normal_task_entry.py",
        "tests/test_preserved_import_guard.py",
        "docs/normal-task-candidate-readiness.md",
    ):
        pins[str(S.KIT / name)] = S.sha(S.KIT / name)
    for path in [BATCH / "cells.json", BATCH / "controls-v2.xml"]:
        pins[str(path)] = S.sha(path)
    for topic in ("request_keys", "single_content"):
        for base in (OLD / "fixtures" / topic, OLD / "private" / topic):
            for path in base.rglob("*"):
                if (
                    path.is_file()
                    and "__pycache__" not in path.parts
                    and ".pytest_cache" not in path.parts
                ):
                    pins[str(path)] = S.sha(path)
    if any(S.sha(p) != digest for p, digest in pins.items()):
        raise ValueError("Lineage/dependency drift")
    S.save(
        BATCH / "registration.json",
        {
            "authorization": "User approved autonomous narrow integration and conditional four-cell trial, weekly20% stop",
            "feature_id": "preserved-import-normal-repeat",
            "feature_risk": "high",
            "integration_risk": "high",
            "units": {
                topic: {
                    "risk": "high",
                    "owned_contract_ids": [topic],
                    "dependencies": [],
                    "rationale": "Public identity/parser compatibility; copied isolation does not lower risk",
                }
                for topic in ("request_keys", "single_content")
            },
            "order": ORDER,
            "registered": 4,
            "pins": pins,
            "lineage": lineage,
            "candidate": "Explicit preserve-existing-imports guard on consolidated controller; previous guard remains default",
            "budget": H.BUDGET,
            "reviewer_budget": {
                "requests": 16,
                "errors": 4,
                "seconds": 600,
                "output_tokens": 4096,
            },
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "context": 24576,
                "quantization": "Q4_K_M",
                "single_residency": True,
            },
            "gate": "4/4 fresh Reviewer + independent Primary complete-chain accept; each task2/2; no assisted credit, no safety/protected drift",
            "continue_rule": "Ordinary failure HOLD but complete fixed diagnostic order; infrastructure/safety/protected drift/20%used/time stops. No replacements or reruns.",
            "weekly_used_start": used,
            "weekly_stop": 20,
            "unit_seconds": 2220,
            "batch_seconds": 10800,
            "scope": "Exposed exact-task repeats only; not holdout, no controlled causal comparison, no R4/R5/product promotion",
            "Primary": "No implementation/algorithm hints; independent full diff review required; costs unknown unless measured",
        },
    )
    print("Four cells frozen; candidate and full checks cannot change during batch")


def run(
    cell,
    used,
    observed,
    *,
    batch=BATCH,
    order=ORDER,
    build_command=command,
    usage_limit=20,
    batch_seconds=10800,
):
    if not 0 <= used < usage_limit or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh account usage below registered stop required")
    registration = S.read(batch / "registration.json")
    if (
        usage_limit != registration["weekly_stop"]
        or batch_seconds != registration["batch_seconds"]
    ):
        raise ValueError("Runner limits differ from registration")
    if any(S.sha(p) != digest for p, digest in registration["pins"].items()):
        raise ValueError("Frozen candidate/input drift")
    for earlier in order[: order.index(cell)]:
        if S.read(batch / "live-results" / earlier / "result.json")["stop_batch"]:
            raise ValueError("Previous cell stopped batch")
    row = S.read(batch / "cells.json")[cell]
    root = Path(row["root"])
    if any(S.sha(root / p) != digest for p, digest in row["files"].items()):
        raise ValueError("Used/changed input")
    clock = batch / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = batch_seconds - (time.time() - S.read(clock)["epoch"])
    if remaining <= 0:
        raise ValueError("Batch deadline reached")
    record = batch / "live-results" / cell
    argv = build_command(root)
    S.save(
        record / "start.json",
        {
            "weekly_used": used,
            "usage_observed_at": observed,
            "argv": argv,
            "epoch": time.time(),
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
        )
        S.save(record / "process.json", {"pid": child.pid})
        try:
            child.wait(timeout=min(2220, remaining))
        except subprocess.TimeoutExpired:
            interrupted = True
            subprocess.run(
                ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
            child.wait(timeout=30)
    checks = []
    if not interrupted:
        for cmd in (
            [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", row["private_tests"]],
            [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
        ):
            available = min(
                started + 2220 - time.monotonic(),
                S.read(clock)["epoch"] + batch_seconds - time.time(),
            )
            if available <= 0:
                interrupted = True
                break
            try:
                checks.append(T.run(cmd, root, timeout=min(120, available)))
            except subprocess.TimeoutExpired:
                interrupted = True
                break
    report = (
        S.read(root / ".agent/unit-report.json")
        if (root / ".agent/unit-report.json").exists()
        else {}
    )
    summary = (
        S.read(root / ".agent/unit-summary.json")
        if (root / ".agent/unit-summary.json").exists()
        else {}
    )
    reviewer_report = (
        S.read(root / ".agent/reviewer-report.json")
        if (root / ".agent/reviewer-report.json").exists()
        else {}
    )
    drift = [
        p
        for p, digest in row["files"].items()
        if p != row["target"] and S.sha(root / p) != digest
    ]
    S.save(
        record / "result.json",
        {
            "cell": cell,
            "seconds": time.monotonic() - started,
            "exit_code": child.returncode,
            "interrupted": interrupted,
            "summary": summary,
            "coder_status": report.get("status"),
            "ledger": report.get("consolidated_harness"),
            "independent_checks": checks,
            "all_independent_pass": len(checks) == 4
            and all(c["exit_code"] == 0 for c in checks),
            "protected_drift": drift,
            "final_source_sha256": S.sha(root / row["target"]),
            "stop_batch": interrupted
            or bool(drift)
            or not summary
            or reviewer_failed(summary, reviewer_report)
            or bool(report.get("infra_failure"))
            or report.get("status") in {"interrupted", "policy_violation"},
            "Primary_decision": "PENDING",
            "assisted": False,
        },
    )
    print(cell, "finished; independent Primary review required")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=["checkpoint", "prepare", "preflights", "freeze", "run"]
    )
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int)
    parser.add_argument("--observed-at", type=float)
    args = parser.parse_args()
    if args.mode == "checkpoint":
        checkpoint()
    elif args.mode == "prepare":
        prepare(args.weekly_used)
    elif args.mode == "freeze":
        freeze(args.weekly_used)
    elif args.mode == "preflights":
        preflights()
    else:
        run(args.cell, args.weekly_used, args.observed_at)
