"""Record completed Primary source/diff reviews and close the frozen A/B batch."""

from pathlib import Path

import bounded_evidence_support as S
import stable_execution_trial as B
import supervised_record as PRIMARY

REASONS = {
    "binding": "Primary inspected this cell's full source and cumulative diff: environment query omitted only for exact empty string; workspace first, application quote(safe='') and nonempty environment values preserved. Independent encoding/empty-field tests and strict profile pass; fresh Reviewer has no findings. No runtime hints or takeover.",
    "hash": "Primary inspected this cell's full make_sample_id source and cumulative diff: only empty source_revision becomes None, other strings and turn_index remain unchanged, all identity fields/defaults and read-only canonical_json SHA256/smp_ format preserved. Independent revision/turn matrix and strict profile pass; fresh Reviewer has no findings. No runtime hints or takeover.",
    "collector": "Primary inspected this cell's full source and cumulative diff: nonempty identity, exact application matching, enabled is True and original ASCII regex preserved. New two-key output encodes each identity value with quote(safe='') in required resource-attribute order, without mutating application. Independent legacy-rejection/encoding tests and strict profile pass; fresh Reviewer has no findings. No runtime hints or takeover.",
}


def main():
    batch = B.BATCH
    reg = S.read(batch / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    cells = S.read(batch / "cells.json")
    results = []
    for cell in B.ORDER:
        row = cells[cell]
        result = S.read(batch / "live-results" / cell / "result.json")
        assert result["all_independent_pass"] and not result["stop_batch"]
        assert not result["protected_drift"] and not result["assisted"]
        if not (batch / "primary" / cell / "primary.json").exists():
            PRIMARY.record(cell, REASONS[row["topic"]], batch=batch)
        root = Path(row["root"])
        identity = row["identity"]["run_id"]
        reviewer = S.read(root / ".agent/tasks" / identity / "reviews" / ("auto-" + identity) / "contract-first-budget.json")
        results.append({"cell":cell,"arm":cell.split("-")[1][0],"primary":"accept","coder":result["ledger"]["actual"],"reviewer_requests":reviewer["actual_requests"],"seconds":result["seconds"]})
    baseline = S.read(batch / "baseline.json")
    assert not [p for p,h in baseline["production"].items() if S.sha(p) != h]
    assert not [p for p,h in baseline["historical_decisions"].items() if S.sha(p) != h]
    origins = S.read(batch / "origins.json")
    assert all(S.sha(row["path"]) == row["sha256"] for row in origins.values())
    arms = {a:{"executed":6,"accepted":6,"requests":sum(r["coder"]["requests"] for r in results if r["arm"]==a),"edits":sum(r["coder"]["edits"] for r in results if r["arm"]==a),"protocol_recoveries":sum(r["coder"]["protocol_recoveries"] for r in results if r["arm"]==a)} for a in ("A","B")}
    S.save(batch / "metrics.json", {"registered":12,"executed":12,"accepted":12,"arms":arms,"rows":results,"unit_seconds":sum(r["seconds"] for r in results),"assisted":0,"takeovers":0,"cloud_tokens":"unknown","Primary_active_seconds":"unknown","Reviewer_defect_detection":"not measured in this all-correct batch","preservation":"production, upstream source, historical decisions and protected inputs unchanged"})
    decision = {"status":"PASS_FIXED_MATRIX_NO_FEEDBACK_ADOPTION","gate":"12/12 complete independent accepts","finding":"A6/6 and B6/6; every Coder one request/one edit. No protocol recovery occurred, so live feedback benefit is unmeasured. Prefer original decoder as execution baseline; keep specific feedback opt-in for diagnostic recovery testing.","scope":"Three frozen requested local changes, two repeats per arm; prelocated source and Primary-authored tests/contracts. Not broad E/C/R or Coordinator release, no economic proof.","next":"Independent recovery controls and Reviewer-to-Coder boundary; retain old1/3 and4/4-regression records.","production_enabled":False}
    S.save(batch / "decision.json", decision)
    S.save(batch / "handoff.json", {**decision,"metrics":"metrics.json","registration":"registration.json","weekly_stop":60,"roles":{"Coder":"qwen/qwen3-coder-30b","Reviewer":"meta/muse-glimmer","Explorer":"NOT_RUN: prelocated sources","Coordinator":"NOT_RUN"}})
    print("Closed:12/12 complete accepts; A6/6 B6/6, feedback benefit unmeasured")


if __name__ == "__main__":
    main()
