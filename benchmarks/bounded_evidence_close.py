"""Close offline preparation after auditing concrete code, tasks and evidence."""

import ast
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_candidate as C
import bounded_evidence_support as S
import bounded_evidence_tasks as T


def passed(path, count):
    suite = ET.parse(path).getroot().find("testsuite")
    if (
        suite is None
        or int(suite.get("tests", "0")) != count
        or int(suite.get("errors", "0"))
        or int(suite.get("failures", "0"))
    ):
        raise ValueError("Required controls not passed: " + str(path))


def main():
    passed(S.BATCH / "controls-v4.xml", 18)
    passed(S.BATCH / "runner-controls-v2.xml", 7)
    candidate = S.read(S.BATCH / "candidate-freeze.json")
    if any(S.sha(p) != sha for p, sha in candidate["pins"].items()):
        raise ValueError("Candidate changed since protocol freeze")
    readiness = S.read(S.BATCH / "readiness-v2/readiness.json")
    if readiness["status"] != "OFFLINE_READY_FOR_SINGLE_LIVE_APPROVAL":
        raise ValueError("Readiness incomplete")
    if len(readiness["results"]["cells"]) != 12:
        raise ValueError("Not all installed cells checked")
    baseline = S.read(S.BATCH / "baseline.json")
    changed = [
        p for p, digest in baseline["files"].items() if S.sha(S.KIT / p) != digest
    ]
    allowed = {
        "benchmarks/bounded_evidence_support.py",
        "docs/local-model-harness-convergence-plan.md",
        "docs/bounded-evidence-interaction-design.md",
    }
    if set(changed) - allowed:
        raise ValueError("Pre-existing changes were altered: " + repr(changed))
    cells = S.read(S.BATCH / "cells-v4.json")
    task_freeze = S.read(S.BATCH / "task-freeze-v4.json")
    if task_freeze["candidate_freeze_sha256"] != S.sha(
        S.BATCH / "candidate-freeze.json"
    ):
        raise ValueError("Tasks do not bind the candidate freeze")
    upstream = {}
    for name, task in task_freeze["tasks"].items():
        root = Path(task["root"])
        original = ast.parse(
            T.extract(Path(task["origin"]["path"]), task["symbol"])
        ).body[0]
        isolated = next(
            n
            for n in ast.parse((root / "src/product/code.py").read_text()).body
            if isinstance(n, ast.FunctionDef)
        )
        original.decorator_list = []
        if name == "T3":
            original.args.args = original.args.args[1:]
        if ast.dump(original) != ast.dump(isolated):
            raise ValueError("Isolated function differs from declared upstream start")
        upstream[name] = {
            "upstream_hash_matches": S.sha(task["origin"]["path"])
            == task["origin"]["sha256"],
            "function_ast_matches_declared_adaptation": True,
        }
        if not upstream[name]["upstream_hash_matches"]:
            raise ValueError("Upstream source changed during preparation")
        private = S.BATCH / "task-preparation-v4/private" / name
        if (
            S.sha(private / "reference.py") != task["reference_sha256"]
            or S.sha(private / "test_independent.py") != task["private_test_sha256"]
        ):
            raise ValueError("Sealed reference or private acceptance changed")
    for row in cells.values():
        root = Path(row["root"])
        if any(S.sha(root / p) != digest for p, digest in row["files"].items()):
            raise ValueError("Prepared live input drift")
        if list((root / ".agent/tasks").glob("*/runs/*/completed.json")):
            raise ValueError("Live cell was executed during offline preparation")
    scripts = [
        "benchmarks/" + p.name
        for p in (S.KIT / "benchmarks").glob("bounded_evidence_*.py")
    ]
    scripts += [
        "tests/test_bounded_evidence_candidate.py",
        "tests/test_bounded_evidence_run.py",
    ]
    pins = {**candidate["pins"], **{str(S.KIT / p): S.sha(S.KIT / p) for p in scripts}}
    for path in [
        S.BATCH / p
        for p in (
            "candidate-freeze.json",
            "task-freeze-v4.json",
            "cells-v4.json",
            "readiness-v2/readiness.json",
            "controls-v4.xml",
        "runner-controls-v2.xml",
        )
    ]:
        pins[str(path)] = S.sha(path)
    for topic in T.TASKS:
        for path in (S.BATCH / "task-preparation-v4/private" / topic).glob("*.py"):
            pins[str(path)] = S.sha(path)
        for path in (S.BATCH / "readiness-v2/input-messages").glob(topic + "-*.json"):
            pins[str(path)] = S.sha(path)
    S.save(
        S.BATCH / "experiment-freeze-v2.json",
        {
            "pins": pins,
            "full_experiment_preparation": True,
            "candidate_frozen_before_task_selection": True,
        },
    )
    config = S.read(Path(cells["T1-A1"]["root"]) / ".agent/config.json")
    model_fields = {
        k: v
        for k, v in config.items()
        if k.startswith(("coder_", "reviewer_")) and k != "coder_single_function"
    }
    registration = {
        "status": "DRAFT_READY_AWAITING_NEW_HUMAN_LIVE_APPROVAL",
        "live_authorized": False,
        "batch": "bounded-evidence-prep-20261018-1",
        "order": T.ORDER,
        "registered_for_preparation": 12,
        "live_executed": 0,
        "candidate_freeze": "candidate-freeze.json",
        "task_freeze": "task-freeze-v4.json",
        "cells": "cells-v4.json",
        "experiment_freeze_sha256": S.sha(S.BATCH / "experiment-freeze-v2.json"),
        "pins": pins,
        "arm_difference": "B adds approved exact-file READ/SEARCH to A; same host, budget, initial factual materials, editor, checks and Reviewer",
        "common_budget": {
            **C.BUDGET,
            "output_per_request": 4096,
            "request_seconds": 180,
            "reviewer_requests": 16,
            "reviewer_protocol_errors": 4,
            "reviewer_seconds": 600,
            "model_load_seconds_each": 360,
            "unit_seconds": 2220,
            "batch_seconds": 10800,
            "weekly_used_ceiling": 15,
        },
        "model_config": model_fields,
        "context": {"coder": 24576, "reviewer": 24576},
        "resident_models": None,
        "actual_quantization": None,
        "actual_template": None,
        "inference_seed": None,
        "sampling": "Preserve pinned config; no model, quantization or template switch",
        "qualification_gate": "Per arm 6/6 and each task 2/2 independent complete-chain accepts; no assisted credit, no wrong-pass masking; no production or R5 admission",
        "comparison": "Report paired counts and evidence use; both6/6 is no completion-rate advantage; A improvement cannot all be attributed to B",
        "ordinary_failure": "Qualification HOLD, continue remaining registered diagnostics if safe and under budget; no failed-cell replacement",
        "safety_infrastructure_drift": "Stop new cells; preserve current evidence and partial edits; unstarted NOT_RUN",
        "reviewer": "Frozen fresh contract-first. Protocol recovery allowed within original budget; no substantive same-code same-evidence resampling",
        "assistance": "Any new semantic guidance, missing dependency location or code takeover separately assisted, not autonomous accept",
        "input_matching_caveat": "Initial facts equal after audit-only normalization of sandbox/JUnit paths, terminal elapsed and object repr addresses. Actual messages retained; not byte-identical inputs.",
        "cost": "Primary-only comparison absent; record intervention and time, unknown cloud tokens/active time remain null; weekly usage is only stop observation",
        "environment_precondition": "LM Studio service must be available. lms ps --json attempted service wake then timed out; no models loaded. B schema live compatibility unknown until authorized run",
        "tasks": {
            k: {
                key: value
                for key, value in task.items()
                if key
                in {
                    "kind",
                    "symbol",
                    "contract",
                    "interactions",
                    "origin",
                    "adaptations",
                    "exposure",
                }
            }
            for k, task in task_freeze["tasks"].items()
        },
    }
    S.save(S.BATCH / "registration-v2-draft.json", registration)
    commands = []
    for cell in T.ORDER:
        commands.append(
            {
                "cell": cell,
                "argv": [
                    str(S.PYTHON),
                    "-B",
                    str(S.KIT / "benchmarks/bounded_evidence_run.py"),
                    "--cell",
                    cell,
                    "--approval",
                    str(S.BATCH / "live-approval.json"),
                    "--weekly-used",
                    "<fresh_actual_used_below_15>",
                    "--usage-observed-at",
                    "<observation_unix_seconds_within_120s>",
                ],
                "after": "Inspect actual diff/contract and private checks; record Primary canonical review; classify Reviewer error/assistance. Do not rewrite result.json.",
            }
        )
    S.save(
        S.BATCH / "commands-v2.json",
        {
            "not_executed": True,
            "approval_binding": {
                "registration_sha256": S.sha(S.BATCH / "registration-v2-draft.json"),
                "human_approved_live": True,
            },
            "commands": commands,
        },
    )
    S.save(
        S.BATCH / "completion-audit-v2.json",
        {
            "original_objective": "Offline A/B preparation ready for consolidated approval",
            "candidate_and_protocol_frozen": True,
            "exact_tasks_and_compliant_solutions": 3,
            "installed_cells_checked": 12,
            "candidate_controls": 18,
            "runner_controls": 7,
            "offline_scripted_chains": 3,
            "actual_Worker_calls": 0,
            "upstream": upstream,
            "preexisting_changed_paths": changed,
            "history_candidate_pin_count": len(candidate["pins"]),
            "history_candidate_pin_mismatches": 0,
            "prepared_cells_unexecuted_and_unchanged": True,
            "registration_sha256": S.sha(S.BATCH / "registration-v2-draft.json"),
            "weekly_used_observed": 9,
            "weekly_ceiling": 15,
            "R4": "HOLD",
            "R5": "NOT_ADMITTED",
        },
    )
    S.save(
        S.BATCH / "decision-v2.json",
        {
            "status": "OFFLINE_PREPARATION_COMPLETE_AWAITING_HUMAN_LIVE_APPROVAL",
            "live_authorized": False,
            "live_executed": 0,
            "not_run": 12,
            "R4": "HOLD",
            "R5": "NOT_ADMITTED",
            "production_enabled": False,
            "stop_reason": "Requested offline preparation complete; user-required consolidated live approval pending, not budget exhaustion",
            "weekly_used": 9,
            "weekly_used_ceiling": 15,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "prior_failures_retained": [
                "controls-v3: missing original Reviewer opt-ins in test harness",
                "task prep v1: fixture imports and extracted helper export",
                "v2: reference Iterator typing",
                "v3: Ruff cache incorrectly included in source inputs",
                "readiness first comparisons: unnormalized execution metadata",
            ],
            "next": "One consolidated human approval of exact registration and LM Studio availability before any live",
        },
    )
    checked = subprocess.run(
        ["git", "diff", "--check"],
        cwd=S.KIT,
        capture_output=True,
        text=True,
        check=False,
    )
    if checked.returncode:
        raise ValueError(checked.stdout + checked.stderr)
    print(
        "Offline preparation audited; 12 live cells remain NOT_RUN; no live authorization created."
    )


if __name__ == "__main__":
    main()
