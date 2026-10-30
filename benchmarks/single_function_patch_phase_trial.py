"""Frozen patch-only repair phase; prior results and sibling projects are read-only."""

import argparse
import copy
import importlib.util
import json
import shutil
from pathlib import Path

import single_function_entry_trial as prior

BASE = prior.KIT / "benchmarks/work/system-convergence/single-function-patch-phase-20261012-1"
OLD = BASE.parent / "single-function-repair-state-20261012-1"
prior.BASE = BASE


def setup():
    old = prior.common.read(OLD / "freeze.json")
    frozen = {}
    for name in prior.ORDER:
        source = OLD / name / "isolated"
        root = BASE / name / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for folder in ["src", "tests"]:
            shutil.copytree(source / folder, root / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(source / "pyproject.toml", root / "pyproject.toml")
        shutil.copytree(prior.KIT / ".local-agents", root / ".local-agents", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        packet = copy.deepcopy(prior.common.read(source / ".agent/packet.json"))
        run = source / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        for item in prior.common.read(run / "preimages.json"):
            if item["path"] in packet["scope"]["modify"]:
                shutil.copyfile(source / item["archive_path"], root / item["path"])
        for path, digest in old["cases"][name].items():
            if path.startswith(("src/", "tests/")) or path == "pyproject.toml":
                assert prior.common.sha(root / path) == digest, (name, path)
        packet["run_id"] = "single-patch-phase-" + name
        config = prior.common.read(source / ".agent/config.json")
        config["coder_single_function_patch_repair"] = True
        prior.common.save(root / ".agent/packet.json", packet)
        prior.common.save(root / ".agent/config.json", config)
        frozen[name] = {p.relative_to(root).as_posix(): prior.common.sha(p) for p in prior.common.files(root)}
    prior.common.save(BASE / "freeze.json", {"cases": frozen, "order": prior.ORDER,
        "candidate": {p: prior.common.sha(prior.KIT / p) for p in prior.CANDIDATE},
        "driver": prior.common.sha(Path(prior.__file__)), "phase_driver": prior.common.sha(Path(__file__))})
    print("frozen six unchanged inputs; only opt-in patch phase enabled", flush=True)


def audit(name):
    path = BASE.parent / "single-function-terminal-20261012-1/audit.py"
    spec = importlib.util.spec_from_file_location("terminal_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE = BASE
    module.case(name)


def finish():
    frozen = prior.common.read(BASE / "freeze.json")
    for path, digest in frozen["candidate"].items():
        assert prior.common.sha(prior.KIT / path) == digest, path
    assert prior.common.sha(Path(__file__)) == frozen["phase_driver"]
    before = prior.common.read(BASE / "baseline.json")
    changed = [p for p, digest in before.items() if not Path(p).is_file() or prior.common.sha(Path(p)) != digest]
    assert all(p in {str(prior.KIT / item) for item in prior.CANDIDATE}
               for p in changed if Path(p).is_relative_to(prior.KIT)), changed
    rows = [prior.common.read(BASE / name / "independent-result.json") for name in prior.ORDER]
    result = {"rows": rows, "full_chain_passed": sum(r["full_chain_pass"] for r in rows),
              "total": len(rows), "decision": "FROZEN_CORPUS_ONLY" if all(r["full_chain_pass"] for r in rows) else "NO_GENERAL_RELEASE",
              "pinned_files_checked": len(before), "changed_pinned_files": changed,
              "candidate_unchanged_after_live": True, "cross_file": "Primary only", "commit_push": False}
    prior.common.save(BASE / "stage-conclusion.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "setup", "run", "audit", "finish"])
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "checkpoint":
        prior.checkpoint()
        prior.common.save(BASE / "patch-phase-authorization.json", {
            "weekly_used_start": 23, "weekly_used_ceiling": 30,
            "supersedes_checkpoint_candidate_description_only": True,
            "candidate": "Opt-in single-function failed-validation repair: model returns exact patch or explicit block, host dispatches through existing SafeEditor; next turn requires fresh contract confirmation and VALIDATE. Normal action loop otherwise unchanged.",
            "order": prior.ORDER, "gate": "6/6 complete chains with independent checks and unchanged protected inputs; no live tuning",
            "fixed": "models, sampling, contracts, tests, Reviewer, terminal gate, budgets, single residency",
            "brothers_readonly": True, "commit_push": False})
    elif args.action == "setup": setup()
    elif args.action == "run": prior.run(args.case)
    elif args.action == "audit": audit(args.case)
    else: finish()
