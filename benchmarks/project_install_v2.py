"""Same candidate/project task; fix only complete-package evidence preparation."""

import argparse
import json
import os
import shutil
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import installed_scope_trial as I
import normal_task_trial as N
import project_install_trial as V

BATCH=I.BASE / "project-live-20261022-2"


def prepare(used):
    original_material,original_save=V.F.install_material,S.save
    pending={}
    def material(root,identity,**kwargs):
        # Only enumerate already approved project source, not external packages.
        kwargs["source_paths"]=sorted(set(kwargs["source_paths"]) | {p.relative_to(root).as_posix() for p in (root / "src").rglob("*.py")})
        return original_material(root,identity,**kwargs)
    def save(path,value):
        if Path(path)==BATCH / "registration.json":
            pending["registration"]=value
        else:
            original_save(path,value)
    V.BATCH=BATCH
    V.F.install_material,S.save=material,save
    try:
        V.prepare(used)
    finally:
        V.F.install_material,S.save=original_material,original_save
    rows=S.read(BATCH / "cells.json")
    reference=T.extract(BATCH / "reference-project" / V.TARGET,"make_sample_id")
    proofs={}
    for cell,row in rows.items():
        root=BATCH / "offline" / cell / "isolated"
        shutil.copytree(row["root"],root)
        replay=root.parent / "reference.json"
        S.save(replay,[{"kind":"replacement","content":reference}])
        os.environ["PYTHONPATH"]=str(root / "src")
        os.environ["PYTEST_ADDOPTS"]="--basetemp="+str(root / ".agent/pytest-owned")
        result=T.run(I.command(root,replay=replay),root,timeout=300)
        S.save(root.parent / "process.json",result)
        assert result["exit_code"]==0,result
        proofs[cell]={"exit_code":0,"summary":S.read(root / ".agent/unit-summary.json"),"status":S.read(root / ".agent/unit-report.json")["status"]}
    row=rows[V.ORDER[0]]
    negative=BATCH / "offline/negative/isolated"
    shutil.copytree(row["root"],negative)
    policy_path=negative / V.F.POLICY_PATH
    policy=S.read(policy_path)
    omitted="src/evaluation_harness/__init__.py"
    assert omitted in policy["source_paths"]
    policy["source_paths"].remove(omitted)
    policy["readonly_hashes"].pop(omitted)
    policy_path.write_text(json.dumps(policy,indent=2),encoding="utf-8")
    os.environ["PYTHONPATH"]=str(negative / "src")
    result=T.run([S.PYTHON,"-B",negative / V.F.PRODUCER,"--policy",V.F.POLICY_PATH],negative)
    S.save(negative.parent / "process.json",result)
    assert result["exit_code"]!=0 and "unmanifested local import: evaluation_harness" in result["stderr"]
    S.save(BATCH / "offline-controls.json",{"positive":proofs,"negative_missing_package_entry":"rejected","worker_calls":0})
    reg=pending["registration"]
    reg["preparation_lineage"]="project-live-20261022-1 correctly rejected unmanifested package import; no acceptance. Same code candidate/contracts/tests, complete approved-source manifest and actual installed-unit replay now required."
    for p in (Path(__file__),BATCH / "offline-controls.json"):
        reg["pins"][str(p)]=S.sha(p)
    S.save(BATCH / "registration.json",reg)
    print("Full project import negative control and two installed full-unit replays passed")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("prepare","run"))
    p.add_argument("--cell",choices=V.ORDER)
    p.add_argument("--weekly-used",type=int,required=True)
    p.add_argument("--observed-at",type=float)
    a=p.parse_args()
    os.environ["PYTHONIOENCODING"]="utf-8"
    if a.mode=="prepare":
        prepare(a.weekly_used)
    else:
        root=Path(S.read(BATCH / "cells.json")[a.cell]["root"])
        os.environ["PYTHONPATH"]=str(root / "src")
        os.environ["PYTEST_ADDOPTS"]="--basetemp="+str(root / ".agent/pytest-owned")
        N.run(a.cell,a.weekly_used,a.observed_at or time.time(),batch=BATCH,order=V.ORDER,build_command=I.command,usage_limit=60,batch_seconds=10800)
