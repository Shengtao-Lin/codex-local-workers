"""Retest the exposed source-only question with explicit trusted obligations."""

import argparse
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import packaged_explorer_investigate as INV

BATCH = I.BASE / "explorer-obligation-live-20261022-1"
CONTROLS = I.BASE / "explorer-obligation-controls-20261022-1/green.xml"


def prepare(used):
    cases = list(ET.parse(CONTROLS).iter("testcase"))
    assert len(cases) == 85 and not any(c.find(x) is not None for c in cases for x in ("failure", "error", "skipped"))
    original = S.save

    def save(path, value):
        path = Path(path)
        if path.name == "config.json" and path.parent.name == ".local-agents":
            value["explorer_require_test_evidence"] = False
        if path == BATCH / "registration.json":
            runtime = BATCH / "isolated/.local-agents/explorer-runtime.py"
            value.update(candidate="Explicit source-only test obligation; bounded missing-citation read guidance; default legacy inference unchanged",
                         exposure="Same previously exposed investigation, not a new task or holdout",
                         history="Prior locate causal-evidence HOLD and investigate protocol failure retained",
                         gate="One correct actual caller/argument and field evidence; no fabricated citations or Primary semantic answer",
                         offline_controls="85 passed, original negative run10 failed/1 passed retained")
            value["pins"].update({str(runtime): S.sha(runtime), str(Path(__file__)): S.sha(__file__), str(CONTROLS): S.sha(CONTROLS)})
        original(path, value)

    INV.BATCH = BATCH
    S.save = save
    try:
        INV.prepare(used)
    finally:
        S.save = original


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    INV.BATCH = INV.OLD.BATCH = BATCH
    INV.OLD.TASK = INV.TASK
    if a.mode == "prepare":
        prepare(a.weekly_used)
    else:
        INV.OLD.run(a.weekly_used, time.time())
