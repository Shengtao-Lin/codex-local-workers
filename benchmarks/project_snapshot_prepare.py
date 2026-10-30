"""Read-only committed sibling snapshot, actual project checks, no model calls."""

import os
import subprocess
import zipfile
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T

UP=Path("F:/ChatGPT/agent-evaluation-harness")
BATCH=S.KIT / "benchmarks/work/harness-convergence/project-install-20261022-1"


def main():
    assert not BATCH.exists()
    commit=subprocess.check_output(["git","-C",str(UP),"rev-parse","HEAD"],text=True).strip()
    working=subprocess.check_output(["git","-C",str(UP),"status","--short","-uno"],text=True)
    entries=subprocess.check_output(["git","-C",str(UP),"ls-tree","--name-only","HEAD"],text=True).splitlines()
    selected=[p for p in entries if not p.startswith(".") and p!="AGENTS.md"]
    S.save(BATCH / "registration.json",{"phase":"E offline project baseline","upstream":str(UP),"commit":commit,"working_changes":working,"snapshot":"Committed tree only; current uncommitted sibling changes are untouched and excluded explicitly","selected":selected,"worker_calls":0,"weekly_stop":60,"gate":"Actual baseline unit tests, project format/lint/type checks and imported-module provenance pass before live","pins":{str(Path(__file__)):S.sha(__file__)}})
    archive=BATCH / "source.zip"
    subprocess.run(["git","-C",str(UP),"archive","--format=zip","--output="+str(archive),commit,*selected],check=True)
    root=BATCH / "snapshot"
    root.mkdir()
    with zipfile.ZipFile(archive) as source:
        assert all((root/name).resolve().is_relative_to(root.resolve()) for name in source.namelist())
        source.extractall(root)
    os.environ["PYTHONPATH"]=str(root / "src")
    checks=[]
    paths=[name for name in ("src","tests","examples","scripts") if (root/name).exists()]
    for argv in (
        [S.PYTHON,"-B","-c","import evaluation_harness.canonical.fingerprint as f; from pathlib import Path; assert Path(f.__file__).resolve().is_relative_to(Path.cwd()); print(f.__file__)"],
        [S.PYTHON,"-B","-m","pytest","-q","-m","not integration","tests"],
        [S.PYTHON,"-B","-m","ruff","format","--check",*paths],
        [S.PYTHON,"-B","-m","ruff","check",*paths],
        [S.PYTHON,"-B","-m","pyright","--pythonpath",S.PYTHON],
    ):
        checks.append(T.run(argv,root,timeout=300))
    S.save(BATCH / "baseline-checks.json",checks)
    status="BASELINE_READY" if all(c["exit_code"]==0 for c in checks) else "BASELINE_BLOCKED_NO_LIVE"
    S.save(BATCH / "decision.json",{"status":status,"worker_calls":0,"passed_checks":sum(c["exit_code"]==0 for c in checks),"total_checks":len(checks),"source_archive_sha256":S.sha(archive),"baseline_only":True})
    print(status)


if __name__=="__main__":
    main()
