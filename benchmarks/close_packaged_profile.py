"""Close the installed migration and retain recoverable source-version lineage."""

from pathlib import Path

import bounded_evidence_support as S
import close_stable_execution as REASONS
import package_profile_checkpoint as CHECKPOINT
import packaged_profile_trial as P
import supervised_record as PRIMARY


def main():
    reg=S.read(P.BATCH / "registration.json")
    assert all(S.sha(path)==h for path,h in reg["pins"].items())
    cells=S.read(P.BATCH / "cells.json")
    rows=[]
    for cell in P.ORDER:
        row=cells[cell]
        result=S.read(P.BATCH / "live-results" / cell / "result.json")
        assert result["all_independent_pass"] and not result["stop_batch"]
        if not (P.BATCH / "primary" / cell / "primary.json").exists():
            PRIMARY.record(cell,REASONS.REASONS[row["topic"]],batch=P.BATCH)
        root=Path(row["root"])
        identity=row["identity"]["run_id"]
        review=S.read(root / ".agent/tasks" / identity / "reviews" / ("auto-"+identity) / "contract-first-budget.json")
        rows.append({"cell":cell,"accepted":True,"coder":result["ledger"]["actual"],"reviewer_requests":review["actual_requests"],"reviewer_protocol_errors":review["protocol_errors"],"seconds":result["seconds"]})
    before=S.read(CHECKPOINT.BATCH / "baseline.json")["preimages"]
    allowed={"AGENTS.md",".local-agents/README.md",".local-agents/host-proposal.md",".local-agents/local-bounded-unit.py",".local-agents/local-bounded-review.py",".local-agents/model_residency.py",".local-agents/worker-runtime.py"}
    changed=[p for p,h in before.items() if S.sha(S.KIT / p)!=h]
    assert set(changed)<=allowed
    assert all(S.sha(CHECKPOINT.BATCH / "preimages" / p)==before[p] for p in before)
    S.save(CHECKPOINT.BATCH / "source-lineage.json",{p:{"old_sha256":before[p],"new_sha256":S.sha(S.KIT / p),"preserved_at":str(CHECKPOINT.BATCH / "preimages" / p)} for p in changed})
    metrics={"registered":6,"executed":6,"accepted":6,"rows":rows,"coder_requests":sum(r["coder"]["requests"] for r in rows),"effective_edits":sum(r["coder"]["edits"] for r in rows),"coder_protocol_recoveries":sum(r["coder"]["protocol_recoveries"] for r in rows),"reviewer_requests":sum(r["reviewer_requests"] for r in rows),"reviewer_protocol_errors":sum(r["reviewer_protocol_errors"] for r in rows),"unit_seconds":sum(r["seconds"] for r in rows),"assisted":0,"takeovers":0,"cloud_tokens":"unknown","Primary_active_seconds":"unknown"}
    S.save(P.BATCH / "metrics.json",metrics)
    decision={"status":"PASS_FIXED_INSTALLED_PROFILE_MATRIX","accepted":6,"registered":6,"gate":reg["gate"],"scope":"Three known requested local task families, each2/2; actual installer/configuration path, not new holdout or broad production qualification","profile":"bounded_compatibility_profile flat-v1; model_load_ack_policy api_verified","default_config":"unchanged","semantic_boundaries":"ASCII repair and unconfirmed automatic semantic Reviewer rework remain unqualified; global Coordinator admission unchanged","history":"Old failures/preparation faults retained; source preimages and lineage record the shared code upgrade","economic_saving":"not established"}
    S.save(P.BATCH / "decision.json",decision)
    S.save(P.BATCH / "handoff.json",{**decision,"metrics":"metrics.json","registration":"registration.json","source_lineage":str(CHECKPOINT.BATCH / "source-lineage.json"),"weekly_stop":60})
    print("6/6 independent product-install accepts; defaults unchanged; bounded scope only")


if __name__=="__main__":
    main()
