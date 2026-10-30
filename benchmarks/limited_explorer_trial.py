"""Read-only navigation controls on unchanged sibling code, not causal repair."""

import argparse
import shutil
from pathlib import Path

import bounded_evidence_support as S
import reviewer_causal_investigation as E

BATCH = S.KIT / "benchmarks/work/harness-convergence/limited-explorer-20261020-1"
UPSTREAM = Path("F:/ChatGPT/agent-runtime-kit")
ORDER = ["agent-1", "tool-1", "tool-2", "agent-2"]
FILES = [
    "src/agent_runtime/registry.py",
    "src/agent_runtime/tools/registry.py",
    "src/agent_runtime/tools/models.py",
    "src/agent_runtime/models.py",
    "src/agent_runtime/errors.py",
    "src/agent_runtime/config.py",
    "tests/unit/test_registry.py",
    "tests/unit/test_tools.py",
]
QUESTIONS = {
    "agent": "One read-only locating question: where is duplicate AGENT registration rejected, and which actual unit-test lines demonstrate that rejection? Distinguish agent registration from tool registration. Cite the implementation branch, exception definition and actual test expectation. Source is under src/agent_runtime, tests under tests/unit. Do not claim tests were executed or infer a defect; return bounded references with remaining uncertainty.",
    "tool": "One read-only locating question: where is a TOOL invocation timeout mapped to its stable timeout error, and which actual unit-test lines demonstrate timeout rather than ordinary handler failure? Cite the controlling branch, exception definition and actual timeout assertion. Source is under src/agent_runtime, tests under tests/unit. Do not claim tests were executed or infer a defect; return bounded references with remaining uncertainty.",
}


def prepare():
    rows = {}
    for cell in ORDER:
        family = cell.split("-")[0]
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        hashes = {}
        for name in FILES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(UPSTREAM / name, target)
            hashes[name] = S.sha(UPSTREAM / name)
        shutil.copytree(
            S.KIT / ".local-agents",
            root / ".local-agents",
            ignore=shutil.ignore_patterns("tests", "__pycache__", ".ruff_cache"),
        )
        config = S.read(S.KIT / ".local-agents/config.example.json")
        config.update(
            python=str(S.PYTHON),
            model_load_backend="cli",
            model_load_cli_path="C:/Users/Lin/.lmstudio/bin/lms.exe",
            explorer_mode="locate",
            explorer_answer_protocol=False,
            max_explorer_turns=16,
            max_explorer_file_reads=8,
            max_explorer_searches=10,
            max_explorer_protocol_errors=6,
            explorer_invocation_timeout_seconds=600,
            explorer_required_citation_paths=[
                "src/agent_runtime/registry.py"
                if family == "agent"
                else "src/agent_runtime/tools/registry.py",
                "src/agent_runtime/errors.py",
                "tests/unit/test_registry.py"
                if family == "agent"
                else "tests/unit/test_tools.py",
            ],
        )
        S.save(root / ".agent/config.json", config)
        rows[cell] = {
            "root": str(root),
            "question": QUESTIONS[family],
            "upstream_source_hashes": hashes,
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
            },
        }
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 4,
            "cells": rows,
            "weekly_stop": 50,
            "batch_seconds": 3600,
            "model": "openai/gpt-oss-20b",
            "context_length": 32768,
            "turns": 16,
            "reads": 8,
            "searches": 10,
            "errors": 6,
            "per_call_seconds": 600,
            "pins": {str(p): S.sha(p) for p in (Path(__file__), Path(E.__file__))},
            "gate": "4/4 source-backed correct navigation reports, each family2/2, no invented execution or protected drift. Ordinary failures retained; no revised questions or resampling.",
            "scope": "Copied unchanged sibling source/test navigation, paths constrained by existing required citation mechanism. Not causal diagnosis, code repair, broad unknown-repository locating or Coordinator qualification.",
            "roles": "Explorer only; no Coder handoff or model-provided plan",
            "continue_rule": "Fixed order even on ordinary report failure; safety/infra/time/weekly50 stop",
            "offline_basis": "Same installed runtime passed 82 Explorer controls in explorer-install-20261020-1; no new runtime changes",
        },
    )
    print("Four read-only navigation controls frozen; no live calls")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare()
    else:
        E.run(args.cell, args.weekly_used, args.observed_at, batch=BATCH)
