"""C2 four-cell adapter reusing C1's bounded local-unit launcher."""

import argparse
import json
from pathlib import Path
import runpy
import shutil
import sys

import convergence_coder as shared
from system_convergence import read_object, ref, sha256

KIT = shared.KIT
BASE = KIT / "benchmarks/work/system-convergence/c2-20261010-1"
shared.BASE = BASE
shared.ARMS = {
    "baseline": KIT / "benchmarks/work/system-convergence/c1-20261010-1/baseline",
    "candidate": BASE / "candidate-kit/.local-agents",
}


def prepare():
    original = read_object(
        KIT / "benchmarks/work/system-convergence/c1-20261010-1/registration.json"
    )
    cells = []
    for kind, arms in (
        ("timestamp", ("baseline", "candidate")),
        ("async", ("candidate", "baseline")),
    ):
        source_cell = next(c for c in original["cells"] if c["id"] == kind + "-baseline")
        source_root = Path(source_cell["root"])
        ident = source_cell["identity"]
        archive = source_root / f".agent/tasks/{ident['task_id']}/runs/{ident['run_id']}"
        preimages = {p["path"]: p for p in json.loads((archive / "preimages.json").read_text())}
        for arm in arms:
            cell_id = kind + "-" + arm
            root = BASE / "cells" / cell_id
            if root.exists():
                raise FileExistsError("cell exists")
            for item in source_cell["inputs"]:
                path = item["path"]
                source = (
                    source_root / preimages[path]["archive_path"]
                    if path in preimages
                    else source_root / path
                )
                assert sha256(source) == item["sha256"]
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            packet = read_object(source_root / ".agent/packet.json")
            task = "convergence-c2-" + cell_id
            packet.update(task_id=task, feature_id=task, run_id=task + "-a1")
            shared.save(root / ".agent/packet.json", packet)
            shared.save(
                root / ".agent/config.json", read_object(source_root / ".agent/config.json")
            )
            cells.append(
                {
                    "id": cell_id,
                    "kind": kind,
                    "arm": arm,
                    "root": str(root),
                    "identity": {k: packet[k] for k in ("task_id", "unit_id", "run_id")},
                    "inputs": source_cell["inputs"],
                    "writable": source_cell["writable"],
                    "packet": ref(root, ".agent/packet.json"),
                    "config": ref(root, ".agent/config.json"),
                }
            )
    shared.save(
        BASE / "registration.json",
        {
            "stage": "C2",
            "registered_calls": 4,
            "cells": cells,
            "driver": ref(KIT, "benchmarks/convergence_coder.py"),
            "adapter_driver": ref(KIT, "benchmarks/convergence_diagnostic.py"),
            "candidate_tests": ref(
                BASE / "candidate-kit", ".local-agents/tests/test_worker_runtime.py"
            ),
            "runtime": {
                arm: [ref(path, p.relative_to(path).as_posix()) for p in path.glob("*.py")]
                for arm, path in shared.ARMS.items()
            },
            "weekly_used_start": 51,
            "weekly_used_ceiling": 60,
            "promotion": "Candidate two full-chain accepts, unchanged protected gates and fewer target diagnostic-field errors; otherwise KEEP_BASELINE",
            "reuses_launcher": True,
            "C1_stacked": False,
            "external_rework_allowed": False,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "audit"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "run":
        registration = read_object(BASE / "registration.json")
        assert sha256(Path(__file__)) == registration["adapter_driver"]["sha256"]
        assert (
            sha256(BASE / "candidate-kit/.local-agents/tests/test_worker_runtime.py")
            == registration["candidate_tests"]["sha256"]
        )
        shared.run(args.cell)
    else:
        sys.argv = ["convergence_coder_audit.py", args.cell]
        runpy.run_path(str(KIT / "benchmarks/convergence_coder_audit.py"), run_name="__main__")
