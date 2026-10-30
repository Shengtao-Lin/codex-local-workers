"""R1: exactly the original sixteen semantic controls, fresh contexts, no resample."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import time

from convergence_coder import KIT, PYTHON, save
from system_convergence import read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/r1-20261010-1"
OLD = KIT / "benchmarks/work/capability-fit/reviewer-evidence-1"
RUNTIME = BASE / "candidate-kit/.local-agents"


def prepare():
    old = read_object(OLD / "registration.json")
    cells = []
    for original in old["controls"]:
        source = Path(original["root"])
        root = BASE / "cells" / original["id"]
        shutil.copytree(
            source,
            root,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache", "*temp*"),
        )
        request = read_object(source / ".agent/review-request.json")
        request["review_id"] = "r1-display-coverage-1"
        save(root / ".agent/r1-review-request.json", request)
        # Preserve the old .agent verbatim; new filenames/identity never overwrite it.
        artifacts = [
            ref(root, p.relative_to(root).as_posix()) for p in root.rglob("*") if p.is_file()
        ]
        cells.append(
            {
                "id": original["id"],
                "root": str(root),
                "identity": request,
                "inputs": artifacts,
                "expected_decision": original["expected_decision"],
                "expected_defect_primary_only": original["expected_defect"],
                "synthetic_primary_archive": True,
            }
        )
    assert len(cells) == 16
    save(
        BASE / "registration.json",
        {
            "stage": "R1",
            "registered": 16,
            "cells": cells,
            "original_registration": ref(
                KIT, (OLD / "registration.json").relative_to(KIT).as_posix()
            ),
            "historical_adjudications": ref(
                KIT, (OLD / "primary-adjudications-1.json").relative_to(KIT).as_posix()
            ),
            "driver": ref(KIT, "benchmarks/convergence_reviewer.py"),
            "runtime": [
                ref(RUNTIME, p.relative_to(RUNTIME).as_posix()) for p in RUNTIME.rglob("*.py")
            ],
            "weekly_used_start": 51,
            "weekly_used_ceiling": 60,
            "gate": "Original sixteen semantic expectations unchanged; any mismatch HOLD. Coverage may independently qualify as a safety change.",
            "new_coder_calls": 0,
            "resample_allowed": False,
            "cloud_tokens": None,
        },
    )


def run(cell_id):
    registration = read_object(BASE / "registration.json")
    assert sha256(Path(__file__)) == registration["driver"]["sha256"]
    for item in registration["runtime"]:
        assert sha256(RUNTIME / item["path"]) == item["sha256"]
    cell = next(c for c in registration["cells"] if c["id"] == cell_id)
    root = Path(cell["root"])
    for item in cell["inputs"]:
        assert sha256(root / item["path"]) == item["sha256"]
    output = root / "r1-invocation.json"
    if output.exists() or (root / ".agent/r1-reviewer.json").exists():
        raise FileExistsError("already attempted")
    temp = root / ".agent/r1-process-temp"
    temp.mkdir()
    started = time.perf_counter()
    result = subprocess.run(
        [
            str(PYTHON),
            "-B",
            str(RUNTIME / "local-review.py"),
            "--request",
            str(root / ".agent/r1-review-request.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/r1-reviewer.json"),
        ],
        cwd=root,
        env=dict(os.environ, TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    save(
        output,
        {
            "exit": result.returncode,
            "command_wall_seconds": time.perf_counter() - started,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cloud_tokens": None,
        },
    )
    protected = {
        p: sha256(root / p) == sha
        for p, sha in (
            (i["path"], i["sha256"]) for i in cell["inputs"] if not i["path"].startswith(".agent/")
        )
    }
    save(root / "r1-protection.json", protected)
    assert all(protected.values())
    print(cell_id, result.returncode, result.stdout[-1800:], result.stderr[-600:], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    prepare() if args.action == "prepare" else run(args.cell)
