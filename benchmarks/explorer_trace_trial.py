"""One existing-role causal TRACE, independent of Coder repair credit."""

import argparse
import shutil
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import mapping_recovery_trial as M

BATCH = S.KIT / "benchmarks/work/harness-convergence/explorer-trace-20261020-2"
QUESTION = "Investigate why tests/test_contract.py::test_all_mapping_keys_even_when_mapping_is_false fails against src/product/code.py. Trace the relevant control flow using actual source and test evidence; cite read file/line ranges and explain the causal discrepancy, not just the assertion message. Read-only research, no implementation or test changes; distinguish confirmed evidence from hypothesis."


def prepare():
    old = S.read(M.BATCH / "cells.json")["for-1"]
    root = BATCH / "isolated"
    root.mkdir(parents=True, exist_ok=False)
    for name, digest in old["files"].items():
        if name == ".agent/packet.json" or name.startswith("acceptance/"):
            continue
        source = Path(old["root"]) / name
        if S.sha(source) != digest:
            raise ValueError("Frozen unchanged failing draft drifted")
        if name == ".agent/config.json":
            continue
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    config = S.read(Path(old["root"]) / ".agent/config.json")
    config["explorer_mode"] = "investigate"
    config["explorer_answer_protocol"] = False
    config["explorer_required_citation_paths"] = [
        "src/product/code.py",
        "tests/test_contract.py",
    ]
    S.save(root / ".agent/config.json", config)
    S.save(
        BATCH / "registration.json",
        {
            "registered": 1,
        "mode": "existing investigate mode; answer_protocol false, original locate-only call retained separately",
            "root": str(root),
            "question": QUESTION,
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
            },
            "model": "openai/gpt-oss-20b",
            "context_length": 32768,
            "weekly_stop": 50,
            "single_residency": True,
            "budget": {
                "turns": 16,
                "reads": 8,
                "searches": 10,
                "errors": 6,
                "seconds": 600,
            },
            "gate": "One source-backed actual causal diagnosis; locating-only citations insufficient. No Coder/full-chain qualification. No hidden/private tests, answer or Primary fix supplied.",
            "scope": "New focused TRACE question on exposed frozen failure, not unseen-repository qualification; existing required citations safeguard unchanged.",
        },
    )
    print("One bounded causal TRACE frozen; no model calls")


def run(used, observed):
    if not 0 <= used < 50 or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh usage below50 required")
    reg = S.read(BATCH / "registration.json")
    root = Path(reg["root"])
    if any(S.sha(root / p) != h for p, h in reg["files"].items()):
        raise ValueError("Input drift")
    S.save(BATCH / "start.json", {"weekly_used": used, "observed_at": observed})
    start = time.monotonic()
    result = T.run(
        [
            S.PYTHON,
            "-B",
            root / ".local-agents/local-explore.py",
            "--task",
            QUESTION,
            "--task-id",
            BATCH.name,
            "--config",
            root / ".agent/config.json",
            "--report",
            root / ".agent/explorer.json",
            "--full-report",
        ],
        root,
        timeout=1200,
    )
    result["seconds"] = time.monotonic() - start
    result["protected_drift"] = [
        p for p, h in reg["files"].items() if S.sha(root / p) != h
    ]
    S.save(BATCH / "process.json", result)
    report = (
        S.read(root / ".agent/explorer.json")
        if (root / ".agent/explorer.json").exists()
        else {}
    )
    print(
        "Explorer", report.get("status"), "Primary causal/citation verification pending"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare"])
    p.parse_args()
    prepare()
