"""Close only explicitly Primary-reviewed recovery cells; never re-run workers."""

import argparse
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import installed_scope_trial as I
import supervised_record as PRIMARY


def close(batch, accepted):
    batch = I.BASE / batch
    reg, cells = S.read(batch / "registration.json"), S.read(batch / "cells.json")
    assert all(S.sha(p) == h for p,h in reg["pins"].items())
    rows = []
    for cell in reg["order"]:
        row = cells[cell]
        root = Path(row["root"])
        result = S.read(batch / "live-results" / cell / "result.json")
        assert not result["protected_drift"] and not result["interrupted"]
        if cell in accepted:
            assert result["all_independent_pass"] and result["summary"]["reviewer_decision"] == "pass_to_primary"
            if not (batch / "primary" / cell / "primary.json").exists():
                reason = (
                    "Primary read full destination source and cumulative diff: nonempty ASCII digit validation uses isascii with isdigit, original mismatch repr and missing-key behavior preserved, no mutation. Independent Unicode/leading-zero/compatibility tests and strict checks pass; fresh Reviewer has no findings. Exposed repair only; no semantic hints or takeover."
                )
                PRIMARY.record(cell, reason, batch=batch)
        else:
            assert not result["all_independent_pass"]
            identity = row["identity"]
            command = [S.PYTHON,"-B",root / ".local-agents/record-review.py","--repo",root,"--task-id",identity["task_id"],"--run-id",identity["run_id"],"--decision","replan","--summary","Primary inspected actual failed draft/diff: Unicode digit acceptance remains; retain validation/protocol/no-op failure, no feature acceptance or takeover.","--config",root / ".agent/config.json"]
            recorded = T.run(command, root)
            S.save(batch / "primary" / cell / "record-command.json", recorded)
            assert recorded["exit_code"] == 0, recorded
        rows.append({"cell":cell,"accepted":cell in accepted,"coder":result["coder_status"],"actual":result["ledger"]["actual"],"reviewer":result["summary"]["reviewer_decision"],"independent":result["all_independent_pass"],"seconds":result["seconds"]})
    before = S.read(batch / "baseline.json")["production"]
    assert not [p for p,h in before.items() if S.sha(p) != h]
    for source in reg["draft_origins"].values():
        assert S.sha(source["path"]) == source["sha256"]
    S.save(batch / "metrics.json", {"registered":reg["registered"],"executed":len(rows),"accepted":len(accepted),"rows":rows,"cloud_tokens":"unknown","Primary_active_seconds":"unknown","unit_seconds":sum(r["seconds"] for r in rows),"assisted":0,"takeovers":0,"production_enabled":False})
    passed = len(accepted) == len(rows)
    decision = {"status":"PASS_EXPOSED_REPAIR_BATCH" if passed else "HOLD_EXPOSED_REPAIR_BATCH","accepted":len(accepted),"executed":len(rows),"gate":reg["gate"],"scope":"Exposed failed-draft repairs; no general transfer or economic proof. Successful later cells do not erase failures.","semantic_reviewer_rework":"Unconfirmed automated Reviewer advice remains disabled; historical4/4 regressions retained","production_enabled":False}
    S.save(batch / "decision.json", decision)
    S.save(batch / "handoff.json", {**decision,"metrics":"metrics.json","registration":"registration.json","weekly_stop":60})
    print(batch.name, len(accepted), "/", len(rows), decision["status"])


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("batch")
    p.add_argument("--accepted", nargs="*", required=True)
    a=p.parse_args()
    close(a.batch,set(a.accepted))
