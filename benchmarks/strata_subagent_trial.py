"""Four frozen feasibility cells: bounded interactive worker and direct Primary."""

import argparse
import os
import shutil
from pathlib import Path

import strata_boundary_ready_trial as READY

B, J, P, S = READY.B, READY.B.J, READY.B.P, READY.B.S
BATCH = P.I.BASE / "strata-subagent-20261023-1"
ENTRY = Path(__file__).with_name("strata_subagent_entry.py")
ARMS = {"message-1": "A", "hash-1": "B", "hash-2": "A", "message-2": "B"}
COPY = J.copy_project
OLD = P.I.BASE / "strata-project-20261023-2/cells/message-1/isolated"


def copy_project(origin, destination):
    COPY(origin, destination)
    if Path(origin) == J.TASKS.SNAPSHOT and Path(destination).name == "message":
        target = "src/evaluation_harness/adapters/common.py"
        shutil.copyfile(OLD / target, Path(destination) / target)


def save(path, value):
    path = Path(path)
    if path == BATCH / "replay/hash/reference.json":
        value = [
            {
                "kind": "read",
                "path": "src/evaluation_harness/canonical/fingerprint.py",
                "start_line": 1,
                "end_line": 30,
            },
            *value,
        ]
    if (
        path.name == "config.json"
        and ".agent" in path.parts
        and "prepared" not in path.parts
    ):
        cell = path.parent.parent.parent.name
        topic = cell.split("-")[0]
        files = (
            [
                "src/evaluation_harness/adapters/common.py",
                "src/evaluation_harness/adapters/generic_otel.py",
                "src/evaluation_harness/canonical/models.py",
            ]
            if topic == "message"
            else [
                "src/evaluation_harness/jobs/queue.py",
                "src/evaluation_harness/canonical/fingerprint.py",
                "src/evaluation_harness/persistence/tables.py",
            ]
        )
        value = {
            **value,
            "experimental_strata_subagent": ARMS[cell] == "B",
            "experimental_evidence_files": [
                *files,
                f"tests/unit/test_local_worker_{topic}.py",
            ],
        }
    if path == BATCH / "registration.json":
        value = {
            **value,
            "weekly_cap": 40,
            "candidate": "A existing flat Coder+fresh Reviewer+Primary; B same host plus4 read/search actions and direct Primary, no Local Reviewer",
            "model": "Same resident Strata iq3_s,128K/parallel1; clients64K,medium,4096 thinking/12288 total output,temperature1/top_p.95/top_k20",
            "budget": "Both C12 requests/3 effective edits/1 initial+3 postchecks/2 protocol recoveries/900s. B max4 evidence actions consume same12; A fresh Reviewer16requests/600s. Cell2220s,batch5400s. No arbitrary shell.",
            "arms": ARMS,
            "exposure": "Two exposed complete-project contracts,1 execution per arm each. Message starts from retained wrong draft(isinstance int) and protected boundary cases; hash starts legacy. Test-assisted known-task feasibility, not holdout or stability estimate.",
            "gate": "B2/2 independent project tests/statics, verified canonical host handoff, full Primary diff/contract review, zero unsafe drift; no unapproved semantics or manual code. NOT production E/C/R release. If B never reads/searches, evidence interaction benefit unexercised.",
            "continue_rule": "Ordinary failure HOLD but complete fixed four cells. Immediately stop infrastructure/residency/drift/safety/deadline/weekly40; inspect each result before next dispatch. No rerolls.",
            "Primary": "Reuse detailed contracts/test scaffolds; one-time adapter/prep costs separate. Full final review both arms. Any new semantic explanation or fix is assisted. No savings claim or precise active/cloud cost without measurement.",
            "confounds": "B changes both evidence interaction and Local Reviewer routing; joint feasibility, not isolated causal attribution. Familiar contracts and Primary tests;2 tasks not generality; no Primary-only economic control.",
            "primary_return": "Only on an actual defect/block, not manufactured for a demo. A bounded rework packet may use remaining original Coder credits; no reset, hidden-test feedback or algorithm injection. Record separately before dispatch. No second live packet preallocated in this four-cell registration.",
            "production_acceptance": False,
        }
        for filename in (
            "strata_subagent_trial.py",
            "strata_subagent_entry.py",
            "strata_subagent_rules.py",
            "strata_model_entry.py",
            "strata_entry.py",
            "approved_evidence.py",
        ):
            p = Path(__file__).with_name(filename)
            value["pins"][str(p)] = S.sha(p)
        value["pins"][str(Path(B.__file__))] = S.sha(B.__file__)
        return B.MODEL.BASE_SAVE(path, value)
    if path == BATCH / "preparation.json":
        value = {
            **value,
            "authorization": "User approved trying an implementation subagent, opt-in experiment, weekly40 stop; sibling read-only, no commit/push/default change",
            "start_note": "Message template uses immutable prior wrong draft; hash template frozen upstream baseline. Both arms match per topic; hidden acceptance/reference remain outside Worker scopes.",
        }
    return READY.save(path, value)


def configure():
    B.BATCH = B.MODEL.BATCH = B.FIRST.BATCH = BATCH
    B.FIRST.ENTRY = ENTRY
    B.FIRST.configure()
    B.FIRST.ORIGINAL_SAVE = save
    J.copy_project = copy_project
    J.TASKS.tasks = B.tasks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=J.ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    assert args.weekly_used < 40
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    configure()
    if args.mode == "prepare":
        J.prepare(args.weekly_used)
    else:
        P.TARGET = S.read(BATCH / "cells.json")[args.cell]["target"]
        P.run(args.cell, args.weekly_used)
