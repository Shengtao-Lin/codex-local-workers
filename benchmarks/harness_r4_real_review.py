"""Frozen exposed real-archive review diagnostic; not Coder/transfer credit."""

import argparse
import shutil
from pathlib import Path

import harness_r4_evidence as E
import reviewer_experiment_entry as A

B, R = E.B, E.R
BATCH = E.BATCH.parent / "r4-real-review-20261016-2"
ADAPTER = B.KIT / "benchmarks/reviewer_experiment_entry.py"
CASES = [("datetime", "pass_to_primary"), ("collect_tools", "rework")]


def prepare(used):
    assert used < 45
    assert B.read(E.BATCH / "decision.json")["qualification"] == "PASS"
    E.prior_unchanged()
    BATCH.mkdir(exist_ok=False)
    rows = []
    for topic, expected in CASES:
        origin = E.D.OLD.H.BATCH / "cases" / f"{topic}-candidate-1" / "isolated"
        original_run = (
            origin
            / ".agent/tasks"
            / ("r4-" + topic)
            / "runs"
            / ("r4-20261016-" + topic + "-candidate-1")
        )
        root = BATCH / "cells" / topic / "isolated"
        copied = {}

        def copy(source, relative, root=root, copied=copied):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied[relative] = {"origin": str(source), "sha256": B.sha(source)}

        for top in ("src", "tests", ".local-agents"):
            for source in B.files(origin / top):
                copy(source, source.relative_to(origin).as_posix())
        copy(origin / "pyproject.toml", "pyproject.toml")
        # Diagnostic copies start before review; never remove dispatch/index from
        # a real archive. Omitted original files remain hashed and preserved.
        excluded = {}
        for source in B.files(original_run):
            if source.name in {
                "review.json",
                "host-review-dispatch.json",
                "auto-review-request.json",
            }:
                excluded[source.name] = {"path": str(source), "sha256": B.sha(source)}
                continue
            copy(source, source.relative_to(origin).as_posix())
        identity = B.read(original_run / "auto-review-request.json")
        identity["review_id"] = "evidence-real-" + topic
        config = B.read(origin / ".agent/config.json")
        config.update(reviewer_compact_report=True, reviewer_evidence_state=True)
        B.save(root / ".agent/experiment-config.json", config)
        B.save(root / ".agent/experiment-request.json", identity)
        module = R.load(
            root / ".local-agents/reviewer-runtime.py", "real_review_preflight_" + topic
        )
        runtime = A.install(module)(
            root, identity, config, type("NoModel", (), {"native_tools": None})()
        )
        runtime.initial_payload()
        assert runtime.max_turns == 16 and runtime.max_protocol_errors == 4
        rows.append(
            {
                "id": topic,
                "root": str(root),
                "identity": identity,
                "expected_decision": expected,
                "origin": str(origin),
                "copied_inputs": copied,
                "excluded_prior_review_outputs": excluded,
                "files": {
                    p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)
                },
            }
        )
    B.save(
        BATCH / "registration.json",
        {
            "registered": 2,
            "cells": rows,
            "weekly_used_start": used,
            "usage_ceiling": 45,
            "feature_id": "exposed-real-review-diagnostic-v1",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "risk_rationale": "Fresh-context assessment of actual canonical archives, not automatic acceptance or production redispatch",
            "owned_contract_ids": [
                "actual-archive-fidelity",
                "independent-semantic-detection",
                "immutable-history",
            ],
            "criterion": "Correct clean disposition and causal None-result omission finding; matching rework for unrelated complaints is not success",
            "not_transfer_credit": True,
            "not_fresh_holdouts": True,
            "no_retry": True,
            "candidate": str(E.BATCH / "live-freeze.json"),
            "model": "meta/muse-glimmer",
            "same_original_request_budget": True,
            "diagnostic_entry_boundary": "Only reviewer_compact_report and reviewer_evidence_state are adapter switches outside the archived Coder config. All original config fields and every archived hash still go through the unmodified verifier; changed model, limits, checks or unknown fields are rejected.",
            "copy_boundary": "Exclude prior review outputs in new isolated diagnostic copies only; preserve canonical Coder facts, original inputs and every original output. No production replay or archive cleanup.",
        },
    )
    print(
        "Two exposed real archives copied and host-handoff preflight passed; no model calls"
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + x) for x in ("failure", "error", "skipped")
    )
    old = B.read(E.BATCH / "live-freeze.json")
    pins = {
        **old["pins"],
        str(Path(__file__)): B.sha(Path(__file__)),
        str(BATCH / "registration.json"): B.sha(BATCH / "registration.json"),
        str(ADAPTER): B.sha(ADAPTER),
        str(B.KIT / "tests/test_harness_real_review.py"): B.sha(
            B.KIT / "tests/test_harness_real_review.py"
        ),
    }
    B.save(BATCH / "live-freeze.json", {"pins": pins})
    print("Real diagnostic frozen; no new semantic hints")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "freeze", "run"])
    parser.add_argument("--used", type=int)
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        # Reuse the exact frozen single-cell executor, changing only its batch
        # location in this process. No prior script or result file is rewritten.
        E.BATCH = BATCH
        E.ADAPTER = ADAPTER
        E.run(args.case, args.used)
