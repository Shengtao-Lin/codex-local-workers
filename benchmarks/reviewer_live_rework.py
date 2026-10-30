"""Two preregistered live repairs from unchanged frozen Reviewer controls.

Parents are copied synthetic Coder archives with real historical Reviewer calls.
Only children receive new Coder/Reviewer calls; no real-project credit is claimed.
"""

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from capability_fit import WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "reviewer-live-rework-1"
SNAPSHOT = WORK / "reviewer-live-rework-runtime-1"
SOURCE = WORK / "reviewer-evidence-1"
IDS = ("display-default-b-r1", "lookup-fallback-b-r1")


def invoke(root, name, argv):
    started = time.monotonic()
    p = subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1500,
        check=False,
    )
    result = {
        "exit": p.returncode,
        "seconds": time.monotonic() - started,
        "output": p.stdout + p.stderr,
    }
    write(root / f".agent/{name}-invocation.json", result)
    return result


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    worker = load_worker(SNAPSHOT)
    cells = {c["id"]: c for c in read(SOURCE / "registration.json")["controls"]}
    judgments = {c["id"]: c for c in read(SOURCE / "primary-adjudications-1.json")}
    rows = []
    for identity in IDS:
        old = Path(cells[identity]["root"])
        root = BASE / identity
        root.mkdir()
        for path in ("src", "tests"):
            shutil.copytree(old / path, root / path)
        shutil.copy2(old / "pyproject.toml", root / "pyproject.toml")
        config = read(old / ".agent/config.json")
        write(root / ".agent/config.json", config)
        report_path = next(
            (old / ".agent/tasks").glob("*/reviews/control-1/handoff.json")
        )
        report = read(report_path)
        task, parent = report["identity"]["task_id"], report["identity"]["run_id"]
        task_root = root / ".agent/tasks" / task
        shutil.copytree(
            old / ".agent/tasks" / task / "runs" / parent,
            task_root / "runs" / parent,
            ignore=shutil.ignore_patterns("review.json"),
        )
        shutil.copytree(report_path.parent, task_root / "reviews/control-1")
        write(
            task_root / "state.json",
            {
                "schema_version": 1,
                "task_id": task,
                "reviews": [],
                "completed_units": [],
                "recent_attempts": [],
                "usage": {},
            },
        )
        child = {
            "schema_version": 2,
            "task_id": task,
            "unit_id": "qual-unit",
            "run_id": parent[:-2] + "a2",
            "attempt": 2,
            "plan_revision": 1,
            "packet_revision": 2,
            "parent_run_id": parent,
            "preserve_contract": True,
            "review_feedback": [
                {
                    "finding_id": report["findings"][0]["id"],
                    "contract_id": "qual-unit",
                    "text": judgments[identity]["summary"],
                    "source_anchor": "display_name"
                    if identity.startswith("display")
                    else "lookup_or",
                    "verify_in_review": True,
                }
            ],
        }
        write(root / ".agent/child.json", child)
        try:
            worker.resolve_inherited_packet(root, child)
        except worker.WorkerError as exc:
            assert "Primary disposition" in str(exc)
            write(
                root / ".agent/unconfirmed-preflight.json",
                {"rejected": True, "error": str(exc), "model_calls": 0},
            )
        else:
            raise AssertionError("Unconfirmed repair was accepted")
        disposition = {
            "schema_version": 1,
            "authority": "primary",
            "identity": report["identity"],
            "report_sha256": digest(report_path),
            "resolution": "cleared",
            "evidence": [judgments[identity]["summary"]],
            "findings": [
                {
                    "finding_id": f["id"],
                    "disposition": "confirmed_defect",
                    "evidence": judgments[identity]["summary"],
                }
                for f in report["findings"]
            ],
        }
        write(root / ".agent/parent-disposition.json", disposition)
        result = invoke(
            root,
            "confirm-parent",
            [
                sys.executable,
                "-B",
                str(SNAPSHOT / ".local-agents/record-review.py"),
                "--repo",
                str(root),
                "--task-id",
                task,
                "--run-id",
                parent,
                "--decision",
                "rework",
                "--summary",
                judgments[identity]["summary"],
                "--disposition",
                str(root / ".agent/parent-disposition.json"),
            ],
        )
        assert result["exit"] == 0, result
        resolved = worker.resolve_inherited_packet(root, child)
        assert resolved["_inheritance"]["parent_input_state"]["status"] == "unchanged"
        rows.append(
            {
                "id": identity,
                "root": str(root),
                "original_root": str(old),
                "task_id": task,
                "parent_run_id": parent,
                "run_id": child["run_id"],
                "parent_synthetic": True,
                "original_report_sha256": digest(report_path),
                "protected": {
                    p: digest(root / p)
                    for p in (
                        "tests/test_target.py",
                        "pyproject.toml",
                        ".agent/config.json",
                    )
                },
                "before_source": (root / "src/product/target.py").read_text(
                    encoding="utf-8"
                ),
            }
        )
    write(
        BASE / "registration.json",
        {
            "cells": rows,
            "driver_sha256": digest(Path(__file__)),
            "gate": "Both actual children edit, validate, auto-review pass and pass independent boundary probes; no changed tests/config/contracts. One call per cell; no automatic retry.",
            "models_unchanged": True,
            "single_model_residency": True,
            "new_cases": 0,
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )
    print(json.dumps(rows, indent=2))


def run(identity):
    registration = read(BASE / "registration.json")
    assert digest(Path(__file__)) == registration["driver_sha256"]
    row = next(r for r in registration["cells"] if r["id"] == identity)
    root = Path(row["root"])
    for path, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        assert digest(SNAPSHOT / path) == sha, path
    result = invoke(
        root,
        "live-unit",
        [
            sys.executable,
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/child.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/child-coder.json"),
            "--review-report",
            str(root / ".agent/child-reviewer.json"),
        ],
    )
    print(json.dumps(result, indent=2))


def probe(identity):
    row = next(
        r for r in read(BASE / "registration.json")["cells"] if r["id"] == identity
    )
    root = Path(row["root"])
    for path, sha in row["protected"].items():
        assert digest(root / path) == sha, path
    spec = importlib.util.spec_from_file_location(
        "target", root / "src/product/target.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    facts = []
    if identity.startswith("display"):
        for record, expected in (
            ({"name": "Ada"}, "Ada"),
            ({"name": ""}, ""),
            ({"name": None}, None),
            ({}, "unnamed"),
        ):
            before = record.copy()
            actual = module.display_name(record)
            facts.append(
                {
                    "input": before,
                    "actual": actual,
                    "correct": actual == expected and record == before,
                }
            )
    else:
        for value in (0, False, "", None, object()):
            calls = []

            def fetch(key, calls=calls, value=value):
                calls.append(key)
                return value

            actual = module.lookup_or(fetch, "k", 99)
            facts.append(
                {
                    "probe": "value-identity",
                    "correct": actual is value and calls == ["k"],
                }
            )
        for error in (KeyError("missing"), RuntimeError("original")):
            calls = []

            def fetch(key, calls=calls, error=error):
                calls.append(key)
                raise error

            try:
                actual = module.lookup_or(fetch, "k", 99)
                correct = isinstance(error, KeyError) and actual == 99
            except (RuntimeError, KeyError) as caught:
                correct = isinstance(error, RuntimeError) and caught is error
            facts.append(
                {"probe": type(error).__name__, "correct": correct and calls == ["k"]}
            )
    result = {
        "facts": facts,
        "passed": all(f["correct"] for f in facts),
        "source": (root / "src/product/target.py").read_text(encoding="utf-8"),
        "source_sha256": digest(root / "src/product/target.py"),
        "protected_unchanged": True,
    }
    write(root / ".agent/independent-probe.json", result)
    print(json.dumps(result, indent=2))


def audit():
    registration = read(BASE / "registration.json")
    assert digest(BASE / "registered-driver.py") == registration["driver_sha256"]
    rows = []
    for row in registration["cells"]:
        root, old = Path(row["root"]), Path(row["original_root"])
        original_report = (
            old / ".agent/tasks" / row["task_id"] / "reviews/control-1/handoff.json"
        )
        assert digest(original_report) == row["original_report_sha256"]
        assert (old / "src/product/target.py").read_text(encoding="utf-8") == row[
            "before_source"
        ]
        for path, sha in row["protected"].items():
            assert digest(root / path) == digest(old / path) == sha
        coder = read(root / ".agent/child-coder.json")
        reviewer = read(root / ".agent/child-reviewer.json")
        run = root / ".agent/tasks" / row["task_id"] / "runs" / row["run_id"]
        assert coder["status"] == "ready_for_review"
        assert [c["path"] for c in coder["changed_files"]] == ["src/product/target.py"]
        assert coder["validation_summary"]["executed"] > 0
        assert coder["validation_summary"]["inputs_unchanged"]
        assert all(
            c["status"] == "passed"
            for c in coder["validation_summary"]["configured_checks"]
        )
        assert reviewer["decision"] == "pass_to_primary"
        assert reviewer["runtime_facts"]["inputs_unchanged"]
        assert set(reviewer["runtime_facts"]["read_paths"]) >= {
            "src/product/target.py",
            "tests/test_target.py",
        }
        assert set(reviewer["verified_check_ids"]) == {"ruff-format", "ruff-check"}
        assert reviewer["contract_review"][0]["status"] == "verified"
        assert read(run / "review.json")["decision"] == "accept"
        assert read(root / ".agent/unconfirmed-preflight.json")["rejected"]
        assert read(root / ".agent/independent-probe.json")["passed"]
        assert (run / "auto-review-request.json").is_file()
        rows.append(
            {
                "id": row["id"],
                "accepted": True,
                "command_seconds": read(root / ".agent/live-unit-invocation.json")[
                    "seconds"
                ],
                "reviewer_protocol_errors": reviewer["runtime_facts"][
                    "protocol_error_count"
                ],
                "coder_validation_attempts": len(
                    list(run.glob("validation-attempt-*.json"))
                ),
                "reviewer_id": reviewer["identity"]["review_id"],
            }
        )
    for path, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        assert digest(SNAPSHOT / path) == sha
    write(
        BASE / "stage-decision.json",
        {
            "decision": "controlled_rework_chain_pass",
            "passed": 2,
            "total": 2,
            "rows": rows,
            "new_coder_calls": 2,
            "new_reviewer_calls": 2,
            "synthetic_parents": True,
            "real_project_credit": False,
            "formal_reviewer_semantic_gate": "HOLD",
            "coordinator_enabled": False,
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "weekly_used_last_observed": 46,
            "weekly_used_ceiling": 50,
            "stop_reason": "Preregistered bounded experiment conclusion, not formal product release",
            "audit_driver_sha256": digest(Path(__file__)),
        },
    )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "probe", "audit"))
    parser.add_argument("--id", choices=IDS)
    args = parser.parse_args()
    if args.action in {"prepare", "audit"}:
        globals()[args.action]()
    else:
        globals()[args.action](args.id)
