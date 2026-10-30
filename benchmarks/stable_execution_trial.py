"""Frozen A/B through the installed entry, using existing setup/check/archive code."""

import argparse
import json
import os
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import installed_real_trial as R
import installed_scope_trial as I
import normal_task_trial as N
import proposal_field_feedback as C
import stable_execution_tasks as TASKS

BATCH = I.BASE / "stable-execution-ab-20261021-2"
PREP = I.BASE / "stable-execution-prep-20261021-1"
ORDER = ["binding-A1", "binding-B1", "hash-B1", "hash-A1", "collector-A1", "collector-B1", "binding-B2", "binding-A2", "hash-A2", "hash-B2", "collector-B2", "collector-A2"]


def reviewer_install(root):
    path = root / ".local-agents/local-bounded-review.py"
    source = path.read_text(encoding="utf-8")
    anchor = "from bounded import reviewer_capture_entry as CAPTURE"
    assert source.count(anchor) == 1 and "DIRECT.install" not in source
    source = source.replace(anchor, anchor + "\nfrom bounded import reviewer_direct_report as DIRECT")
    anchor = "    if options.inspect_only:"
    assert source.count(anchor) == 1
    source = source.replace(anchor, "    runtime_class = DIRECT.install(module, runtime_class, enabled=True)\n" + anchor)
    path.write_text(source, encoding="utf-8")
    shutil.copyfile(S.KIT / "benchmarks/reviewer_direct_report.py", root / ".local-agents/bounded/reviewer_direct_report.py")


def prepare(used):
    assert 0 <= used < 60 and not BATCH.exists()
    controls = list(ET.parse(PREP / "controls-4.xml").iter("testcase"))
    assert len(controls) == 27 and not any(c.find(t) is not None for c in controls for t in ("failure", "error", "skipped"))
    original_save, original_refresh = S.save, I.refresh_material
    production = {str(p): S.sha(p) for p in (S.KIT / ".local-agents").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    def refresh(root, config):
        original_refresh(root, config)
        reviewer_install(root)
        if root.parent.name.split("-")[-1].startswith("B"):
            C.install(root)
    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                registered=12, weekly_stop=60,
                authorization="User approved autonomous branch-plan execution and routine blocker resolution; weekly60 stop",
                candidate="A installed bounded-v1 + frozen direct-report Reviewer; B same plus field/type-specific proposal rejection feedback",
                gate="12/12 independent complete accepts and no false acceptance for full tested matrix; partial family qualification explicitly separate",
                exposure="New requested behaviors on Primary-read sibling functions; known symbols may have prior exposure. First cells unexposed to this requested change; repeats exposed. No holdout claims for legacy symbols.",
                continue_rule="Ordinary semantic/protocol budget failures HOLD and continue fixed diagnostics. Infrastructure, safety, protected drift, deadline or weekly60 stop. No replacement cells or in-batch candidate changes.",
                hypothesis="Specific protocol feedback improves recovery without changing accepted outputs, authority, checks, model or semantic guidance. Without actual protocol errors, this batch cannot establish feedback benefit.",
                budget={"requests":12,"edits":3,"initial_checks":1,"post_edit_checks":3,"protocol_recoveries":2,"coder_seconds":900,"reviewer_requests":16,"reviewer_seconds":600,"output_tokens":4096},
                Primary="Authored contracts/public-private tests/reference controls; prior preparation failures preserved. No runtime repair hints or production edits. Active time/cloud tokens unknown; no economic claim.",
            )
            for p in (Path(__file__), Path(TASKS.__file__), Path(C.__file__), S.KIT / "benchmarks/reviewer_direct_report.py", PREP / "controls-4.xml"):
                value["pins"][str(p)] = S.sha(p)
        original_save(path, value)
    R.BATCH, R.ORDER, R.TASKS = BATCH, ORDER, TASKS.tasks(T.extract)
    I.refresh_material, S.save = refresh, save
    try:
        original_save(BATCH / "baseline.json", {"production":production,"weekly_used":used,"weekly_stop":60,"head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=S.KIT).decode().strip(),"dirty":subprocess.check_output(["git","status","--short","-uno"],cwd=S.KIT).decode(),"historical_decisions":{str(p):S.sha(p) for p in (I.BASE / "reviewer-direct-20261021-1/decision.json",I.BASE / "bounded-chain-matrix-20261021-1/decision.json")}})
        R.prepare(used)
    finally:
        I.refresh_material, S.save = original_refresh, original_save
    # Exact starts and task material match; only the B decoder feedback differs.
    rows = S.read(BATCH / "cells.json")
    for topic in R.TASKS:
        starts = [Path(rows[c]["root"]) for c in ORDER if rows[c]["topic"] == topic]
        for name in ("src/product/code.py", "tests/test_contract.py", "pyproject.toml"):
            assert len({S.sha(root / name) for root in starts}) == 1
    assert not [p for p,h in production.items() if S.sha(p) != h]
    print("12 matched starts frozen; production untouched")


def run(cell, used, observed):
    N.run(cell, used, observed, batch=BATCH, order=ORDER, build_command=I.command, usage_limit=60, batch_seconds=10800)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        run(args.cell, args.weekly_used, args.observed_at or time.time())
