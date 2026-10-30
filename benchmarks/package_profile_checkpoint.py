"""Recoverable preimages before explicit-profile integration; no Git mutation."""

import shutil
import subprocess

import bounded_evidence_support as S

BATCH=S.KIT / "benchmarks/work/harness-convergence/packaged-flat-profile-20261022-1"


def main():
    assert not BATCH.exists()
    assert S.read(S.KIT / "benchmarks/work/harness-convergence/project-live-20261022-2/decision.json")["accepted"]==2
    files=[p for p in (S.KIT / ".local-agents").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    files.append(S.KIT / "AGENTS.md")
    S.save(BATCH / "baseline.json",{"weekly_stop":60,"head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=S.KIT,text=True).strip(),"status":subprocess.check_output(["git","status","--short","-uno"],cwd=S.KIT,text=True),"preimages":{p.relative_to(S.KIT).as_posix():S.sha(p) for p in files},"authorization":"Explicit default-off compatibility profile integration after component/offline/full-package evidence; preserve user changes and old versions","scope":"Wire adaptation, Reviewer request profile and verified CLI completion only; no semantic budget/permission/acceptance changes"})
    for path in files:
        target=BATCH / "preimages" / path.relative_to(S.KIT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    print("All current agent files and user changes checkpointed before integration")


if __name__=="__main__":
    main()
