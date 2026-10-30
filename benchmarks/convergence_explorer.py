"""Frozen E1 investigations over read-only sibling source copies; no source edits."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from system_convergence import read_object, ref, sha256, write_output

KIT = Path(__file__).resolve().parents[1]
BASE = KIT / "benchmarks/work/system-convergence/e1-20261010-1"
PYTHON = KIT / "benchmarks/work/stability-v1/.venv-diagnostics/Scripts/python.exe"
SOURCE = KIT.parent / "agent-runtime-kit"
FILES = (
    "src/agent_runtime/registry.py",
    "src/agent_runtime/runtime.py",
    "tests/unit/test_registry.py",
    "tests/integration/test_runtime.py",
)
QUESTIONS = {
    "caller": (
        "locate",
        "Locate the runtime caller that resolves a registered agent before invoking it, and the registry branch that rejects an unknown agent. Give current source ranges for both; do not claim tests executed.",
    ),
    "integration": (
        "locate",
        "Locate the integration test that demonstrates an idempotent runtime response is replayed without invoking the agent twice. Cite its replay and call-count assertion, and the implementation branch returning the cached response. Do not claim the database test ran.",
    ),
    "absence": (
        "investigate",
        "In src/agent_runtime/registry.py only, determine whether unregister_agent exists. Reconcile any positive matches for AgentRegistry.get without treating them as evidence that unregister_agent exists. Read the registry implementation and state exactly what scope supports an absence conclusion and what remains unknown. Do not generalize to other files or claim tests ran.",
    ),
}


def save(name, value):
    write_output(KIT, (BASE / name).relative_to(KIT).as_posix(), value)


def prepare():
    if BASE.exists():
        raise FileExistsError("batch already exists")
    BASE.mkdir(parents=True)
    config = read_object(KIT / ".local-agents/config.json")
    config.update(
        model_load_backend="cli", model_load_cli_path=r"C:\Users\Lin\.lmstudio\bin\lms.exe"
    )
    cells = []
    for question, (mode, task) in QUESTIONS.items():
        for repeat in (1, 2):
            cell_id = f"{question}-r{repeat}"
            root = BASE / cell_id
            for path in FILES:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SOURCE / path, target)
            local_config = dict(config, explorer_mode=mode)
            save(cell_id + "/.agent/config.json", local_config)
            cells.append(
                {
                    "id": cell_id,
                    "question": question,
                    "task": task,
                    "mode": mode,
                    "task_id": "convergence-e1-" + cell_id,
                    "root": str(root),
                    "inputs": [ref(root, p) for p in FILES],
                    "config": ref(root, ".agent/config.json"),
                    "assistance": "Question gives symbols/behavior, not answer paths except explicit negative-search scope",
                    "fresh_context": True,
                    "expected": "Independently satisfy every question obligation with current displayed evidence; scoped negative with uncertainties is valid",
                }
            )
    save(
        "registration.json",
        {
            "stage": "E1",
            "candidate": "unchanged-current-baseline",
            "runtime": [
                ref(KIT, p.relative_to(KIT).as_posix())
                for p in (KIT / ".local-agents").glob("*.py")
            ],
            "driver": ref(KIT, "benchmarks/convergence_explorer.py"),
            "source": str(SOURCE),
            "cells": cells,
            "registered_calls": 6,
            "weekly_used_start": 50,
            "weekly_used_ceiling": 60,
            "no_known_answer_anchors": True,
            "no_cache_or_task_hints_copied": True,
            "promotion": "6/6 question-complete, preserve all failures, otherwise limited research assistant",
        },
    )


def run(cell_id):
    registration = read_object(BASE / "registration.json")
    for artifact in [registration["driver"], *registration["runtime"]]:
        if sha256(KIT / artifact["path"]) != artifact["sha256"]:
            raise ValueError("registered runtime or driver drift")
    cell = next(c for c in registration["cells"] if c["id"] == cell_id)
    root = Path(cell["root"])
    report = root / ".agent/explorer.json"
    if report.exists() or (BASE / (cell_id + "/invocation.json")).exists():
        raise FileExistsError("call already attempted")
    for artifact in [cell["config"], *cell["inputs"]]:
        if sha256(root / artifact["path"]) != artifact["sha256"]:
            raise ValueError("registered input drift")
    temp = root / ".agent/process-temp"
    temp.mkdir()
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1")
    start = time.perf_counter()
    result = subprocess.run(
        [
            str(PYTHON),
            "-B",
            str(KIT / ".local-agents/explorer-runtime.py"),
            "--task",
            cell["task"],
            "--task-id",
            cell["task_id"],
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(report),
            "--full-report",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    save(
        cell_id + "/invocation.json",
        {
            "exit_code": result.returncode,
            "command_wall_seconds": time.perf_counter() - start,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "loading_seconds": None,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    changed = [a["path"] for a in cell["inputs"] if sha256(root / a["path"]) != a["sha256"]]
    if changed:
        raise ValueError("read-only fixture changed: " + repr(changed))
    value = read_object(report) if report.is_file() else {}
    print(
        json.dumps(
            {
                "cell": cell_id,
                "exit": result.returncode,
                "status": value.get("status"),
                "failure_reason": value.get("failure_reason"),
                "cache": value.get("cache"),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    prepare() if args.action == "prepare" else run(args.cell)
