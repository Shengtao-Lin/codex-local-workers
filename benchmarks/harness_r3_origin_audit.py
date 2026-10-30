"""Post-run experiment audit; no changes to the frozen R3 candidate or cells."""
import json
import shutil

import harness_fixture_origin as origin
import harness_r3_prepare as P
import harness_r3_run as run

B = P.B


def main():
    repair_manifest = B.read(P.R2 / "freeze.json")["cases"]["raw-1"]
    presence_manifest = B.read(P.PRESENCE.parent.parent / "freeze.json")["cases"]["presence-1"]
    rows = []
    for name in P.ORDER:
        root = run.BATCH / "cases" / name / "isolated"
        manifest = repair_manifest if name.startswith("repair-") else presence_manifest
        mismatch = origin.drift(root, manifest)
        rows.append({"cell": name, "initial_source_valid": not mismatch, "drift": mismatch,
                     "live_executed": (root.parent / "started.json").exists()})
    # A corrected source-only copy, not a second live matrix. Locate a verified
    # unchanged input rather than trusting a result directory's label. The
    # original R0 formal-1 workspace was also changed by its historical run;
    # the new origin guard correctly rejects it before any copy/model call.
    archive = B.KIT / "benchmarks/work/harness-convergence/r2-rendering-20261014-1/cases/json-1/isolated"
    origin.require_origin(archive, repair_manifest)
    root = P.BATCH / "origin-audit/corrected-repair-input"
    root.mkdir(parents=True, exist_ok=False)
    for relative in origin.source_inputs(repair_manifest):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive / relative, destination)
    origin.require_origin(root, repair_manifest)
    commands = [
        ["-m", "pytest", "-q", "-p", "no:cacheprovider", "tests", "--junitxml=" + str(P.BATCH / "origin-audit/corrected-reference.xml")],
        ["-m", "ruff", "format", "--check", "src", "tests"],
        ["-m", "ruff", "check", "src", "tests"],
        ["-m", "pyright", "--pythonpath", str(P.PYTHON)],
    ]
    checks = [B.command([str(P.PYTHON), "-B", *args], cwd=root) for args in commands]
    B.save(P.BATCH / "origin-audit/corrected-baseline-checks.json", checks)
    assert [row["exit_code"] for row in checks] == [0, 0, 1, 0]
    assert "E501" in checks[2]["stdout"]
    correct = B.sha(root / B.SOURCE)
    wrong = B.sha(run.BATCH / "cases/repair-candidate-1/isolated" / B.SOURCE)
    request = B.read(P.R2 / "cases/owned-1/request.json")["body"]
    new_wire = sorted((run.BATCH / "cases/repair-candidate-1/wire").glob("*-request.json"))
    new = B.read(new_wire[0])["body"]
    settings_same = {k: v for k, v in request.items() if k != "messages"} == {k: v for k, v in new.items() if k != "messages"}
    facts = {
        "status": "EXPERIMENT_INVALID", "model_capability_verdict": "INCONCLUSIVE",
        "cause": "prepare copied the post-R2 raw-1 workspace instead of a SHA-bound pre-run input; pair equality did not establish origin fidelity",
        "expected_repair_sha256": correct, "actual_repair_sha256": wrong,
        "actual_matches_r2_post_result": wrong == B.read(P.R2 / "cases/raw-1/result.json")["source_sha256"],
        "cells": rows, "corrected_copy_only": str(root), "corrected_live_calls": 0,
        "corrected_baseline_check_exits": [row["exit_code"] for row in checks],
        "r2_vs_r3_model_sampling_transport_identical": settings_same,
        "r2_system_prompt_equal": request["messages"][0] == new["messages"][0],
        "r3_context_delta": "Additional packet metadata and receipts; validation failure is ruff-format outside function, not frozen E501. Causal input/context conclusions unavailable.",
        "next_live_requires_new_registration": True, "candidate_unchanged_after_freeze": True,
    }
    B.save(P.BATCH / "origin-audit.json", facts)
    print(json.dumps({"status": facts["status"], "correct": correct, "wrong": wrong, "settings_same": settings_same}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
