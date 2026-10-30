"""Frozen R3 offline preflight and single-cell execution; no automatic retries."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import harness_r3_prepare as P

B, BATCH = P.B, P.BATCH / "preparation-v2"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_files(root, files, *, except_paths=()):
    drift = [
        name
        for name, digest in files.items()
        if name not in except_paths
        and (not (root / name).is_file() or B.sha(root / name) != digest)
    ]
    if drift:
        raise ValueError("Frozen paths changed: " + str(drift))


def preflight():
    cases = B.read(BATCH / "prepared-cases.json")
    rows = {}
    for name, files in cases.items():
        root = BATCH / "cases" / name / "isolated"
        assert_files(root, files)
        worker = load(root / ".local-agents/worker-runtime.py", "r3_preflight_" + name)
        packet, config = (
            B.read(root / ".agent/packet.json"),
            B.read(root / ".agent/config.json"),
        )
        client = type(
            "NoModel",
            (),
            {
                "timeout": 180,
                "structured_output": config.get("coder_structured_output", True),
                "native_tools": None,
                "typed_action_arguments": config.get(
                    "coder_typed_action_arguments", False
                ),
            },
        )()
        cls = worker.WorkerRuntime
        if "-candidate-" in name:
            host = load(
                root / ".local-agents/host-proposal.py", "r3_host_preflight_" + name
            )
            cls = host.make_runtime_class(worker)
        runtime = cls(root, packet, config, client)
        rows[name] = runtime.preflight()
        assert runtime.max_turns == runtime.hard_max_turns == 6
        runtime.close()
        assert_files(root, files)
    # Paired inputs differ only by run identity and trusted mode switches.
    for repeat in range(1, 4):
        for task in ("repair", "presence"):
            left = cases[f"{task}-baseline-{repeat}"]
            right = cases[f"{task}-candidate-{repeat}"]
            for path in left:
                if path.startswith(("src/", "tests/")) or path == "pyproject.toml":
                    assert left[path] == right[path], (task, path)
            a = B.read(
                BATCH / f"cases/{task}-baseline-{repeat}/isolated/.agent/packet.json"
            )
            b = B.read(
                BATCH / f"cases/{task}-candidate-{repeat}/isolated/.agent/packet.json"
            )
            a.pop("run_id")
            b.pop("run_id")
            assert a == b
    B.save(
        BATCH / "entry-preflight.json",
        {"no_model_calls": True, "cases": rows, "paired_inputs_equal": True},
    )
    print("12 installed entries preflight passed without model calls", flush=True)


def freeze():
    for name in ("controls-5.xml", "regression-final-2.xml", "wire-control.xml"):
        tree = ET.parse(P.BATCH / name)
        assert tree.findall(".//testcase") and not any(
            tree.findall(".//" + kind) for kind in ("failure", "error", "skipped")
        ), name
    assert B.read(BATCH / "entry-preflight.json")["paired_inputs_equal"]
    assert len(B.read(P.BATCH / "holdouts-freeze.json")["cases"]) == 3
    for name, row in B.read(P.BATCH / "holdouts-freeze.json")["cases"].items():
        assert_files(P.BATCH / "holdouts-v2" / name, row["files"])
    assert B.read(P.BATCH / "preservation-prelive.json")["passed"] is True
    assert B.read(BATCH / "installation.json")["default_enabled"] is False
    paths = [
        "benchmarks/harness_r3_run.py",
        "benchmarks/harness_r3_prepare.py",
        "benchmarks/harness_r3_budget_entry.py",
        "benchmarks/harness_r3_baseline_unit.py",
        "benchmarks/r3_capture/sitecustomize.py",
    ]
    paths += [
        p.relative_to(B.KIT).as_posix() for p in (B.KIT / ".local-agents").glob("*.py")
    ]
    B.save(
        BATCH / "live-freeze-approved.json",
        {
            "candidate_and_driver": {p: B.sha(B.KIT / p) for p in paths},
            "prepared_cases": B.sha(BATCH / "prepared-cases.json"),
            "registration": B.sha(BATCH / "registration.json"),
            "holdouts": B.sha(P.BATCH / "holdouts-freeze.json"),
            "wire_observer": "byte-preserving localhost POST capture, same for both arms",
            "no_live_changes": True,
        },
    )
    print("R3 live freeze sealed", flush=True)


def run(name, used):
    if not 0 <= used < 30:
        raise ValueError("Actual fresh usage below 30 required")
    registration = B.read(BATCH / "registration.json")
    frozen = B.read(BATCH / "live-freeze-approved.json")
    assert_files(B.KIT, frozen["candidate_and_driver"])
    assert B.sha(BATCH / "prepared-cases.json") == frozen["prepared_cases"]
    assert B.sha(BATCH / "registration.json") == frozen["registration"]
    assert B.sha(P.BATCH / "holdouts-freeze.json") == frozen["holdouts"]
    for previous in registration["order"]:
        if previous == name:
            break
        result = B.read(BATCH / "cases" / previous / "result.json")
        if "-candidate-" in previous and not result["eligible_for_primary"]:
            raise ValueError(
                "Candidate gate already unreachable; remaining cells must stay NOT_RUN"
            )
    else:
        raise ValueError("Unregistered cell")
    case = BATCH / "cases" / name
    root = case / "isolated"
    inputs = B.read(BATCH / "prepared-cases.json")[name]
    assert_files(root, inputs)
    B.save(
        case / "started.json",
        {"case": name, "weekly_used": used, "at": time.time(), "no_retry": True},
    )
    packet = B.read(root / ".agent/packet.json")
    entry = "r3-baseline-unit.py" if "-baseline-" in name else "local-unit.py"
    started = time.monotonic()
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(B.KIT / "benchmarks/r3_capture"),
        "R3_WIRE_DIR": str(case / "wire"),
    }
    argv = [
        sys.executable,
        "-B",
        str(root / ".local-agents" / entry),
        "--packet",
        str(root / ".agent/packet.json"),
        "--config",
        str(root / ".agent/config.json"),
        "--coder-report",
        str(case / "coder.json"),
        "--review-report",
        str(case / "reviewer.json"),
    ]
    result = subprocess.run(
        argv,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    B.save(
        case / "entry-result.json",
        {
            "argv": argv,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "seconds": time.monotonic() - started,
        },
    )
    coder = B.read(case / "coder.json") if (case / "coder.json").exists() else {}
    reviewer = (
        B.read(case / "reviewer.json") if (case / "reviewer.json").exists() else {}
    )
    run_root = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    canonical = (
        B.read(run_root / "handoff.json")
        if (run_root / "handoff.json").exists()
        else coder
    )
    checks = []
    checks_dir = case / "independent-checks"
    checks_dir.mkdir()
    commands = [
        [
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            *packet["focused_tests"],
            "--junitxml=" + str(checks_dir / "pytest.xml"),
        ],
        ["-m", "ruff", "format", "--check", "src", "tests"],
        ["-m", "ruff", "check", "src", "tests"],
        ["-m", "pyright", "--pythonpath", str(P.PYTHON)],
    ]
    for args in commands:
        checks.append(B.command([str(P.PYTHON), "-B", *args], cwd=root))
    B.save(checks_dir / "results.json", checks)
    protected_drift = [
        p
        for p, h in inputs.items()
        if p not in packet["scope"]["modify"] and B.sha(root / p) != h
    ]
    eligibility = (
        result.returncode == 0
        and canonical.get("status")
        in {"ready_for_review", "validation_passed_pending_review"}
        and reviewer.get("decision") == "pass_to_primary"
        and not protected_drift
        and all(c["exit_code"] == 0 for c in checks)
    )
    row = {
        "case": name,
        "coder_status": canonical.get("status"),
        "coder_failure": canonical.get("failure_reason"),
        "infra_failure": canonical.get("infra_failure"),
        "reviewer_decision": reviewer.get("decision"),
        "reviewer_failure": reviewer.get("failure_reason"),
        "protected_drift": protected_drift,
        "checks_passed": all(c["exit_code"] == 0 for c in checks),
        "eligible_for_primary": eligibility,
        "primary_acceptance": "pending" if eligibility else "not_eligible",
        "canonical_archive": str(run_root),
        "seconds": time.monotonic() - started,
        "model_requests": len(list((case / "wire").glob("*-request.json"))),
        "primary_active_seconds": None,
    }
    B.save(case / "result.json", row)
    print(json.dumps(row, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["preflight", "freeze", "run"])
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    if args.action == "run":
        run(args.case, args.used)
    else:
        (preflight if args.action == "preflight" else freeze)()
