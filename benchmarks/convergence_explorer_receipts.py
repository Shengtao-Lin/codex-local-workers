"""Explorer candidate: bounded navigation and actual SEARCH receipts, same E1 obligations."""

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

from convergence_coder import KIT, PYTHON, save
from convergence_followup import BASE
from system_convergence import read_object, ref, sha256

ROOT = BASE / "explorer"
RUNTIME = ROOT / "candidate-kit/.local-agents"
OLD = KIT / "benchmarks/work/system-convergence/e1-20261010-1"


def prepare():
    shutil.copytree(
        BASE / "candidate-kit",
        ROOT / "candidate-kit",
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )


def register():
    old = read_object(OLD / "registration.json")
    cells = []
    for item in old["cells"]:
        source = Path(item["root"])
        root = ROOT / "cells" / item["id"]
        root.mkdir(parents=True, exist_ok=False)
        for artifact in item["inputs"]:
            path = artifact["path"]
            assert sha256(source / path) == artifact["sha256"]
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / path, root / path)
        config = read_object(source / item["config"]["path"])
        save(root / ".agent/config.json", config)
        cells.append(
            {
                **item,
                "root": str(root),
                "task_id": "receipt-e1-" + item["id"],
                "config": ref(root, ".agent/config.json"),
                "exposure": "Same frozen E1 questions; new observation protocol, not novel-task credit",
            }
        )
    save(
        ROOT / "registration.json",
        {
            **old,
            "cells": cells,
            "driver": ref(KIT, "benchmarks/convergence_explorer_receipts.py"),
            "runtime": [
                ref(RUNTIME, p.relative_to(RUNTIME).as_posix())
                for p in RUNTIME.rglob("*.py")
            ],
            "candidate": "bounded-navigation-and-search-receipts-1",
            "weekly_used_start": 1,
            "weekly_used_ceiling": 15,
            "original_registration": ref(
                KIT, (OLD / "registration.json").relative_to(KIT).as_posix()
            ),
        },
    )


def run(cell_id):
    registration = read_object(ROOT / "registration.json")
    assert sha256(Path(__file__)) == registration["driver"]["sha256"]
    for artifact in registration["runtime"]:
        assert sha256(RUNTIME / artifact["path"]) == artifact["sha256"]
    cell = next(c for c in registration["cells"] if c["id"] == cell_id)
    root = Path(cell["root"])
    output = root / "invocation.json"
    if output.exists() or (root / ".agent/explorer.json").exists():
        raise FileExistsError("already attempted")
    for artifact in [cell["config"], *cell["inputs"]]:
        assert sha256(root / artifact["path"]) == artifact["sha256"]
    temp = root / ".agent/process-temp"
    temp.mkdir()
    start = time.perf_counter()
    process = subprocess.run(
        [
            str(PYTHON),
            "-B",
            str(RUNTIME / "explorer-runtime.py"),
            "--task",
            cell["task"],
            "--task-id",
            cell["task_id"],
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
        ],
        cwd=root,
        env=dict(
            os.environ, TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1"
        ),
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    save(
        output,
        {
            "exit": process.returncode,
            "command_wall_seconds": time.perf_counter() - start,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "cloud_tokens": None,
        },
    )
    assert all(sha256(root / a["path"]) == a["sha256"] for a in cell["inputs"])
    report = read_object(root / ".agent/explorer.json")
    print(cell_id, report.get("status"), report.get("failure_reason"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "register", "run"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "register":
        register()
    else:
        run(args.cell)
