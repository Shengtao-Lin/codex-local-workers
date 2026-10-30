"""One transport-only Reviewer recovery; no Coder rerun or report resampling."""

import os
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import tagged_recovery_v2 as V

BATCH=V.I.BASE / "reviewer-load-recovery-20261022-1"


def main():
    assert not BATCH.exists()
    row=S.read(V.BATCH / "cells.json")["message-2"]
    root=Path(row["root"])
    identity=row["identity"]
    old=S.read(root / ".agent/reviewer-report.json")
    assert old["infra_failure"]["reason_code"]=="model_switch_failed"
    run=root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
    previous=root / ".agent/tasks" / identity["task_id"] / "reviews" / ("auto-"+identity["run_id"])
    assert not list(previous.glob("phase-response-*.json"))
    assert S.read(V.BATCH / "live-results/message-2/result.json")["all_independent_pass"]
    request=S.read(run / "review-request.json")
    request["review_id"]="retry-"+identity["run_id"]
    request_path=root / ".agent/reviewer-load-recovery-request.json"
    S.save(request_path,request)
    before={str(p):S.sha(p) for p in (root / "src").rglob("*.py")}
    S.save(BATCH / "registration.json",{"authorization":"Approved autonomous infrastructure recovery; no original model review was attempted","identity":identity,"original_failure":old,"original_model_requests":0,"max_substantive_review_requests":16,"max_seconds":600,"reviewer":"meta/muse-glimmer","candidate":"Unchanged direct-report Reviewer","old_batch_stop_preserved":True,"scope":"One fresh-context transport recovery only; first valid semantic rework/escalation is final, no same-code PASS sampling","weekly_stop":60,"pins":{str(request_path):S.sha(request_path),str(run / "review-config.json"):S.sha(run / "review-config.json"),**before}})
    argv=[S.PYTHON,"-B",root / ".local-agents/local-bounded-review.py","--request",request_path,"--config",run / "review-config.json","--report",root / ".agent/reviewer-load-recovery.json"]
    started=time.monotonic()
    result=T.run(argv,root,timeout=960)
    S.save(BATCH / "process.json",result)
    report=S.read(root / ".agent/reviewer-load-recovery.json")
    assert all(S.sha(p)==h for p,h in before.items())
    S.save(BATCH / "decision.json",{"status":"REVIEW_TRANSPORT_RECOVERED" if report.get("decision") in ("pass_to_primary","rework","escalate") else "REVIEW_RECOVERY_FAILED","reviewer_decision":report.get("decision"),"seconds":time.monotonic()-started,"code_changed":False,"coder_rerun":False,"original_batch_score_unchanged":True,"Primary_acceptance":"pending"})
    print(report.get("decision"))


if __name__=="__main__":
    os.environ["PYTHONIOENCODING"]="utf-8"
    main()
