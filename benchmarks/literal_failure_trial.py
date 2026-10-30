"""Second narrow candidate: literal pytest excerpt, unchanged source and checks."""

import argparse
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import literal_failure_feedback as C
import normal_task_trial as N
import stable_recovery_trial as D

BATCH = I.BASE / "literal-failure-recovery-20261022-1"
ORDER = ["destination-1", "destination-2"]
CONTROLS = I.BASE / "stable-execution-prep-20261021-1/literal-controls.xml"


def prepare(used):
    assert not BATCH.exists()
    controls = list(ET.parse(CONTROLS).iter("testcase"))
    assert len(controls) == 7 and not any(c.find(t) is not None for c in controls for t in ("failure","error","skipped"))
    original_save, original_refresh = S.save, I.refresh_material
    def refresh(root, config):
        original_refresh(root, config)
        C.install(root)
    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                registered=2,
                candidate="Preferred original decoder plus lossless literal display of existing pytest focused_tests.excerpt. No type-feedback adapter, semantic hints or tool/budget changes.",
                gate="2/2 independent complete accepts; otherwise stop tuning this exposed failure and retain capability boundary",
                hypothesis="Literal pytest failure display can improve use of existing evidence. No new source/test/expected outputs; roundtrip control proves exact metadata and excerpt preservation.",
                comparison="Exposed sequential diagnostic against old original/field-feedback repairs, not randomized causal proof or general transfer qualification",
                candidate_limit="Second narrow repair candidate in this branch; no third prompt/representation candidate on this old task if HOLD",
            )
            for p in (Path(__file__), Path(C.__file__), CONTROLS):
                value["pins"][str(p)] = S.sha(p)
        original_save(path, value)
    D.BATCH, D.ORDER = BATCH, ORDER
    I.refresh_material, S.save = refresh, save
    try:
        D.prepare(used)
    finally:
        I.refresh_material, S.save = original_refresh, original_save
    print("Two literal-failure-only cells frozen")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare","run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--observed-at", type=float)
    a = p.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if a.mode == "prepare":
        prepare(a.weekly_used)
    else:
        N.run(a.cell,a.weekly_used,a.observed_at or time.time(),batch=BATCH,order=ORDER,build_command=I.command,usage_limit=60,batch_seconds=10800)
