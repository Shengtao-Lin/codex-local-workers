"""Blinded known-behavior review controls; no feature acceptance or Coder credit."""

import argparse
import json
import os
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import installed_scope_trial as I
import packaged_profile_trial as P
import stable_execution_tasks as TASKS

BATCH=I.BASE / "reviewer-profile-screen-20261022-1"
ORDER=["hash-1","binding-1","collector-1"]


def prepare(used):
    assert not BATCH.exists()
    original=S.save
    pending={}
    def save(path,value):
        if Path(path)==BATCH / "registration.json":
            pending["registration"]=value
        else:
            original(path,value)
    P.BATCH,P.ORDER=BATCH,ORDER
    S.save=save
    try:
        P.prepare(used)
    finally:
        S.save=original
    cells=S.read(BATCH / "cells.json")
    specs=TASKS.tasks(T.extract)
    expected={"hash-1":"rework","binding-1":"pass_to_primary","collector-1":"rework"}
    controls={}
    for cell,row in cells.items():
        topic=row["topic"]
        source=specs[topic]["reference"]
        if topic=="hash":
            old='None if source_revision == "" else source_revision'
            assert source.count(old)==1
            source=source.replace(old,'None if not source_revision or not source_revision.strip() else source_revision')
        elif topic=="collector":
            old='if application.get("enabled") is not True:'
            assert source.count(old)==1
            source=source.replace(old,'if not application.get("enabled"):')
        root=Path(row["root"])
        replay=BATCH / "oracle" / (cell+"-proposal.json")
        S.save(replay,[{"kind":"replacement","content":source}])
        result=T.run(I.command(root,replay=replay),root,timeout=180)
        S.save(BATCH / "offline" / (cell+".json"),result)
        assert result["exit_code"]==0,result
        report=S.read(root / ".agent/unit-report.json")
        assert report["consolidated_harness"]["actual"]["model_requests"]==0
        assert report["status"]=="validation_passed_pending_review"
        private=T.run([S.PYTHON,"-B","-m","pytest","-q","tests",row["private_tests"]],root)
        S.save(BATCH / "oracle" / (cell+"-checks.json"),private)
        assert (private["exit_code"]==0)==(topic=="binding")
        identity=row["identity"]["run_id"]
        run=root / ".agent/tasks" / identity / "runs" / identity
        request=S.read(run / "review-request.json")
        request["review_id"]="screen-"+identity
        S.save(root / ".agent/screen-request.json",request)
        controls[cell]={"source_sha256":S.sha(root / row["target"]),"config_sha256":S.sha(run / "review-config.json"),"request_sha256":S.sha(root / ".agent/screen-request.json")}
    S.save(BATCH / "oracle.json",{"expected":expected,"reason":{"hash-1":"Nonempty whitespace revision incorrectly normalizes to None","binding-1":"Correct implementation","collector-1":"Truthy non-True enabled accepted"},"Worker_access":"Oracle/proposals/private checks outside approved read roots; no expected verdict or hidden failure forwarded"})
    S.save(BATCH / "controls.json",controls)
    reg=pending["registration"]
    reg.update(registered=3,gate="Correct positive pass1/1 and source-backed true implementation-defect rework2/2; no semantic resampling",candidate="Unchanged packaged flat-v1 fresh Reviewer on authentic current archives from scripted draft application",scope="Reviewer semantic diagnostic only; Coder model calls0; no feature acceptance or general unknown-boundary claim",continue_rule="Complete three valid semantic outcomes; infrastructure/safety/weekly60 stop; each first valid verdict final")
    for path in (Path(__file__),BATCH / "oracle.json",BATCH / "controls.json"):
        reg["pins"][str(path)]=S.sha(path)
    S.save(BATCH / "registration.json",reg)
    print("Three blinded Reviewer controls frozen after actual checks")


def run(cell,used,observed):
    assert 0<=used<60 and 0<=time.time()-observed<=120
    reg=S.read(BATCH / "registration.json")
    assert all(S.sha(p)==h for p,h in reg["pins"].items())
    row=S.read(BATCH / "cells.json")[cell]
    root=Path(row["root"])
    identity=row["identity"]["run_id"]
    controls=S.read(BATCH / "controls.json")[cell]
    assert S.sha(root / row["target"])==controls["source_sha256"]
    run=root / ".agent/tasks" / identity / "runs" / identity
    S.save(BATCH / "live-results" / cell / "start.json",{"weekly_used":used,"observed_at":observed})
    result=T.run([S.PYTHON,"-B",root / ".local-agents/local-bounded-review.py","--request",root / ".agent/screen-request.json","--config",run / "review-config.json","--report",root / ".agent/screen-review.json"],root,timeout=960)
    S.save(BATCH / "live-results" / cell / "process.json",result)
    report=S.read(root / ".agent/screen-review.json")
    assert S.sha(root / row["target"])==controls["source_sha256"]
    S.save(BATCH / "live-results" / cell / "result.json",{"decision":report.get("decision"),"report_path":str(root / ".agent/screen-review.json"),"Primary_assessment":"pending","feature_acceptance":False})
    print(cell,report.get("decision"),"Primary semantic confirmation pending")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("prepare","run"))
    p.add_argument("--cell",choices=ORDER)
    p.add_argument("--weekly-used",type=int,required=True)
    p.add_argument("--observed-at",type=float)
    a=p.parse_args()
    os.environ["PYTHONIOENCODING"]="utf-8"
    if a.mode=="prepare":
        prepare(a.weekly_used)
    else:
        run(a.cell,a.weekly_used,a.observed_at or time.time())
