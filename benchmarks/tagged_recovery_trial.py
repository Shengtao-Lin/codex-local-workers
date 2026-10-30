"""Flat-schema compatibility repair; preserve the existing host and task contracts."""

import argparse
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import normal_task_trial as N
import schema_wire_probe as W
import stable_recovery_trial as D
import tagged_proposal_wire as C

BATCH=I.BASE / "tagged-wire-recovery-20261022-1"
WIRE=I.BASE / "schema-tagged-wire-20261022-1"
ORDER=["destination-1","message-1","message-2","destination-2"]
CONTROLS=I.BASE / "stable-execution-prep-20261021-1/tagged-controls.xml"


def wire(used):
    original_load,original_save=W.F.load,S.save
    def load(path,name):
        module=original_load(path,name)
        if name=="schema_probe_protocol":
            C.extend(vars(module))
        return module
    def save(path,value):
        if Path(path)==WIRE / "registration.json":
            value.update(weekly_used_start=used,schema_variant_labels={"union":"tagged flat kind/content candidate (legacy probe key)","flat":"single-field control"},candidate="Flat required kind/content; string enum plus string body, no oneOf",pins={**value["pins"],str(Path(C.__file__)):S.sha(C.__file__),str(Path(__file__)):S.sha(__file__)})
        original_save(path,value)
    W.BATCH=WIRE
    W.F.load,S.save=load,save
    try:
        W.main()
    finally:
        W.F.load,S.save=original_load,original_save


def prepare(used):
    assert not BATCH.exists() and S.read(WIRE / "decision.json")["valid"]==4
    controls=list(ET.parse(CONTROLS).iter("testcase"))
    assert len(controls)==10 and not any(c.find(t) is not None for c in controls for t in ("failure","error","skipped"))
    original_save,original_refresh=S.save,I.refresh_material
    def refresh(root,config):
        original_refresh(root,config)
        C.install(root)
    def save(path,value):
        if Path(path)==BATCH / "registration.json":
            value.update(candidate="Flat required kind/content schema normalized to unchanged host replacement/blocked_reason. System/phase text only updated for wire fields; no semantic advice, source privileges or budget changes.",gate="4/4 independent complete accepts, destination2/2 and message2/2, no safety drift; ordinary failure HOLD but finish registered diagnostics",hypothesis="Observed oneOf schema violations can be avoided with the provider-tested flat schema. Transport recovery and semantic completion reported separately.",scope="Exposed diagnostic repairs, not new algorithm discovery; original failed batches unchanged",prior_candidates="Specific field feedback1/2 and literal pytest0/2 remain HOLD. This candidate repairs independently observed wire-schema compatibility, not another semantic hint on the task.")
            for p in (Path(__file__),Path(C.__file__),WIRE / "decision.json",CONTROLS):
                value["pins"][str(p)]=S.sha(p)
        original_save(path,value)
    D.BATCH,D.ORDER=BATCH,ORDER
    I.refresh_material,S.save=refresh,save
    try:
        D.prepare(used)
    finally:
        I.refresh_material,S.save=original_refresh,original_save
    print("Four flat-schema recovery cells frozen")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("wire","prepare","run"))
    p.add_argument("--cell",choices=ORDER)
    p.add_argument("--weekly-used",type=int,required=True)
    p.add_argument("--observed-at",type=float)
    a=p.parse_args()
    os.environ["PYTHONIOENCODING"]="utf-8"
    if a.mode=="wire":
        wire(a.weekly_used)
    elif a.mode=="prepare":
        prepare(a.weekly_used)
    else:
        N.run(a.cell,a.weekly_used,a.observed_at or time.time(),batch=BATCH,order=ORDER,build_command=I.command,usage_limit=60,batch_seconds=10800)
