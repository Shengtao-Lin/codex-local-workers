"""One known dependency chain through the explicitly selected product profile."""

import argparse
import time
from pathlib import Path

import bounded_chain_matrix as M
import bounded_evidence_support as S

ROOT = M.D.I.BASE / "packaged-chain-profile-20261022-1"
CELL = "tags-packaged"
M.ROOT, M.ORDER = ROOT, [CELL]


def select_profile():
    original = M.D.I.refresh_material

    def refresh(root, config):
        original(root, config)
        config.update(bounded_compatibility_profile="flat-v1", model_load_ack_policy="api_verified")

    M.D.I.refresh_material = refresh


def prepare(used):
    assert S.read(M.D.I.BASE / "reviewer-profile-screen-20261022-3/decision.json")["status"] == "PASS_FIXED_REVIEWER_SCREEN"
    original = S.save

    def save(path, value):
        path = Path(path)
        if path.name == "reference-only.json":
            value = [{"kind": "replacement", "content": v["replacement"]} for v in value]
        if path.name == "registration.json":
            value.update(weekly_stop=60,
                         candidate="Actual installed bounded-v1 with flat-v1/API verified load acknowledgement; unchanged Coordinator and acceptance bridge",
                         exposure="Known stable_unique -> render_tags chain; installed-profile compatibility regression, not new task/holdout",
                         scope="One explicitly approved immutable-snapshot chain; no generic routing, classification or production default",
                         continue_rule="Ordinary failure HOLD; no dependent execution until producer independently accepted; stop infrastructure/safety/drift/time/weekly60. No semantic resampling")
            value["pins"][str(Path(__file__))] = S.sha(__file__)
            if path == ROOT / "registration.json":
                value.update(registered_chains=1, registered_units=2,
                             gate="One correctly decomposed and approved dependency chain, both units independently accepted, complete integration/checks/current bridge receipts; no semantic rescue or drift")
        original(path, value)

    S.save = save
    try:
        M.prepare(used)
    finally:
        S.save = original


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "plan", "approve", "execute", "accept", "close", "hold"))
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--topic", choices=("encode", "append"))
    p.add_argument("--reason")
    a = p.parse_args()
    select_profile()
    if a.mode == "prepare":
        prepare(a.weekly_used)
    else:
        live = a.mode in {"plan", "execute"}
        M.frozen(CELL, a.weekly_used if live else None, time.time())
        if a.mode == "plan":
            M.D.plan(a.weekly_used, time.time())
        elif a.mode == "approve":
            M.D.approve(a.reason)
        elif a.mode == "execute":
            M.D.execute(a.topic, a.weekly_used, time.time())
        elif a.mode == "accept":
            M.D.accept(a.topic, a.reason)
        elif a.mode == "hold":
            M.hold(CELL, a.reason)
        else:
            M.CLOSE.close(a.weekly_used, a.reason)
            S.save(ROOT / "decision.json", {"status": "PASS_PACKAGED_SNAPSHOT_CHAIN",
                   "accepted_chains": 1, "accepted_units": 2, "semantic_assistance": 0,
                   "evidence": str(M.D.BATCH / "decision.json"),
                   "qualification": "Current product-profile compatibility with previously qualified snapshot routing; no general production or economic claim"})
