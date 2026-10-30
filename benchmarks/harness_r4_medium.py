"""Freeze original 16 controls plus four exposed real-source formal reviews."""

import argparse
import shutil
from pathlib import Path

import harness_r4_evidence as E
import harness_reviewer_terms as T

B, R = E.B, E.R
BATCH = E.BATCH.parent / "r4-review-medium-formal-20261016-1"
ADAPTER = B.KIT / "benchmarks/reviewer_medium_entry.py"
OUTPUTS = {".agent/current-task.json", ".agent/tasks/semantic-terms/state.json"}


def prepare(used):
    assert 0 <= used < 45
    previous = B.read(E.BATCH.parent / "r4-review-strength-20261016-1/decision.json")
    assert previous["selected_for_formal_diagnostic"] == "medium"
    E.prior_unchanged()
    BATCH.mkdir(exist_ok=False)
    originals = [
        {**r, "group": "original-sixteen", "new_id": r["id"]}
        for r in B.read(E.BATCH / "registration.json")["cells"]
    ]
    real = B.read(T.BATCH / "registration.json")["cells"]
    for i, name in enumerate(("cell-02", "cell-04", "cell-05", "cell-07"), 1):
        row = next(r for r in real if r["id"] == name)
        originals.append({**row, "group": "exposed-real", "new_id": f"real-{i:02}"})
    rows = []
    for original in originals:
        source = Path(original["root"])
        root = BATCH / "cells" / original["new_id"] / "isolated"
        frozen = {p: sha for p, sha in original["files"].items() if p not in OUTPUTS}
        R.assert_files(source, frozen)
        for path in frozen:
            if path in {
                ".agent/experiment-config.json",
                ".agent/experiment-request.json",
            }:
                continue
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / path, dest)
        config = B.read(source / ".agent/experiment-config.json")
        identity = {
            **original["identity"],
            "review_id": "medium-v1-" + original["new_id"],
        }
        B.save(root / ".agent/experiment-config.json", config)
        B.save(root / ".agent/experiment-request.json", identity)
        rows.append(
            {
                "id": original["new_id"],
                "group": original["group"],
                "root": str(root),
                "origin": str(source),
                "origin_files": frozen,
                "identity": identity,
                "expected_decision": original["expected_decision"],
                "files": {
                    p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)
                },
            }
        )
    B.save(
        BATCH / "registration.json",
        {
            "cells": rows,
            "registered": 20,
            "feature_id": "formal-reviewer-medium-directive",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "axis": "Only effective system reasoning directive low -> medium; archived Coder config, source, contract, checks, evidence/DTO/schema/gates/model/sampling/budgets unchanged.",
            "criterion": "Original sixteen 16/16 substantive correctness AND exposed real-source four 4/4 (two causal None defect detections, two correct reference acceptances). No resampling. No R4, holdout or Coder success credit.",
            "failure_policy": "Complete ordinary semantic/protocol/output-cap failures. Stop safety/input drift/transport/usage. Output-cap classifications retain raw results.",
            "weekly_used_start": used,
            "usage_ceiling": 45,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "production_promoted": False,
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls-v3.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(T.BATCH / "live-freeze.json")["pins"],
                **{
                    str(p): B.sha(p)
                    for p in (
                        Path(__file__),
                        ADAPTER,
                        B.KIT / "tests/test_reviewer_medium.py",
                        BATCH / "registration.json",
                        BATCH / "controls-v3.xml",
                    )
                },
            }
        },
    )


def boundary(path, value):
    p = Path(path).resolve()
    infra = value.get("infra_failure") if isinstance(value, dict) else None
    if (
        p.parent.parent == (BATCH / "cells").resolve()
        and p.name == "result.json"
        and isinstance(infra, dict)
        and infra.get("reason_code") == "output_token_limit"
    ):
        return {**value, "infra_failure": None}
    return value


def run(name, used):
    original_read, old_batch, old_adapter = B.read, E.BATCH, E.ADAPTER
    B.read = lambda path: boundary(path, original_read(path))
    E.BATCH, E.ADAPTER = BATCH, ADAPTER
    try:
        E.run(name, used)
    finally:
        B.read, E.BATCH, E.ADAPTER = original_read, old_batch, old_adapter


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "freeze", "run"])
    p.add_argument("--case")
    p.add_argument("--used", type=int)
    args = p.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
