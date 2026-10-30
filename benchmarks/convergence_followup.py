"""New authorized iteration; immutable old candidates, fixed original role gates."""

import argparse
import os
import shutil
from pathlib import Path

import convergence_reviewer as reviewer
from convergence_coder import KIT, save
from system_convergence import read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/followup-20261011-2"
PREVIOUS = KIT / "benchmarks/work/system-convergence/i1-20261011-1"


def prepare():
    BASE.mkdir(parents=True, exist_ok=False)
    sources = []
    for folder in (".local-agents", "benchmarks", "tests", "docs", "scripts"):
        for directory, children, files in os.walk(KIT / folder):
            children[:] = [
                name
                for name in children
                if name not in {"work", "__pycache__", ".pytest_cache", ".ruff_cache"}
            ]
            for name in files:
                path = Path(directory) / name
                relative = path.relative_to(KIT)
                sources.append(ref(KIT, relative.as_posix()))
    save(
        BASE / "baseline.json",
        {
            "sources": sources,
            "previous_decision": ref(
                KIT, (PREVIOUS / "stage-decision-1.json").relative_to(KIT).as_posix()
            ),
            "previous_gates": read_object(PREVIOUS / "release-gates.json"),
            "weekly_used_start": 0,
            "weekly_used_ceiling": 15,
            "usage_reset_at": 1792295862,
            "models_changed": False,
            "original_gates_unchanged": True,
            "production_promotion_allowed": False,
        },
    )
    shutil.copytree(
        PREVIOUS / "candidate-kit",
        BASE / "candidate-kit",
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )
    # Original historical adapter inputs are data, not new model executions.
    historical = [
        "tool-native-nudge-1/fresh-2",
        "tool-deadline-fresh-1/candidate-1",
    ]
    for name in historical:
        source = KIT / "benchmarks/work/capability-fit" / name
        target = BASE / "candidate-kit/benchmarks/work/capability-fit" / name
        if not target.exists():
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns(
                    "__pycache__", ".pytest_cache", ".ruff_cache", "*temp*"
                ),
            )


def register_reviewer():
    reviewer.BASE = BASE / "reviewer"
    reviewer.RUNTIME = BASE / "candidate-kit/.local-agents"
    # Old driver verifies itself; wrapper and exact new runtime are also frozen.
    reviewer.prepare()
    save(
        reviewer.BASE / "followup-registration.json",
        {
            "registration": ref(reviewer.BASE, "registration.json"),
            "driver": ref(KIT, "benchmarks/convergence_followup.py"),
            "weekly_used_start": 0,
            "weekly_used_ceiling": 15,
            "candidate": "first-observation-freshness-1",
            "old_gate": "All original sixteen unchanged semantic expectations; no resample",
            "old_registration_budget_superseded": True,
        },
    )


def assemble_coordinator():
    source = BASE / "candidate-kit"
    target = BASE / "coordinator-kit"
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if not path.is_file() or any(
            part in {"__pycache__", ".pytest_cache", ".ruff_cache"}
            for part in relative.parts
        ):
            continue
        destination = target / relative
        if destination.exists():
            assert sha256(destination) == sha256(path), str(relative)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)


def run_reviewer(cell):
    reviewer.BASE = BASE / "reviewer"
    reviewer.RUNTIME = BASE / "candidate-kit/.local-agents"
    followup = read_object(reviewer.BASE / "followup-registration.json")
    assert sha256(Path(__file__)) == followup["driver"]["sha256"]
    assert (
        sha256(reviewer.BASE / "registration.json")
        == followup["registration"]["sha256"]
    )
    reviewer.run(cell)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "register-reviewer",
            "run-reviewer",
            "assemble-coordinator",
        ),
    )
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "register-reviewer":
        register_reviewer()
    elif args.action == "assemble-coordinator":
        assemble_coordinator()
    else:
        run_reviewer(args.cell)
