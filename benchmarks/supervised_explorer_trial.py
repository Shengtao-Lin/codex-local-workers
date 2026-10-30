"""Independent read-only locating qualification; no Coder success can erase it."""

import argparse
import shutil
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T

BATCH = S.KIT / "benchmarks/work/harness-convergence/supervised-explorer-20261019-1"
SOURCE = Path("F:/ChatGPT/agent-evaluation-harness")
SEED = (
    S.KIT
    / "benchmarks/work/harness-convergence/function-normal-repeat-20261019-1/cells/request_keys-1/isolated"
)
ORDER = ["raw-1", "fingerprint-1", "fingerprint-2", "raw-2"]
QUESTIONS = {
    "raw": "Locate where malformed JSON and valid non-object trace payloads are rejected in the adapters, and how a concrete adapter reaches this check. Give exact source/line evidence and a relevant existing adapter test; distinguish test coverage you actually read from inferred coverage. Read-only investigation, no implementation.",
    "fingerprint": "Locate how the content fingerprint excludes volatile sample fields while retaining content, and find the existing test that demonstrates this behavior. Give real source/line evidence for the exclusion rule, serialization path and test; do not confuse sample ID generation with content fingerprinting. Read-only investigation.",
}


def prepare():
    paths = [
        "src/evaluation_harness/adapters/common.py",
        "src/evaluation_harness/adapters/base.py",
        "src/evaluation_harness/adapters/generic_otel.py",
        "src/evaluation_harness/adapters/agent_runtime_kit.py",
        "src/evaluation_harness/adapters/registry.py",
        "src/evaluation_harness/canonical/fingerprint.py",
        "src/evaluation_harness/canonical/models.py",
        "src/evaluation_harness/trace_sources/base.py",
        "tests/unit/test_adapters.py",
        "tests/unit/test_canonical.py",
        "tests/conftest.py",
        "tests/fixtures/synthetic_traces/generic_multi_turn.json",
        "tests/fixtures/synthetic_traces/runtime_kit.json",
    ]
    rows = {}
    for cell in ORDER:
        root = BATCH / "cells" / cell
        root.mkdir(parents=True, exist_ok=False)
        for name in paths:
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / name, dest)
        shutil.copytree(SEED / ".local-agents", root / ".local-agents")
        config = S.read(SEED / ".agent/config.json")
        S.save(root / ".agent/config.json", config)
        rows[cell] = {
            "root": str(root),
            "question": QUESTIONS[cell.rsplit("-", 1)[0]],
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
            "cells": rows,
            "registered": 4,
            "weekly_stop": 40,
            "model": "openai/gpt-oss-20b",
            "context": 32768,
            "single_residency": True,
            "budget": {
                "turns": 16,
                "reads": 8,
                "searches": 10,
                "protocol_errors": 6,
                "invocation_seconds": 600,
            },
            "gate": "4/4 actual locating answers with correct real source/test citations; no false test coverage claim; no protected changes",
            "scope": "two frozen research questions, not arbitrary repository qualification",
            "continue": "ordinary quality failure recorded, complete four; stop safety/infra/40%",
            "cost": "Primary selected frozen corpus and questions; source not executed; no hints delivered during run",
        },
    )
    print("Four Explorer cells prepared, no model calls")


def run(cell, used, observed, batch=BATCH):
    BATCH = Path(batch).resolve()
    if not 0 <= used < 40 or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh weekly observation required")
    registration = S.read(BATCH / "registration.json")
    for earlier in ORDER[: ORDER.index(cell)]:
        if S.read(BATCH / "results" / earlier / "process.json")["stop_batch"]:
            raise ValueError("Earlier infrastructure/safety stop")
    row = registration["cells"][cell]
    root = Path(row["root"])
    if any(S.sha(root / p) != digest for p, digest in row["files"].items()):
        raise ValueError("Input drift")
    S.save(
        BATCH / "results" / cell / "start.json",
        {"weekly_used": used, "observed_at": observed},
    )
    argv = [
        S.PYTHON,
        "-B",
        root / ".local-agents/local-explore.py",
        "--task",
        row["question"],
        "--task-id",
        "supervised-explorer-" + cell,
        "--config",
        root / ".agent/config.json",
        "--report",
        root / ".agent/explorer.json",
        "--full-report",
    ]
    start = time.monotonic()
    result = T.run(argv, root, timeout=1200)
    report = (
        S.read(root / ".agent/explorer.json")
        if (root / ".agent/explorer.json").exists()
        else {}
    )
    drift = [p for p, digest in row["files"].items() if S.sha(root / p) != digest]
    result.update(
        seconds=time.monotonic() - start,
        protected_drift=drift,
        stop_batch=bool(drift) or bool(report.get("infra_failure")) or not report,
    )
    S.save(BATCH / "results" / cell / "process.json", result)
    print(cell, report.get("status"), "; semantic Primary verification still required")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    prepare() if args.mode == "prepare" else run(
        args.cell, args.weekly_used, args.observed_at
    )
