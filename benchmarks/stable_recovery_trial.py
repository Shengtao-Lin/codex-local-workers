"""Four fresh repair starts from exposed failed drafts; no semantic fix supplied."""

import argparse
import os
import shutil
import time
from pathlib import Path

import bounded_evidence_support as S
import installed_real_trial as R
import installed_scope_trial as I
import normal_task_trial as N
import real_change_trial as TASK
import stable_execution_trial as ENTRY

BATCH = I.BASE / "stable-recovery-20261022-1"
ORIGIN = I.BASE / "reviewer-direct-20261021-1"
ORDER = ["destination-1", "message-1", "message-2", "destination-2"]


def prepare(used):
    assert not BATCH.exists() and 0 <= used < 50
    assert S.read(ENTRY.BATCH / "decision.json")["status"] == "PASS_FIXED_MATRIX_NO_FEEDBACK_ADOPTION"
    origins = S.read(ORIGIN / "cells.json")
    draft_sources = {topic: Path(origins[topic + "-1"]["root"]) / "src/product/code.py" for topic in ("destination", "message")}
    original_save, original_refresh = S.save, I.refresh_material
    def refresh(root, config):
        topic = root.parent.name.split("-")[0]
        shutil.copyfile(draft_sources[topic], root / "src/product/code.py")
        original_refresh(root, config)
        ENTRY.reviewer_install(root)
    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                registered=4, weekly_stop=60,
                authorization="User approved autonomous branch-plan including failed-check recovery, weekly60 stop",
                gate="4/4 fresh Reviewer plus independent final accepts, no hints, takeover or source/protected drift",
                candidate="Preferred A: installed bounded-v1 unmodified decoder, frozen direct-report Reviewer; fresh repair starts from actual old failed drafts",
                exposure="Fully exposed diagnostic repairs, not holdout/initial task successes. Exact old contract/public/private acceptance. No successful patch, hidden failures or Primary repair advice supplied.",
                difference="Old latest failed implementation is the new starting source. Host reruns current checks and displays facts before first proposal. New identity and batch; not continuation or erasure of old run; no causal fresh-context claim.",
                continue_rule="Ordinary implementation/review rework HOLD, complete four diagnostics; infra/safety/drift/time/weekly60 stop. No replacement or candidate edits.",
                budgets={"requests":12,"edits":3,"initial_checks":1,"post_edit_checks":3,"protocol_recoveries":2,"coder_seconds":900,"reviewer_requests":16,"reviewer_seconds":600,"output_tokens":4096},
                prior_reviewer_rework="Raw unconfirmed automatic semantic rework remains disabled after old4/4 regressions; this batch tests Coder repair of exposed drafts, not that policy's adoption",
                draft_origins={k:{"path":str(p),"sha256":S.sha(p),"prior_cell":k+"-1"} for k,p in draft_sources.items()},
            )
            for p in (Path(__file__), Path(TASK.__file__), Path(ENTRY.__file__), S.KIT / "benchmarks/reviewer_direct_report.py", ORIGIN / "decision.json", *draft_sources.values()):
                value["pins"][str(p)] = S.sha(p)
        original_save(path, value)
    R.BATCH, R.ORDER = BATCH, ORDER
    R.TASKS = {k:v for k,v in TASK.TASKS.items() if k in ("destination", "message")}
    I.refresh_material, S.save = refresh, save
    try:
        original_save(BATCH / "baseline.json", {"production":{str(p):S.sha(p) for p in (S.KIT / ".local-agents").rglob("*") if p.is_file() and "__pycache__" not in p.parts},"weekly_used":used,"weekly_stop":60})
        R.prepare(used)
    finally:
        I.refresh_material, S.save = original_refresh, original_save
    print("Four exposed failed-draft repairs frozen; original runs untouched")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--observed-at", type=float)
    a = p.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if a.mode == "prepare":
        prepare(a.weekly_used)
    else:
        N.run(a.cell,a.weekly_used,a.observed_at or time.time(),batch=BATCH,order=ORDER,build_command=I.command,usage_limit=60,batch_seconds=10800)
