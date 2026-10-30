"""Original sixteen semantic controls with the frozen R3 Reviewer, no Coder credit."""

import argparse
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_r4_prepare as H

B, R = H.B, H.R
BATCH = H.BATCH / "reviewer-screen-v2"


def prepare():
    source_registration = B.read(H.REVIEWER_REGISTRATION)
    adjudications = B.read(
        H.REVIEWER_REGISTRATION.parent / "primary-adjudications-1.json"
    )
    expected = {row["id"]: row["expected"] for row in adjudications}
    current = B.read(
        H.S.BATCH / "cases/presence-candidate-1/isolated/.agent/config.json"
    )
    frozen = B.read(H.BATCH / "live-freeze-approved.json")
    R.assert_files(B.KIT, frozen["candidate_and_driver"])
    BATCH.mkdir(exist_ok=False)
    rows = []
    for item in source_registration["cells"]:
        origin = Path(item["root"])
        mutable = {
            ".agent/current-task.json",
            f".agent/tasks/{item['identity']['task_id']}/state.json",
        }
        R.assert_files(
            origin,
            {row["path"]: row["sha256"] for row in item["inputs"]},
            except_paths=mutable,
        )
        cell = BATCH / "cells" / item["id"]
        B.save(
            cell / "historical-index-audit.json",
            {
                "excluded_only_runtime_bookkeeping": [
                    {
                        "path": row["path"],
                        "before_live_sha256": row["sha256"],
                        "after_live_sha256": B.sha(origin / row["path"]),
                    }
                    for row in item["inputs"]
                    if row["path"] in mutable
                ],
                "all_source_tests_config_and_canonical_inputs_match_original_registration": True,
                "indexes_not_copied_or_worker_visible": True,
            },
        )
        root = cell / "isolated"
        H.P.copy_inputs(origin, root)
        identity = item["identity"]
        relative_run = (
            Path(".agent/tasks") / identity["task_id"] / "runs" / identity["run_id"]
        )
        shutil.copytree(origin / relative_run, root / relative_run)
        shutil.copytree(
            B.KIT / ".local-agents",
            root / ".local-agents",
            ignore=shutil.ignore_patterns(
                "tests", "__pycache__", "*.pyc", "config.json"
            ),
        )
        config = B.read(origin / ".agent/config.json")
        original_config = dict(config)
        # Preserve original trusted validation profiles; all Reviewer controls
        # use the same qualified current protocol/model/sampling configuration.
        for key in set(config) | set(current):
            if key.startswith(("reviewer_", "max_reviewer_")):
                config.pop(key, None)
                if key in current:
                    config[key] = current[key]
        for key in (
            "single_model_residency",
            "model_switch_timeout_seconds",
            "model_request_timeout_seconds",
            "model_load_backend",
            "model_load_cli_path",
            "model_context_safety_margin",
        ):
            if key in current:
                config[key] = current[key]
        request = {**identity, "review_id": "r4-frozen-" + item["id"]}
        B.save(root / ".agent/config.json", config)
        B.save(root / ".agent/r4-review-request.json", request)
        runtime_module = R.load(
            root / ".local-agents/reviewer-runtime.py",
            "r4_review_control_" + item["id"],
        )
        client = type("NoModel", (), {"native_tools": None})()
        runtime = runtime_module.ReviewerRuntime(root, request, config, client)
        assert runtime.max_turns == 16 and runtime.max_protocol_errors == 4
        runtime.initial_payload()
        files = {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)}
        rows.append(
            {
                "id": item["id"],
                "root": str(root),
                "expected_decision": expected[item["id"]],
                "identity": request,
                "files": files,
                "config_delta": {
                    key: {"before": original_config.get(key), "after": config.get(key)}
                    for key in set(original_config) | set(config)
                    if original_config.get(key) != config.get(key)
                },
            }
        )
    B.save(
        BATCH / "registration.json",
        {
            "registered": 16,
            "cells": rows,
            "source_registration_sha256": B.sha(H.REVIEWER_REGISTRATION),
            "criterion": "16/16 original substantive correctness; source-backed causal findings, not verdict-label matching",
            "candidate_and_driver": frozen["candidate_and_driver"],
            "synthetic_archives_not_coder_credit": True,
            "models_and_budgets_unchanged_from_transfer": True,
            "finish_current_screen_after_semantic_failure": True,
            "no_retries": True,
            "usage_ceiling": 30,
        },
    )
    print(
        "Sixteen original controls cloned and preflighted without model calls",
        flush=True,
    )


def run(name, used):
    assert 0 <= used < 30
    assert B.read(H.BATCH / "transfer-decision.json")["qualification"] in {
        "PASS",
        "HOLD",
    }
    seal = B.read(BATCH / "diagnostic-live-freeze.json")
    assert B.sha(Path(__file__)) == seal["driver"]
    assert B.sha(BATCH / "registration.json") == seal["registration"]
    assert (
        B.sha(BATCH / "diagnostic-registration.json") == seal["diagnostic_registration"]
    )
    registration = B.read(BATCH / "registration.json")
    R.assert_files(B.KIT, registration["candidate_and_driver"])
    rows = registration["cells"]
    item = next(row for row in rows if row["id"] == name)
    for previous in rows[: rows.index(item)]:
        assert (BATCH / "cells" / previous["id"] / "result.json").exists()
    cell, root = BATCH / "cells" / name, Path(item["root"])
    R.assert_files(root, item["files"])
    B.save(
        cell / "started.json",
        {"weekly_used": used, "at": time.time(), "no_retry": True},
    )
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(B.KIT / "benchmarks/r3_capture"),
        "R3_WIRE_DIR": str(cell / "wire"),
    }
    argv = [
        sys.executable,
        "-B",
        str(root / ".local-agents/local-review.py"),
        "--request",
        str(root / ".agent/r4-review-request.json"),
        "--config",
        str(root / ".agent/config.json"),
        "--report",
        str(cell / "reviewer.json"),
    ]
    started = time.monotonic()
    completed = subprocess.run(
        argv,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    B.save(
        cell / "entry-result.json",
        {
            "argv": argv,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "seconds": time.monotonic() - started,
        },
    )
    report = B.read(cell / "reviewer.json")
    drift = [
        path for path, digest in item["files"].items() if B.sha(root / path) != digest
    ]
    result = {
        "id": name,
        "observed": report.get("decision"),
        "failure_reason": report.get("failure_reason"),
        "infra_failure": report.get("infra_failure"),
        "expected": item["expected_decision"],
        "label_match_not_adjudication": report.get("decision")
        == item["expected_decision"],
        "protected_drift": drift,
        "seconds": time.monotonic() - started,
        "primary_adjudication": "pending",
    }
    B.save(cell / "result.json", result)
    print(result, flush=True)


def freeze():
    tree = ET.parse(BATCH / "controls-diagnostic.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + kind) for kind in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "diagnostic-live-freeze.json",
        {
            "driver": B.sha(Path(__file__)),
            "registration": B.sha(BATCH / "registration.json"),
            "tests": B.sha(B.KIT / "tests/test_harness_r4_reviewer.py"),
            "diagnostic_registration": B.sha(BATCH / "diagnostic-registration.json"),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "run", "freeze"])
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "run":
        run(args.case, args.used)
    else:
        freeze()
