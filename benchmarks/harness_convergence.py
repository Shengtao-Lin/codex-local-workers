"""Read-only baseline capture and isolated R0/R1/R2 preparation.

All generated state lives under the explicit batch root. No production writes,
no old-driver BASE mutation, and no model requests during preparation.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SOURCE = "src/evaluation_harness/trace_sources/mlflow.py"
SYMBOL = "MlflowTraceSource.get_many"
HISTORY = KIT / "benchmarks/work/system-convergence"
SHORT = HISTORY / "ruff-repair-20261011-1/repeat-1/isolated"
LONG = HISTORY / "single-function-patch-phase-20261012-1/live/repair-1/isolated"
FIXTURE = HISTORY / "harness-factorial-20261012-1/minimal-json-1/isolated"
PLAN = "docs/local-model-harness-convergence-plan.md"
EXCLUDE = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def files(root):
    for parent, directories, names in os.walk(root, followlinks=False):
        directories[:] = [d for d in directories if d not in EXCLUDE]
        for name in names:
            path = Path(parent) / name
            if path.is_file() and not path.is_symlink() and path.suffix != ".pyc":
                yield path


def command(argv, cwd=KIT):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, check=False)
    return {"argv": list(map(str, argv)), "exit_code": result.returncode,
            "stdout": result.stdout.decode("utf-8", errors="replace"),
            "stderr": result.stderr.decode("utf-8", errors="replace")}


def method(source):
    tree = ast.parse(source)
    owner, symbol = SYMBOL.split(".")
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner)
    functions = [n for n in node.body if isinstance(n, ast.AsyncFunctionDef) and n.name == symbol]
    if len(functions) != 1:
        raise ValueError("Target method is missing or ambiguous")
    node = functions[0]
    return "".join(source.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])


def prepare(batch, usage):
    batch = batch.resolve()
    allowed = (KIT / "benchmarks/work/harness-convergence").resolve()
    if not batch.is_relative_to(allowed) or batch == allowed:
        raise ValueError("Batch must be a new child of benchmarks/work/harness-convergence")
    batch.mkdir(parents=True, exist_ok=False)
    listed = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=KIT,
        text=True, encoding="utf-8").splitlines()
    existing = {KIT / p for p in listed if (KIT / p).is_file()}
    existing.add(KIT / ".local-agents/config.json")
    existing.update(files(HISTORY))
    sibling_state = {}
    for name in ("agent-evaluation-harness", "agent-runtime-kit"):
        root = KIT.parent / name
        sibling_state[name] = {key: command(["git", "-C", str(root), *args])
                               for key, args in {"head": ["rev-parse", "HEAD"],
                                                 "status": ["status", "--short"]}.items()}
        for directory in ("src", "tests", "docs", ".agent", ".local-agents"):
            existing.update(files(root / directory))
        existing.update(p for p in (root / "AGENTS.md", root / "pyproject.toml") if p.exists())
    baseline = {str(path): sha(path) for path in sorted(existing)}
    save(batch / "baseline.json", baseline)
    # A named recoverable checkpoint of the actual dirty working files.
    for relative in listed:
        source = KIT / relative
        if source.is_file():
            target = batch / "checkpoint" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    shutil.copyfile(KIT / ".local-agents/config.json", batch / "checkpoint/.local-agents/config.json")
    with (batch / "tracked.diff").open("xb") as handle:
        handle.write(subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=KIT))
    environment = {
        "cwd": str(KIT), "usage_start": usage, "usage_ceiling": 30,
        "python": command([sys.executable, "-B", "--version"]),
        "git": {key: command(["git", *args]) for key, args in {
            "head": ["rev-parse", "HEAD"], "branch": ["branch", "--show-current"],
            "status": ["status", "--short"]}.items()},
        "siblings": sibling_state,
        "resident": command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
        "lock_exists": (KIT / ".agent/local-worker-write.lock").exists(),
        "root_config": read(KIT / ".local-agents/config.json"),
        "seed": "unknown; unchanged current sampling", "kv_cache_actual": "unknown",
    }
    save(batch / "environment.json", environment)
    checks = {}
    expected = {"original": (SHORT, 395), "failed-draft": (LONG, 648)}
    for label, (root, length) in expected.items():
        source = root / SOURCE
        block = method(source.read_text(encoding="utf-8-sig"))
        if len(block) != length:
            raise ValueError(f"Unexpected {label} target length {len(block)}")
        checks[label] = {"source": str(source), "sha256": sha(source),
                         "method_sha256": hashlib.sha256(block.encode()).hexdigest(),
                         "method_chars": len(block)}
    evidence = [
        HISTORY / "harness-factorial-20261012-1/stage-conclusion.json",
        HISTORY / "single-function-terminal-20261012-1/stage-conclusion.json",
        HISTORY / "single-function-repair-state-20261012-1/stage-conclusion.json",
        HISTORY / "single-function-patch-phase-20261012-1/closeout.json",
        HISTORY / "integration-delivery-20261011-3/stage-decision-1.json",
        HISTORY / "mixed-execution-20261011-2/release-boundary-1.json",
        LONG / ".agent/tasks/single-function-entry-repair/runs/single-patch-phase-repair-1/preimages.json",
        LONG / ".agent/tasks/single-function-entry-repair/runs/single-patch-phase-repair-1/validation-attempt-1.json",
        LONG / ".agent/tasks/single-function-entry-repair/runs/single-patch-phase-repair-1/cumulative.diff",
    ]
    if any(not p.is_file() for p in evidence):
        raise FileNotFoundError([str(p) for p in evidence if not p.is_file()])
    save(batch / "current-state.json", {
        "evidence": [{"path": str(p), "sha256": sha(p)} for p in evidence],
        "facts": "Limited I1 qualified; old D2/C4 failures retained; latest patch candidate 0/6, not released",
        "source_snapshots": checks,
        "root_mode": "single-function/patch modes absent from root config; only historical isolated modes enabled",
        "installed_sibling_versions": "Exact runtime hashes in baseline; no sibling deployment performed",
        "last_roles": "Latest patch batch only Qwen; zero Reviewer/Explorer/Coordinator invocations. Earlier role evidence remains scope-limited.",
    })
    order = []
    for repeat in range(1, 4):
        pairs = [("original", "minimal"), ("failed-draft", "formal"),
                 ("failed-draft", "minimal"), ("original", "formal")]
        if repeat == 2:
            pairs.reverse()
        for snapshot, context in pairs:
            order.append(f"{snapshot}-{context}-{repeat}")
    for name in order:
        snapshot = "failed-draft" if name.startswith("failed-draft") else "original"
        root = batch / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for directory in ("src", "tests"):
            shutil.copytree(FIXTURE / directory, root / directory,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(FIXTURE / "pyproject.toml", root / "pyproject.toml")
        shutil.copyfile(expected[snapshot][0] / SOURCE, root / SOURCE)
        packet = read(LONG / ".agent/packet.json")
        packet["run_id"] = f"harness-r2-{name}"
        save(root / ".agent/packet.json", packet)
        save(root / ".agent/config.json", read(LONG / ".agent/config.json"))
    save(batch / "freeze.json", {
        "plan": sha(KIT / PLAN), "driver": sha(Path(__file__)),
        "cases": {name: {str(p.relative_to(batch / "cases" / name / "isolated")): sha(p)
                          for p in files(batch / "cases" / name / "isolated")} for name in order},
        "source_snapshots": checks,
    })
    save(batch / "registration.json", {
        "stages": ["R0", "R1", "R2"], "feature_id": "matched-harness-diagnostic",
        "risk": {"feature": "high", "unit": "high", "integration": "high"},
        "risk_rationale": "Execute untrusted patch proposals in protected isolated copies; unchanged source/contract/hash gates",
        "owned_contract_ids": ["sequential-trace-batch", "preservation", "diagnostic-attribution"],
        "dependencies": ["R1 controls all pass before live"], "order": order,
        "registered_cells": 12, "proposals_per_cell": 1, "autoformat": False,
        "r2_gate": "At least one context on the archived 648-character draft all-check passes 3/3",
        "checks": ["pytest 11 executed", "ruff format --check", "ruff check", "strict pyright", "protected hash"],
        "no_live_retry": True, "no_reviewer": True, "r3_authorized": False,
        "usage_ceiling": 30, "model": environment["root_config"]["coder_model"],
    })
    save(batch / "preservation.json", {"checkpoint": "checkpoint", "tracked_diff": "tracked.diff",
         "frozen_paths": len(baseline), "production_edits_authorized": [], "history_overwrite": False})
    print(json.dumps({"batch": str(batch), "frozen_paths": len(baseline),
                      "cases": len(order), "snapshots": checks}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare"])
    parser.add_argument("--batch", required=True, type=Path)
    parser.add_argument("--usage", required=True, type=int)
    args = parser.parse_args()
    prepare(args.batch, args.usage)
