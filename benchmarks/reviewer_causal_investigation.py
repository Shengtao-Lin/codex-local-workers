"""Two new focused investigations on frozen exposed families; no Coder calls."""

import shutil
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import explorer_trace_trial as E
import reviewer_bounded_trial as R
import reviewer_locator_trial as L

BATCH = (
    S.KIT / "benchmarks/work/harness-convergence/reviewer-causal-evidence-20261020-2"
)
ORDER = ["defect", "false-positive"]


def prepare():
    assert S.read(L.BATCH / "decision.json")["gate_met"] is False
    rows = {}
    for label, old_cell in (
        ("defect", "defect-1"),
        ("false-positive", "false-positive-1"),
    ):
        original = R.source(old_cell)
        origin, root = Path(original["root"]), BATCH / "cells" / label / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name in original["files"]:
            if name.startswith((".agent/", "acceptance/")):
                continue
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin / name, dest)
        packet = S.read(origin / ".agent/packet.json")
        target = original["target"]
        tests = packet["focused_tests"]
        config = S.read(E.BATCH / "isolated/.agent/config.json")
        assert config["explorer_model"] == "openai/gpt-oss-20b"
        config.update(
            explorer_mode="investigate",
            explorer_answer_protocol=False,
            explorer_required_citation_paths=[target, *tests],
        )
        S.save(root / ".agent/config.json", config)
        report = S.read(origin / ".agent/reviewer-report.json")
        line = report["findings"][0]["line"]
        question = (
            "One read-only question: does the current named implementation satisfy the unchanged hard contract below, "
            "or is there a concrete source-backed discrepancy? An untrusted prior report flagged "
            + target
            + ":"
            + str(line)
            + "; do not assume this suspicion is correct. "
            "Read the implementation and actual focused tests, trace a concrete example if a discrepancy is supported; "
            "otherwise state that no defect is demonstrated. Cite actual read source/test ranges, separate evidence from hypothesis. "
            "No implementation, test changes or execution claims. Do not infer correctness merely from passing tests. "
            "Likely focused tests: "
            + ", ".join(tests)
            + ". Hard contract: "
            + "\n".join(item["text"] for item in packet["required_behavior"])
        )
        rows[label] = {
            "root": str(root),
            "target": target,
            "question": question,
            "original_cell": old_cell,
            "source_sha256": S.sha(root / target),
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
            },
        }
    S.save(
        BATCH / "registration.json",
        {
            "registered": 2,
            "order": ORDER,
            "cells": rows,
            "weekly_stop": 50,
            "batch_seconds": 3600,
            "per_call_seconds": 600,
            "turns": 16,
            "reads": 8,
            "searches": 10,
            "errors": 6,
            "context_length": 32768,
            "model": "openai/gpt-oss-20b",
            "single_residency": True,
            "scope": "Two exposed contracts, one investigation each. No original diagnosis/fix/hidden tests/reference patch supplied; only unchanged contract, current source/tests and reported location.",
            "gate": "Both focal conclusions must be independently correct with actually read source evidence. Optional prose/line errors recorded separately, not hidden. No Coder or product credit. Any ordinary failure closes diagnostic HOLD, no revised-question retries.",
            "conditional_next": "Only if both evidence-qualified may prepare a separate local-note-assisted Coder transfer; this registration itself authorizes no Coder rerun.",
            "pins": {str(Path(__file__).resolve()): S.sha(__file__)},
        },
    )
    print("Two read-only investigations frozen; Coder NOT_RUN")


def run(label, used, observed, *, batch=BATCH):
    BATCH = Path(batch)
    assert 0 <= used < 50 and 0 <= time.time() - observed <= 120
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    for earlier in reg["order"][: reg["order"].index(label)]:
        assert not S.read(BATCH / "results" / earlier / "process.json")["stop_batch"]
    row = reg["cells"][label]
    root = Path(row["root"])
    assert all(S.sha(root / p) == h for p, h in row["files"].items())
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = 3600 - (time.time() - S.read(clock)["epoch"])
    assert remaining > 0
    S.save(
        BATCH / "results" / label / "start.json",
        {"weekly_used": used, "observed_at": observed},
    )
    started = time.monotonic()
    process = T.run(
        [
            S.PYTHON,
            "-B",
            root / ".local-agents/local-explore.py",
            "--task",
            row["question"],
            "--task-id",
            BATCH.name + "-" + label,
            "--config",
            root / ".agent/config.json",
            "--report",
            root / ".agent/explorer.json",
            "--full-report",
        ],
        root,
        timeout=min(1200, remaining),
    )
    report = S.read(root / ".agent/explorer.json")
    drift = [p for p, h in row["files"].items() if S.sha(root / p) != h]
    process.update(
        seconds=time.monotonic() - started,
        status=report.get("status"),
        protected_drift=drift,
        stop_batch=bool(drift or report.get("infra_failure")),
    )
    S.save(BATCH / "results" / label / "process.json", process)
    print(label, report.get("status"), "Independent causal adjudication pending")
