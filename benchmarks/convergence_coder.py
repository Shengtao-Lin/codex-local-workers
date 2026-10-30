"""One frozen C1 candidate against four paired tasks, without retrying history."""

from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess
import time

from system_convergence import read_object, ref, sha256, write_output

KIT = Path(__file__).resolve().parents[1]
BASE = KIT / "benchmarks/work/system-convergence/c1-20261010-1"
PYTHON = KIT.parent / "agent-evaluation-harness/.venv/Scripts/python.exe"
ARMS = {"baseline": BASE / "baseline", "candidate": BASE / "candidate-kit/.local-agents"}


def save(path, value):
    write_output(KIT, path.relative_to(KIT).as_posix(), value)


def prepare():
    if (BASE / "registration.json").exists():
        raise FileExistsError("already registered")
    originals = read_object(
        KIT / "benchmarks/work/capability-fit/fixed-candidate-repeat-1/registration.json"
    )
    cells = []
    for index, kind in enumerate(("timestamp", "async", "anchor", "errors")):
        for arm in ("baseline", "candidate") if index % 2 == 0 else ("candidate", "baseline"):
            cell_id = kind + "-" + arm
            root = BASE / "cells" / cell_id
            if root.exists():
                raise FileExistsError("cell already exists")
            if kind in {"timestamp", "async"}:
                prior = next(c for c in originals["cells"] if c["id"] == kind + "-r1")
                old_root = Path(prior["root"])
                packet = read_object(old_root / ".agent/packet.json")
                archive = old_root / f".agent/tasks/{packet['task_id']}/runs/{packet['run_id']}"
                import json

                images = {
                    p["path"]: p for p in json.loads((archive / "preimages.json").read_text())
                }
                for path, digest in prior["paths"].items():
                    source = (
                        old_root / images[path]["archive_path"]
                        if path in images
                        else old_root / path
                    )
                    assert sha256(source) == digest
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                config = read_object(old_root / ".agent/config.json")
            else:
                shutil.copytree(KIT / ("benchmarks/fixtures/convergence-repair-" + kind), root)
                template = next(c for c in originals["cells"] if c["id"] == "async-r1")
                packet = read_object(Path(template["root"]) / ".agent/packet.json")
                config = read_object(Path(template["root"]) / ".agent/config.json")
                behavior = (
                    "compute delegates exactly once to evaluate. Both APIs return twice the numeric input and 0 for None, including negative and zero values. Preserve wrapper delegation; no extra callbacks or input mutations."
                    if kind == "anchor"
                    else "load_count delegates exactly once to parse_count. Both reject negative integers with ValueError('count must be nonnegative'), reject bool/non-int with TypeError('count must be integer'), and return nonnegative integers unchanged. Preserve wrapper delegation and all other error branches."
                )
                packet.update(
                    goal=behavior,
                    owned_contract_ids=["repair-" + kind],
                    required_behavior=[
                        {"id": "repair-" + kind, "text": behavior, "risk_floor": "medium"}
                    ],
                    scope={
                        "read": ["src", "tests"],
                        "modify": ["src/product/entry.py", "src/product/core.py"],
                        "create": [],
                        "readonly": ["tests", "pyproject.toml"],
                        "forbidden": [".agent", ".git"],
                    },
                    edit_targets=[
                        {
                            "path": "src/product/entry.py",
                            "anchor": "compute" if kind == "anchor" else "load_count",
                        },
                        {
                            "path": "src/product/core.py",
                            "anchor": "evaluate" if kind == "anchor" else "parse_count",
                        },
                    ],
                    focused_tests=[
                        "tests/test_compute.py" if kind == "anchor" else "tests/test_count.py"
                    ],
                    review_feedback=[],
                    implementation_guidance=[],
                )
            packet = copy.deepcopy(packet)
            task = "convergence-c1-" + cell_id
            packet.update(task_id=task, feature_id=task, run_id=task + "-a1")
            save(root / ".agent/packet.json", packet)
            save(root / ".agent/config.json", config)
            paths = [
                p.relative_to(root).as_posix()
                for p in root.rglob("*")
                if p.is_file() and ".agent" not in p.parts
            ]
            cells.append(
                {
                    "id": cell_id,
                    "kind": kind,
                    "arm": arm,
                    "root": str(root),
                    "identity": {k: packet[k] for k in ("task_id", "unit_id", "run_id")},
                    "inputs": [ref(root, p) for p in paths],
                    "writable": packet["scope"]["modify"],
                    "packet": ref(root, ".agent/packet.json"),
                    "config": ref(root, ".agent/config.json"),
                }
            )
    save(
        BASE / "registration.json",
        {
            "stage": "C1",
            "registered_calls": 8,
            "cells": cells,
            "weekly_used_start": 51,
            "weekly_used_ceiling": 60,
            "models_unchanged": True,
            "driver": ref(KIT, "benchmarks/convergence_coder.py"),
            "runtime": {
                arm: [ref(path, p.relative_to(path).as_posix()) for p in path.glob("*.py")]
                for arm, path in ARMS.items()
            },
            "positive_controls": [
                ref(KIT, (BASE / ("positive-" + name + ".xml")).relative_to(KIT).as_posix())
                for name in ("anchor", "errors")
            ],
            "promotion": "All four candidate full chains pass, safety controls pass, and at least one repair exposes baseline path rejection absent in candidate; otherwise KEEP_BASELINE/no live advantage claim",
            "interventions": "Independent Primary review only; no production fixture edits, no external rework or resampling",
        },
    )


def run(cell_id):
    registration = read_object(BASE / "registration.json")
    assert sha256(Path(__file__)) == registration["driver"]["sha256"]
    cell = next(c for c in registration["cells"] if c["id"] == cell_id)
    root = Path(cell["root"])
    for artifact in [cell["packet"], cell["config"], *cell["inputs"]]:
        assert sha256(root / artifact["path"]) == artifact["sha256"]
    runtime = ARMS[cell["arm"]]
    for artifact in registration["runtime"][cell["arm"]]:
        assert sha256(runtime / artifact["path"]) == artifact["sha256"]
    output = root / "invocation.json"
    if output.exists() or (root / ".agent/coder.json").exists():
        raise FileExistsError("already attempted")
    temp = root / ".agent/process-temp"
    temp.mkdir()
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1")
    start = time.perf_counter()
    result = subprocess.run(
        [
            str(PYTHON),
            "-B",
            str(runtime / "local-unit.py"),
            "--packet",
            str(root / ".agent/packet.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/coder.json"),
            "--review-report",
            str(root / ".agent/reviewer.json"),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    save(
        output,
        {
            "exit": result.returncode,
            "command_wall_seconds": time.perf_counter() - start,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    for artifact in cell["inputs"]:
        if artifact["path"] not in cell["writable"]:
            assert sha256(root / artifact["path"]) == artifact["sha256"]
    print(cell_id, result.returncode, result.stdout[-2200:], result.stderr[-500:])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    prepare() if args.action == "prepare" else run(args.cell)
