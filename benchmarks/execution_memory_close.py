"""Close the fixed diagnostic without granting full-chain acceptance."""

import argparse
from pathlib import Path

import bounded_evidence_support as S
import execution_memory_trial as R


def close(used):
    cells = S.read(R.BATCH / "cells.json")
    outcomes = []
    arms = {
        arm: {
            "executed": 0,
            "independent_checks_pass": 0,
            "requests": 0,
            "edits": 0,
            "noops": 0,
            "seconds": 0.0,
            "continuations": 0,
        }
        for arm in ("A", "B")
    }
    for cell in R.ORDER:
        result = S.read(R.BATCH / "live-results" / cell / "result.json")
        if result["stop_batch"]:
            raise ValueError("Use infrastructure-specific closure instead")
        arm = cell.split("-")[1]
        root = Path(cells[cell]["root"])
        report = S.read(root / ".agent/unit-report.json")
        counts = report["consolidated_harness"]["actual"]
        state = arms[arm]
        state["executed"] += 1
        state["independent_checks_pass"] += int(result["all_independent_pass"])
        for k in ("requests", "edits", "noops"):
            state[k] += counts[k]
        state["seconds"] += result["seconds"]
        state["continuations"] += max(0, counts["requests"] - 1)
        archive = (
            root
            / ".agent/tasks"
            / cells[cell]["identity"]["task_id"]
            / "runs"
            / cells[cell]["identity"]["run_id"]
        )
        outcomes.append(
            {
                "cell": cell,
                "coder_status": result["coder_status"],
                "independent_checks_pass": result["all_independent_pass"],
                "report_sha256": S.sha(root / ".agent/unit-report.json"),
                "diff_sha256": S.sha(archive / "cumulative.diff"),
                "reviewer": "NOT_RUN_DIAGNOSTIC",
                "final_acceptance": "NOT_RUN_DIAGNOSTIC",
                "assisted": False,
            }
        )
    base = S.read(R.BATCH / "baseline.json")["files"]
    drift = [
        p
        for p, digest in base.items()
        if p.startswith((".local-agents/", "AGENTS.md")) and S.sha(S.KIT / p) != digest
    ]
    if drift:
        raise ValueError("Pre-existing production changes drifted: " + repr(drift))
    S.save(
        R.BATCH / "metrics.json",
        {
            "arms": arms,
            "cells": outcomes,
            "protected_production_drift": drift,
            "weekly_used": used,
            "weekly_stop": 50,
            "Primary_takeovers": 0,
            "Primary_semantic_repair_hints": 0,
            "cloud_tokens": None,
            "Primary_active_seconds": None,
        },
    )
    S.save(
        R.BATCH / "decision.json",
        {
            "status": "NO_ADOPTION_COMPLETION_REGRESSION",
            "registered": 12,
            "executed": 12,
            "A": arms["A"],
            "B": arms["B"],
            "production_enabled": False,
            "finding": "B used fewer proposals but missed tuple traversal on json-B-1; current checks passed but independent checks caught it. A6/6 vs B5/6; adoption criterion not met. Memory was actually exercised on both B JSON repairs. No semantic hints or reruns.",
            "limits": "Exposed small paired repeats, no Reviewer/full-chain credit. Does not prove memory causes the omitted behavior or that all agent memory is harmful.",
            "next": "Do not adopt memory by default or tune it on these failures. Separately test existing approved read/search access on the consolidated host, keeping the no-memory static-focused candidate as A.",
            "weekly_used": used,
            "weekly_stop": 50,
        },
    )
    with (R.BATCH / "handoff.md").open("x", encoding="utf-8") as stream:
        stream.write(
            "# Host-observed continuity diagnostic\n\nFixed12 completed: A6/6 independent configured/private checks, B5/6. Reviewer and final full-chain acceptance were NOT_RUN, not12 releases.\n\nB reduced requests10→8 and edits10→8, but json-B-1 omitted tuple traversal; this is a completion/coverage failure caught by independent acceptance, not a Reviewer false pass. No hidden failure or reference implementation was fed back. No default adoption, no resampling. Raw archives and every failure retained.\n\nMemory helps preserve facts mechanically but did not establish greater reliability here. Next isolate approved evidence access on the same safety base, without stacking memory. Coordinator remains not admitted.\n"
        )
    print(arms)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--weekly-used", type=int, required=True)
    close(p.parse_args().weekly_used)
