"""Conditional exposed recovery probe: field feedback only, same failing draft."""

import argparse
import os
import time
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I
import normal_task_trial as N
import proposal_field_feedback as C
import stable_recovery_trial as D

BATCH = I.BASE / "protocol-field-recovery-20261022-1"
ORDER = ["destination-1", "destination-2"]


def prepare(used):
    assert not BATCH.exists()
    assert S.read(D.BATCH / "live-results/destination-1/result.json")["coder_status"] == "failed"
    original_save, original_refresh = S.save, I.refresh_material
    def refresh(root, config):
        original_refresh(root, config)
        C.install(root)
    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                registered=2,
                candidate="Specific field/type feedback after invalid proposal; decoder acceptance unchanged. Same installed host/checks/direct-report Reviewer and model/budget.",
                gate="2/2 independent full-chain accept; otherwise HOLD and classify protocol vs semantic failures",
                comparison="Exposed sequential diagnostic against stable-recovery-20261022-1 destination repeats. Conditional branch triggered by its retained failure; not prospective randomized causal estimate or new holdout.",
                hypothesis="Field/type-specific rejection can recover string proposals from the repeated array output. Semantic correctness independently measured; successful decoding alone is not acceptance.",
            )
            value["pins"][str(Path(__file__))] = S.sha(__file__)
            value["pins"][str(Path(C.__file__))] = S.sha(C.__file__)
        original_save(path, value)
    D.BATCH, D.ORDER = BATCH, ORDER
    I.refresh_material, S.save = refresh, save
    try:
        D.prepare(used)
    finally:
        I.refresh_material, S.save = original_refresh, original_save
    print("Two field-feedback-only recovery cells frozen")


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
