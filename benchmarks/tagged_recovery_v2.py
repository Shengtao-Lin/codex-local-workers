"""Same flat-wire candidate; correct only offline reference-envelope preparation."""

import argparse
import os
import time
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import normal_task_trial as N
import tagged_recovery_trial as V

BATCH=I.BASE / "tagged-wire-recovery-20261022-2"


def prepare(used):
    original=S.save
    def save(path,value):
        path=Path(path)
        if path.name=="reference.json" and "full-chain-replay" in path.parts:
            value=[{"kind":"replacement","content":row["replacement"]} for row in value]
        if path==BATCH / "registration.json":
            value["pins"][str(Path(__file__))]=S.sha(__file__)
            value["preparation_lineage"]="Previous tagged-wire-recovery-20261022-1 had no Worker calls: old reference replay envelope rejected by intentionally new decoder. Only evaluator replay envelope corrected; candidate unchanged."
        original(path,value)
    V.BATCH=BATCH
    S.save=save
    try:
        V.prepare(used)
    finally:
        S.save=original


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
        N.run(a.cell,a.weekly_used,a.observed_at or time.time(),batch=BATCH,order=V.ORDER,build_command=I.command,usage_limit=60,batch_seconds=10800)
