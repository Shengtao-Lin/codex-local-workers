"""One typed answer with runtime-owned provenance, same six E1 questions."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from convergence_coder import KIT, save
from convergence_evidence_protocol import BASE, OLD
from system_convergence import read_object, ref, sha256

ROOT = BASE / "explorer"
TARGET = ROOT / "candidate-kit"
RUNTIME = TARGET / ".local-agents"
PYTHON = KIT / "benchmarks/work/stability-v1/.venv-diagnostics/Scripts/python.exe"
ORIGINAL = KIT / "benchmarks/work/system-convergence/e1-20261010-1"


def prepare():
    shutil.copytree(
        OLD / "i1-candidate-kit",
        TARGET,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )


def register():
    xml = ROOT / "full-regression-1.xml"
    cases = list(ET.parse(xml).iter("testcase"))
    assert not any(
        c.find("failure") is not None or c.find("error") is not None for c in cases
    )
    cells = []
    original = read_object(ORIGINAL / "registration.json")
    for cell in original["cells"]:
        source, root = Path(cell["root"]), ROOT / "cells" / cell["id"]
        root.mkdir(parents=True, exist_ok=False)
        for item in cell["inputs"]:
            assert sha256(source / item["path"]) == item["sha256"]
            target = root / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / item["path"], target)
        config = read_object(source / cell["config"]["path"])
        config["explorer_answer_protocol"] = True
        save(root / ".agent/config.json", config)
        cells.append(
            {
                **cell,
                "root": str(root),
                "task_id": "answer-e1-" + cell["id"],
                "config": ref(root, ".agent/config.json"),
                "mode_presentation": "Original questions unchanged; both locate and investigate use typed final answer, not free tool-history narrative",
            }
        )
    save(
        ROOT / "registration.json",
        {
            **original,
            "cells": cells,
            "candidate": "explorer-typed-scope-answer-1",
            "driver": ref(KIT, "benchmarks/convergence_explorer_answers.py"),
            "runtime": [
                ref(RUNTIME, p.relative_to(RUNTIME).as_posix())
                for p in RUNTIME.rglob("*.py")
            ],
            "weekly_used_start": 2,
            "weekly_used_ceiling": 15,
            "original_registration": ref(
                KIT, (ORIGINAL / "registration.json").relative_to(KIT).as_posix()
            ),
            "offline_regression": ref(ROOT, xml.name),
            "gate": "Original six independently complete and truthful; typed claims are still independently judged, never automatic semantics",
            "known_corpus_not_blind_novel_task": True,
            "resample_allowed": False,
        },
    )


def run(cell_id):
    registration = read_object(ROOT / "registration.json")
    assert sha256(Path(__file__)) == registration["driver"]["sha256"]
    for item in registration["runtime"]:
        assert sha256(RUNTIME / item["path"]) == item["sha256"]
    cell = next(c for c in registration["cells"] if c["id"] == cell_id)
    root = Path(cell["root"])
    for item in [cell["config"], *cell["inputs"]]:
        assert sha256(root / item["path"]) == item["sha256"]
    output, report = root / "invocation.json", root / ".agent/explorer.json"
    if output.exists() or report.exists():
        raise FileExistsError("already attempted")
    temp = root / ".agent/process-temp"
    temp.mkdir()
    start = time.perf_counter()
    result = subprocess.run(
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
            str(report),
            "--full-report",
        ],
        cwd=root,
        env=dict(
            os.environ, TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1"
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    save(
        output,
        {
            "exit": result.returncode,
            "command_wall_seconds": time.perf_counter() - start,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cloud_tokens": None,
        },
    )
    assert all(sha256(root / a["path"]) == a["sha256"] for a in cell["inputs"])
    data = read_object(report)
    print(
        cell_id,
        data["status"],
        data.get("model_answer"),
        data.get("failure_reason"),
        flush=True,
    )


def regression():
    temp = ROOT / "regression-temp-1"
    temp.mkdir(exist_ok=False)
    tempfile.tempdir = str(temp)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["R1_RUNTIME_ROOT"] = str(RUNTIME)
    os.chdir(TARGET)
    sys.path[:0] = [str(TARGET / "benchmarks"), str(TARGET)]
    import tool_reviewer_protocol_reference_trial
    import tool_reviewer_test_consistency_trial
    from convergence_coder import PYTHON as dependency_python

    tool_reviewer_protocol_reference_trial.PYTHON = dependency_python
    tool_reviewer_test_consistency_trial.PYTHON = dependency_python
    import pytest

    raise SystemExit(
        pytest.main(
            [
                ".local-agents/tests",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(temp / "pytest"),
                "--junitxml=" + str(ROOT / "full-regression-1.xml"),
            ]
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "register", "run", "regression"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    {"prepare": prepare, "register": register, "regression": regression}.get(
        args.action, lambda: run(args.cell)
    )()
