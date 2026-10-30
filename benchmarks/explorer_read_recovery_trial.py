"""Same dependency inputs and budgets; only isolated report-repair gate changes."""

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import explorer_read_prerequisite as P
import reviewer_causal_investigation as E
import reviewer_dependency_trial as D

BATCH = (
    S.KIT / "benchmarks/work/harness-convergence/explorer-read-prerequisite-20261020-1"
)


def prepare():
    assert S.read(D.BATCH / "decision.json")["dependency_read"] == 0
    cases = list(ET.parse(BATCH / "offline-controls.xml").iter("testcase"))
    assert len(cases) == 5 and not any(
        c.find(tag) is not None
        for c in cases
        for tag in ("failure", "error", "skipped")
    )
    old = S.read(D.BATCH / "registration.json")
    rows, patches = {}, {}
    for name in old["order"]:
        row = old["cells"][name]
        root = BATCH / "cells" / name / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for relative, digest in row["files"].items():
            source = Path(row["root"]) / relative
            assert S.sha(source) == digest
            dest = root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        patches[name] = P.install(root / ".local-agents/explorer-runtime.py", root)
        files = {
            p.relative_to(root).as_posix(): S.sha(p)
            for p in root.rglob("*")
            if p.is_file()
        }
        assert [p for p, h in row["files"].items() if files[p] != h] == [
            ".local-agents/explorer-runtime.py"
        ]
        rows[name] = {**row, "root": str(root), "files": files}
    S.save(BATCH / "patches.json", patches)
    S.save(
        BATCH / "registration.json",
        {
            **old,
            "cells": rows,
            "pins": {
                str(Path(__file__).resolve()): S.sha(__file__),
                str(Path(P.__file__).resolve()): S.sha(P.__file__),
                str(Path(E.__file__).resolve()): S.sha(E.__file__),
                str(BATCH / "offline-controls.xml"): S.sha(
                    BATCH / "offline-controls.xml"
                ),
            },
            "only_change": "In isolated runtime investigate mode, report formatting recovery keeps READ available while already-required source remains unread. Original permission/quote checks/report-only-once behavior after reads and all budgets unchanged.",
            "gate": "Actual dependency acquisition2/2 and independently correct focal diagnosis2/2, no invented execution. Report success alone is insufficient. No Coder transfer/product credit without separate registration.",
            "continue_rule": "Complete both ordinary outcomes; no changed question, material, model or extra turns; safety/infra/drift/time/weekly50 stop.",
        },
    )
    print("Two exact matched-input gate controls frozen; production untouched")


def run(label, used, observed):
    E.run(label, used, observed, batch=BATCH)
