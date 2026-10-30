"""Two full-package integration trials on the committed sibling snapshot."""

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import installed_scope_trial as I
import limited_family_trial as L
import normal_task_trial as N
import project_snapshot_prepare as SNAP
import stable_execution_tasks as TASKS
import stable_execution_trial as ENTRY
import tagged_proposal_wire as WIRE
import verified_cli_completion as LOAD
from test_installable_bounded import INSTALL

BATCH=I.BASE / "project-live-20261022-1"
ORDER=["project-1","project-2"]
TARGET="src/evaluation_harness/canonical/fingerprint.py"


def install_load(root):
    path=root / ".local-agents/model_residency.py"
    shutil.copyfile(LOAD.__file__,root / ".local-agents/bounded/verified_cli_completion.py")
    path.write_text(path.read_text(encoding="utf-8")+"\nfrom bounded.verified_cli_completion import extend\nextend(globals())\n",encoding="utf-8")


def prepare(used):
    assert not BATCH.exists() and 0<=used<60
    assert S.read(SNAP.BATCH / "baseline-recheck.json")["passed"]==148
    old=S.read(SNAP.BATCH / "baseline-checks.json")
    assert all(c["exit_code"]==0 for index,c in enumerate(old) if index!=1)
    spec=TASKS.tasks(T.extract)["hash"]
    template=BATCH / "template"
    shutil.copytree(SNAP.BATCH / "snapshot",template,ignore=shutil.ignore_patterns("__pycache__",".pytest_cache",".ruff_cache","*.pyc"))
    public=spec["public"].replace("from product.code import make_sample_id","from evaluation_harness.canonical.fingerprint import make_sample_id")
    private=spec["private"].replace("from product.code import make_sample_id","from evaluation_harness.canonical.fingerprint import make_sample_id").replace("from product.dependencies import canonical_json","from evaluation_harness.canonical.fingerprint import canonical_json")
    T.write(template / "tests/unit/test_revision_normalization.py",public)
    private_path=BATCH / "private/test_revision_independent.py"
    T.write(private_path,private)
    for argv in ([S.PYTHON,"-B","-m","ruff","check","--select","I","--fix","tests/unit/test_revision_normalization.py"],[S.PYTHON,"-B","-m","ruff","format","tests/unit/test_revision_normalization.py"]):
        assert T.run(argv,template)["exit_code"]==0
    reference=BATCH / "reference-project"
    shutil.copytree(template,reference)
    source=(reference / TARGET).read_text(encoding="utf-8")
    old_value='"source_revision": source_revision,'
    assert source.count(old_value)==1
    (reference / TARGET).write_text(source.replace(old_value,'"source_revision": None if source_revision == "" else source_revision,'),encoding="utf-8")
    os.environ["PYTHONPATH"]=str(reference / "src")
    os.environ["PYTEST_ADDOPTS"]="--basetemp="+str(reference / "pytest-owned")
    controls=[]
    for argv in ([S.PYTHON,"-B","-m","pytest","-q","-m","not integration","tests",private_path],[S.PYTHON,"-B","-m","ruff","format","--check","src","tests","examples","scripts"],[S.PYTHON,"-B","-m","ruff","check","src","tests","examples","scripts"],[S.PYTHON,"-B","-m","pyright","--pythonpath",S.PYTHON]):
        controls.append(T.run(argv,reference,timeout=300))
    S.save(BATCH / "reference-checks.json",controls)
    assert all(c["exit_code"]==0 for c in controls)
    rows={}
    for cell in ORDER:
        root=BATCH / "cells" / cell / "isolated"
        shutil.copytree(template,root)
        with tempfile.TemporaryDirectory(prefix="project-worker-install-") as directory:
            stage=Path(directory)
            INSTALL.install(S.KIT,stage,apply=True)
            shutil.copytree(stage / ".local-agents",root / ".local-agents")
            shutil.copyfile(stage / "AGENTS.md",root / "AGENTS.md")
        identity={k:BATCH.name+"-"+cell for k in ("task_id","unit_id","run_id")}
        packet=S.read(L.SEED / ".agent/packet.json")
        packet.update(identity,feature_id="full-project-revision-normalization",goal=spec["contract"],primary_plan_sha256=S.sha(__file__))
        paths=[p.relative_to(root).as_posix() for p in (root / "src").rglob("*.py")]
        packet["scope"]={"read":["src","tests","pyproject.toml","acceptance"],"readonly":[p for p in paths if p!=TARGET]+["tests","pyproject.toml",F.POLICY_PATH,F.PRODUCER,F.HELPER],"modify":[TARGET],"create":[],"forbidden":[".agent",".git",".local-agents","AGENTS.md"]}
        packet["focused_tests"]=["tests/unit/test_canonical.py","tests/unit/test_rollout_contracts.py","tests/unit/test_revision_normalization.py"]
        packet["edit_targets"]=[{"path":TARGET,"anchor":"def make_sample_id("}]
        packet["owned_contract_ids"]=["revision-normalization"]
        packet["required_behavior"]=[{"id":"revision-normalization","text":spec["contract"],"risk_floor":"high","implementation_ref":{"path":TARGET,"symbol":"make_sample_id"}}]
        packet["acceptance_criteria"]=[{"id":"revision-normalization","text":"Exact identity normalization, unchanged package compatibility, strict checks and full project integration"}]
        packet["review_feedback"]=[]
        packet["validation_profile"]="project-strict"
        config=S.read(L.SEED / ".agent/config.json")
        config.update(bounded_execution_profile="bounded-v1",coordinator_enabled=False,autoformat_on_ruff_failure=False,experimental_approved_imports=[],coder_single_function={"path":TARGET,"symbol":"make_sample_id","dependencies":"Existing canonical_json is in the same displayed module; all other package definitions and imports remain unchanged."})
        sources=[TARGET,"src/evaluation_harness/canonical/models.py","pyproject.toml",*packet["focused_tests"]]
        _,digest=F.install_material(root,identity,source_paths=sources,target={"path":TARGET,"module":"evaluation_harness.canonical.fingerprint","symbol":"make_sample_id"},family="json-call-model-dump-v1",cases=spec["cases"],writable=[TARGET],python=S.PYTHON)
        config["experimental_capture_policy_sha256"]=digest
        config["validation_profiles"]["project-strict"]={"python":str(S.PYTHON),"commands":[{"id":"ruff-format","argv":["{python}","-B","-m","ruff","format","--check","src","tests","examples","scripts"]},{"id":"ruff-check","argv":["{python}","-B","-m","ruff","check","src","tests","examples","scripts"]},{"id":"pyright","argv":["{python}","-B","-m","pyright","--pythonpath",str(S.PYTHON)]},F.command()]}
        I.refresh_material(root,config)
        WIRE.install(root)
        ENTRY.reviewer_install(root)
        install_load(root)
        S.save(root / ".agent/packet.json",packet)
        S.save(root / ".agent/config.json",config)
        os.environ["PYTHONPATH"]=str(root / "src")
        os.environ["PYTEST_ADDOPTS"]="--basetemp="+str(root / ".agent/pytest-owned")
        result=T.run(I.command(root,"preflight"),root)
        S.save(BATCH / "preflight" / (cell+".json"),result)
        assert result["exit_code"]==0,result
        (root / ".agent/unit-report.json").rename(root / ".agent/preflight-report.json")
        rows[cell]={"root":str(root),"topic":"full-project","identity":identity,"target":TARGET,"private_tests":str(private_path),"files":{p.relative_to(root).as_posix():S.sha(p) for p in root.rglob("*") if p.is_file() and not any(x in p.parts for x in ("__pycache__",".pytest_cache",".ruff_cache","pytest-owned"))}}
    S.save(BATCH / "cells.json",rows)
    pins=[Path(__file__),Path(WIRE.__file__),Path(LOAD.__file__),private_path,BATCH / "cells.json",BATCH / "reference-checks.json",SNAP.BATCH / "baseline-recheck.json"]
    pins += [p for p in (S.KIT / ".local-agents").rglob("*.py") if "__pycache__" not in p.parts]
    S.save(BATCH / "registration.json",{"order":ORDER,"registered":2,"weekly_used_start":used,"weekly_stop":60,"batch_seconds":10800,"pins":{str(p):S.sha(p) for p in pins},"gate":"2/2 fresh Reviewer and Primary complete accepts including actual full-project tests; no assisted credit, unrelated changes or sibling writes","models":"Unchanged Qwen/Muse, one resident","candidate":"Installed bounded-v1 + flat tagged wire + frozen direct-report Reviewer + deferred CLI timeout through original API readiness checks","risk":"high feature/unit/integration due sample identity compatibility","exposure":"Known requested normalization, now tested in actual complete committed project; not new semantic holdout. Sibling working changes excluded explicitly and untouched.","budget":"Coder12requests/3edits/1initial+3postchecks/900s; Reviewer16requests/600s,4096 output; CLI360s unchanged","continue_rule":"Ordinary failure HOLD and continue; infra/safety/drift/deadline/weekly60 stop","Primary":"Prepared contract/tests/reference and project snapshot; no runtime semantic repair hints or takeover; costs unknown"})
    print("Two complete-package units frozen")


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
        root=Path(S.read(BATCH / "cells.json")[a.cell]["root"])
        os.environ["PYTHONPATH"]=str(root / "src")
        os.environ["PYTEST_ADDOPTS"]="--basetemp="+str(root / ".agent/pytest-owned")
        N.run(a.cell,a.weekly_used,a.observed_at or time.time(),batch=BATCH,order=ORDER,build_command=I.command,usage_limit=60,batch_seconds=10800)
