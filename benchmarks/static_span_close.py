"""Close fixed formal batch after Primary rejects a source-backed regression."""

import argparse
import json
from pathlib import Path

import static_span_trial as S

T, BATCH = S.T, S.BATCH


def close(used):
    rows = T.read(BATCH / "cells.json")
    grid = []
    for name in S.ORDER:
        row = rows[name]
        root = Path(row["root"])
        cell = root.parent
        if not (cell / "result.json").exists():
            assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
            grid.append(
                {
                    "case": name,
                    "status": "NOT_RUN",
                    "reason": "New3/3 unreachable after confirmed Primary contract violation",
                }
            )
            continue
        result = T.read(cell / "result.json")
        packet = T.read(root / ".agent/packet.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        primary = T.read(archive / "review.json")
        assert primary["decision"] == "replan"
        T.save(
            cell / "primary-decision.json",
            {
                "decision": primary["decision"],
                "canonical_review": str(archive / "review.json"),
                "sha256": T.sha(archive / "review.json"),
                "semantic_takeover": False,
            },
        )
        wires = [
            T.read(p)["body"]
            for p in sorted((cell / "wire").glob("*-request.json"))
            if T.read(p)["url"].endswith("/chat/completions")
        ]
        grid.append(
            {
                "case": name,
                **result,
                "primary_decision": "replan",
                "model_requests": {
                    model: sum(w["model"] == model for w in wires)
                    for model in ("qwen/qwen3-coder-30b", "meta/muse-glimmer")
                },
                "runtime_validation_attempts": len(
                    list(archive.glob("validation-attempt-*.json"))
                ),
                "finding": "PRIMARY-METADATA-CYCLE-1"
                if name.startswith("new-")
                else "static_checks_failed",
            }
        )
    assert len([g for g in grid if g.get("status") == "NOT_RUN"]) == 4
    pins = T.read(BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    baseline = T.read(BATCH / "baseline.json")
    permitted = {
        "benchmarks/coder_static_span.py",
        "benchmarks/static_span_coder_entry.py",
        "benchmarks/static_span_unit_entry.py",
        "benchmarks/static_span_trial.py",
        "tests/test_static_span_formal.py",
        "docs/local-model-harness-convergence-plan.md",
    }
    drift = [
        p
        for p, sha in baseline["files"].items()
        if p not in permitted and T.sha(S.KIT / p) != sha
    ]
    assert not drift
    T.save(BATCH / "grid-results.json", grid)
    T.save(
        BATCH / "preservation.json",
        {
            "inherited_drift": drift,
            "all_pins_unchanged": True,
            "remaining4_inputs_unchanged": True,
            "production_runtime_modified": False,
            "siblings": "read-only",
            "commit_push": False,
        },
    )
    T.save(
        BATCH / "metrics.json",
        {
            "registered": 6,
            "executed": 2,
            "not_run": 4,
            "coder_validated_units": 1,
            "reviewer_started": 1,
            "reviewer_pass_reports": 1,
            "primary_accepted": 0,
            "primary_confirmed_reviewer_miss": 1,
            "model_requests": {
                model: sum(g.get("model_requests", {}).get(model, 0) for g in grid)
                for model in ("qwen/qwen3-coder-30b", "meta/muse-glimmer")
            },
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "weekly_used_start": 3,
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
        },
    )
    T.save(
        BATCH / "decision.json",
        {
            "status": "HOLD_PRIMARY_CONTRACT_REGRESSION",
            "registered": 6,
            "executed": 2,
            "not_run": 4,
            "goal_complete": False,
            "product_release": False,
            "conditional_migration_allowed": False,
            "conclusion": "Formal span routing, actual validation and automatic qualified Reviewer all executed. Reviewer passed, but Primary reproduced cyclic metadata regression ValueError->RecursionError in both dict/list cycles. Fixed3/3 is unreachable; no further cells or migration.",
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
            "next_action": "Ordinary isolated defect rework under the identical frozen harness, same original contract plus read-only regression derived from the confirmed defect. New results remain recovery evidence, never rewrite this gate or old failures.",
        },
    )
    print(json.dumps(T.read(BATCH / "decision.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
