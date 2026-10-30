"""Known-task migration through the product installer, without runtime patching."""

import argparse
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import installed_real_trial as R
import installed_scope_trial as I
import normal_task_trial as N
import stable_execution_tasks as TASKS

BATCH=I.BASE / "packaged-profile-live-20261022-1"
ORDER=["binding-1","hash-1","collector-1","collector-2","hash-2","binding-2"]
CONTROLS=I.BASE / "packaged-flat-profile-20261022-1/controls.xml"


def prepare(used):
    assert not BATCH.exists()
    cases=list(ET.parse(CONTROLS).iter("testcase"))
    assert len(cases)==44 and not any(c.find(t) is not None for c in cases for t in ("failure","error","skipped"))
    original_save,original_refresh=S.save,I.refresh_material
    def refresh(root,config):
        original_refresh(root,config)
        config.update(bounded_compatibility_profile="flat-v1",model_load_ack_policy="api_verified")
    def save(path,value):
        path=Path(path)
        if path.name=="reference.json" and "full-chain-replay" in path.parts:
            value=[{"kind":"replacement","content":v["replacement"]} for v in value]
        if path==BATCH / "registration.json":
            value.update(registered=6,weekly_stop=60,candidate="Unmodified product installer + explicit bounded_compatibility_profile flat-v1 and model_load_ack_policy api_verified; no experiment runtime patching",gate="6/6 independent complete accepts, each known task2/2; no drift, assisted credit or false acceptance",exposure="All tasks exposed from stable-execution-ab matrix; this is installed-profile migration regression, not new semantic transfer",continue_rule="Ordinary failure HOLD and finish six fixed cells; infrastructure/safety/drift/deadline/weekly60 stops",role_boundary="Coder Qwen/fresh Muse Reviewer; no Explorer/Coordinator credit; ASCII/unconfirmed semantic rework remain unqualified")
            for p in (Path(__file__),Path(TASKS.__file__),CONTROLS):
                value["pins"][str(p)]=S.sha(p)
        original_save(path,value)
    R.BATCH,R.ORDER,R.TASKS=BATCH,ORDER,TASKS.tasks(R.T.extract)
    I.refresh_material,S.save=refresh,save
    try:
        original_save(BATCH / "baseline.json",{"production":{str(p):S.sha(p) for p in (S.KIT / ".local-agents").rglob("*") if p.is_file() and "__pycache__" not in p.parts},"weekly_used":used,"weekly_stop":60})
        R.prepare(used)
    finally:
        I.refresh_material,S.save=original_refresh,original_save
    print("Six product-installed regression cells frozen; no runtime file patch")


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
        N.run(a.cell,a.weekly_used,a.observed_at or time.time(),batch=BATCH,order=ORDER,build_command=I.command,usage_limit=60,batch_seconds=10800)
