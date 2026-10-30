"""One concrete unanswered caller question on a copied actual project."""

import argparse
import os
import shutil
import tempfile
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import installed_scope_trial as I
import packaged_profile_trial as P
import project_snapshot_prepare as SNAP
from test_installable_bounded import INSTALL

BATCH=I.BASE / "packaged-explorer-20261022-1"
TASK="In src/evaluation_harness/adapters/common.py, when _sample calls make_sample_id, is source_revision passed unchanged from SourceTrace or normalized before the call? Trace that one value from the SourceTrace definition to the real call. Cite actual read file/lines for the field and call; cite a test only if you actually read it. Likely files are adapters/common.py and trace_sources/base.py. Read-only research; do not propose implementation or claim whole-feature acceptance."


def prepare(used):
    assert not BATCH.exists()
    root=BATCH / "isolated"
    shutil.copytree(SNAP.BATCH / "snapshot",root,ignore=shutil.ignore_patterns("__pycache__",".pytest_cache",".ruff_cache","*.pyc"))
    with tempfile.TemporaryDirectory(prefix="explorer-product-install-") as directory:
        stage=Path(directory)
        INSTALL.install(S.KIT,stage,apply=True)
        shutil.copytree(stage / ".local-agents",root / ".local-agents")
        shutil.copyfile(stage / "AGENTS.md",root / "AGENTS.md")
    config=S.read(Path(S.read(P.BATCH / "cells.json")["hash-1"]["root"]) / ".agent/config.json")
    S.save(root / ".local-agents/config.json",config)
    paths=[p for p in (root / "src").rglob("*.py")]+[root / "pyproject.toml"]
    S.save(BATCH / "registration.json",{"authorization":"Approved stage E read-only role integration","task_id":"packaged-revision-impact","feature_id":"revision-normalization-impact","feature_risk":"high","unit_risk":"medium","integration_risk":"high","rationale":"Read-only value-flow evidence; no implementation/acceptance invariant delegated","owned_contract_ids":["source-revision-propagation-evidence"],"dependencies":[],"question":TASK,"explorer":"openai/gpt-oss-20b","context":config["explorer_context_length"],"weekly_used_start":used,"weekly_stop":60,"gate":"One source-backed causal trace, verified by Primary; no general Explorer release","scope":"New question on known project source, separate from prior Coder results","pins":{str(p):S.sha(p) for p in paths},"config_sha256":S.sha(root / ".local-agents/config.json")})
    print("Focused Explorer question frozen; no model call")


def run(used,observed):
    assert 0<=used<60 and 0<=time.time()-observed<=120
    reg=S.read(BATCH / "registration.json")
    assert all(S.sha(p)==h for p,h in reg["pins"].items())
    root=BATCH / "isolated"
    assert S.sha(root / ".local-agents/config.json")==reg["config_sha256"]
    S.save(BATCH / "start.json",{"weekly_used":used,"usage_observed_at":observed})
    argv=[S.PYTHON,"-B",root / ".local-agents/local-explore.py","--task",TASK,"--task-id",reg["task_id"],"--report",root / ".agent/explorer-report.json","--full-report"]
    process=T.run(argv,root,timeout=1200)
    S.save(BATCH / "process.json",process)
    assert all(S.sha(p)==h for p,h in reg["pins"].items())
    print("Explorer completed; Primary evidence verification pending",process["exit_code"])


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("prepare","run"))
    p.add_argument("--weekly-used",type=int,required=True)
    p.add_argument("--observed-at",type=float)
    a=p.parse_args()
    os.environ["PYTHONIOENCODING"]="utf-8"
    if a.mode=="prepare":
        prepare(a.weekly_used)
    else:
        run(a.weekly_used,a.observed_at)
