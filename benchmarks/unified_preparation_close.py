"""Primary index and append-only mechanical qualification closeout."""

import argparse
import json
from pathlib import Path

import unified_preparation_trial as U

T, BATCH = U.T, U.BATCH


def index(name):
    root = Path(T.read(BATCH / "cells.json")[name]["root"])
    packet = T.read(root / ".agent/packet.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    review = T.read(archive / "review.json")
    if review["decision"] == "accept":
        assert T.read(root.parent / "result.json")["eligible_for_primary"]
        assert T.read(root.parent / "independent-full-check.json")["exit_code"] == 0
        assert T.read(root.parent / "reviewer.json")["decision"] == "pass_to_primary"
    T.save(root.parent / "primary-decision.json", {"decision": review["decision"],
        "canonical_review": str(archive / "review.json"), "sha256": T.sha(archive / "review.json"),
        "semantic_takeover": False, "qualification": "Exposed recovery unit, not fresh transfer"})


def close(used):
    rows = T.read(BATCH / "cells.json")
    grid = []
    for name in U.ORDER:
        root = Path(rows[name]["root"])
        cell = root.parent
        if not (cell / "result.json").exists():
            assert all(T.sha(root / p) == sha for p, sha in rows[name]["files"].items())
            grid.append({"case": name, "status": "NOT_RUN"})
            continue
        packet = T.read(root / ".agent/packet.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        if not (archive / "review.json").exists():
            record = U.R.S.D.S.O.M.command([U.R.S.D.S.O.M.PYTHON, "-B", root / ".local-agents/record-review.py",
                "--repo", root, "--task-id", packet["task_id"], "--run-id", packet["run_id"],
                "--decision", "replan", "--summary", "Fixed mechanical baseline did not pass validation; preserve failed checks and drafts, no takeover or acceptance."], root)
            assert record["exit_code"] == 0, record
        if not (cell / "primary-decision.json").exists():
            index(name)
        decision = T.read(cell / "primary-decision.json")["decision"]
        coder_requests = len(list(archive.glob("proposal-response-*.json")))
        attempts = len(list(archive.glob("validation-attempt-*.json")))
        wires = [T.read(p)["body"] for p in sorted((cell / "wire").glob("*-request.json"))
                 if T.read(p)["url"].endswith("/chat/completions")]
        if name.startswith("new-") and decision == "accept":
            assert attempts == 3 and coder_requests == 2
            receipt = T.read(archive / "unified-format-preparation.json")
            assert receipt["validation_count_before"] == receipt["validation_count_after"] == 1
            assert T.read(archive / "static-span-route-2.json")["mode"] == "span"
        grid.append({"case": name, **T.read(cell / "result.json"), "primary_decision": decision,
            "independent_full_exit": T.read(cell / "independent-full-check.json")["exit_code"],
            "coder_requests": coder_requests, "validation_attempts": attempts,
            "reviewer_requests": sum(w["model"] == "meta/muse-glimmer" for w in wires),
            "canonical_archive": str(archive)})
    for repeat in (1, 2, 3):
        a, b = [T.read(Path(rows[f"{arm}-{repeat}"]["root"]) / ".agent/packet.json") for arm in ("old", "new")]
        a.pop("run_id"), b.pop("run_id")
        assert a == b
        a, b = [T.read(Path(rows[f"{arm}-{repeat}"]["root"]) / ".agent/config.json") for arm in ("old", "new")]
        a.pop("experimental_unified_preparation"), b.pop("experimental_unified_preparation")
        assert a == b
    pins = T.read(BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    baseline = T.read(BATCH / "baseline.json")
    permitted = {"benchmarks/coder_unified_preparation.py", "benchmarks/unified_coder_entry.py",
                 "benchmarks/unified_unit_entry.py", "benchmarks/unified_preparation_trial.py",
                 "tests/test_unified_preparation.py", "docs/local-model-harness-convergence-plan.md"}
    drift = [p for p, sha in baseline["files"].items() if p not in permitted and T.sha(U.KIT / p) != sha]
    assert not drift
    accepted = sum(g.get("primary_decision") == "accept" and g["case"].startswith("new-") for g in grid)
    qualified = accepted == 3
    T.save(BATCH / "grid-results.json", grid)
    T.save(BATCH / "preservation.json", {"inherited_drift": drift, "old_and_new_pins_match": True,
        "paired_contracts_and_configs_verified": True, "production_changes": False,
        "siblings": "read-only", "commit_push": False})
    T.save(BATCH / "decision.json", {"status": "PASS_EXPOSED_FORMAL_RECOVERY" if qualified else "HOLD_FORMAL_RECOVERY",
        "registered": 6, "executed": sum(g.get("status") != "NOT_RUN" for g in grid),
        "new_accepted": accepted, "new_required": 3, "fresh_transfer_credit": False,
        "goal_complete": False, "product_release": False, "conditional_migration_allowed": qualified,
        "weekly_used_end": used, "weekly_used_ceiling": 15,
        "next_action": "Independently freeze three unexposed normal implementation units, two repeats/two arms, same candidate/Reviewer and original6/6 gate" if qualified else "Analyze retained failure without changing this closed denominator"})
    print(json.dumps(T.read(BATCH / "decision.json")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["index", "close"])
    parser.add_argument("--case")
    parser.add_argument("--used", type=int, default=3)
    args = parser.parse_args()
    index(args.case) if args.action == "index" else close(args.used)
