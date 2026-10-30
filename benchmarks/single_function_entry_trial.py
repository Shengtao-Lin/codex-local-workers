"""Frozen single-function normal-entry trial. Sibling repositories are read-only."""
import argparse
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import repair_transfer as transfer

common = transfer.common
KIT = common.KIT
BASE = KIT / "benchmarks/work/system-convergence/single-function-entry-20261012-1"
ORDER = ["repair-1", "presence-1", "presence-2", "repair-2", "repair-3", "presence-3"]
CANDIDATE = [".local-agents/worker-runtime.py", ".local-agents/single-function-context.py"]


def checkpoint():
    BASE.mkdir(parents=True, exist_ok=False)
    paths = {KIT / p for p in subprocess.check_output(
        ["git", "ls-files", "-c", "-o", "--exclude-standard"], cwd=KIT, text=True).splitlines()
        if (KIT / p).is_file()}
    paths.update(p for p in common.files(BASE.parent) if not p.is_relative_to(BASE))
    siblings = {}
    for name in ["agent-evaluation-harness", "agent-runtime-kit"]:
        root = KIT.parent / name
        for folder in ["src", "tests", "docs", ".agent", ".local-agents"]:
            paths.update(common.files(root / folder))
        siblings[name] = {key: subprocess.check_output(["git", "-C", str(root), *cmd], text=True)
                          for key, cmd in {"head": ["rev-parse", "HEAD"], "status": ["status", "--short"]}.items()}
    paths.add(KIT / ".local-agents/config.json")
    for path in CANDIDATE:
        source = KIT / path
        if source.exists():
            target = BASE / "preimages" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    common.save(BASE / "baseline.json", {str(p): common.sha(p) for p in sorted(paths)})
    common.save(BASE / "authorization.json", {
        "weekly_used_start": 16, "weekly_used_ceiling": 30,
        "candidate_files": CANDIDATE, "feature_id": "single-function-formal-entry",
        "feature_risk": "high", "unit_risk": "high", "integration_risk": "high",
        "risk_rationale": "Changes context and edit constraints, preserving existing runtime/handoff safety gates.",
        "dependencies": [], "owned_contract_ids": ["single-function-scope", "current-validation", "independent-review"],
        "fixed_order": ORDER, "gate": "6/6 Coder all checks + verified automatic handoff + Reviewer pass_to_primary + independent checks; no scope escape; no external repair or candidate tuning after live.",
        "budgets": "Existing runtime/model limits unchanged; one invocation per frozen case; existing local-unit infrastructure-only reviewer retry preserved.",
        "candidate": "Opt-in compact current-function context within existing WorkerRuntime loop, function-scoped block edit guard, existing controlled formatter enabled before trailing-whitespace gate. No model acknowledgements synthesized.",
        "cross_file": "Primary only; rejected by candidate configuration", "siblings": siblings,
        "commit_push": False, "single_model_residency": True})
    print("pinned", len(paths), flush=True)


def setup():
    frozen = {}
    for name in ORDER:
        family = name.split("-")[0]
        old = (transfer.BASE / "presence-1/isolated" if family == "presence"
               else transfer.screen.BASE / "minimal-json-1/isolated")
        root = BASE / name / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for folder in ["src", "tests"]:
            shutil.copytree(old / folder, root / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(old / "pyproject.toml", root / "pyproject.toml")
        shutil.copytree(KIT / ".local-agents", root / ".local-agents", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        if family == "presence":
            path, symbol = transfer.SCORERS, "OutputPresentScorer.score"
            shutil.copyfile(transfer.BASE / "original" / path, root / path)
            goal = transfer.TASKS["presence"]["goal"]
            dependency = transfer.TASKS["presence"]["dependencies"]
        else:
            path, symbol = transfer.screen.SOURCE, transfer.screen.SYMBOL
            shutil.copyfile(transfer.screen.OLD / path, root / path)
            goal = transfer.screen.REQUEST
            dependency = "self.get(id) is async and returns SourceTrace; preserve returned object identity."
        packet = copy.deepcopy(common.read(old / ".agent/packet.json"))
        packet.update(task_id="single-function-entry-" + family, run_id="single-function-entry-" + name, goal=goal)
        config = common.read(old / ".agent/config.json")
        config.update(coder_single_function={"path": path, "symbol": symbol, "dependencies": dependency},
                      autoformat_on_diff_whitespace=True)
        common.save(root / ".agent/packet.json", packet)
        common.save(root / ".agent/config.json", config)
        frozen[name] = {p.relative_to(root).as_posix(): common.sha(p) for p in common.files(root)}
    common.save(BASE / "freeze.json", {"cases": frozen, "order": ORDER,
        "candidate": {p: common.sha(KIT / p) for p in CANDIDATE}, "driver": common.sha(Path(__file__))})
    print("frozen", len(frozen), flush=True)


def run(name):
    frozen = common.read(BASE / "freeze.json")
    assert common.sha(Path(__file__)) == frozen["driver"]
    root = BASE / name / "isolated"
    for path, digest in frozen["cases"][name].items():
        assert common.sha(root / path) == digest, path
    common.save(BASE / name / "started.json", {"case": name, "entry": "local-unit.py"})
    result = subprocess.run([sys.executable, "-B", str(root / ".local-agents/local-unit.py"),
        "--packet", str(root / ".agent/packet.json"), "--config", str(root / ".agent/config.json")],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    common.save(BASE / name / "entry-result.json", {"exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    print(name, result.returncode, result.stdout[-5000:], result.stderr[-1000:], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "setup", "run"])
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "checkpoint": checkpoint()
    elif args.action == "setup": setup()
    else: run(args.case)
