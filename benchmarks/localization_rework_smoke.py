"""One Primary-authorized rework of a completed frozen localization failure."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import stability_e2e as STABILITY


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument(
        "--parent-run",
        choices=("sample-identity-a1", "sample-identity-a2"),
        default="sample-identity-a1",
    )
    args = parser.parse_args()
    root = args.snapshot.resolve()
    plan_path = root / ".agent" / "feature-plan.json"
    old_path = (
        root
        / ".agent"
        / ("packet.json" if args.parent_run.endswith("a1") else "packet-a2.json")
    )
    request_path = root / ".agent" / "localization-request.json"
    plan, old, request = map(read_json, (plan_path, old_path, request_path))
    if old["unit_id"] != "sample-identity" or old["run_id"] != args.parent_run:
        parser.error("the frozen packet does not match the named parent run")
    next_attempt = old["attempt"] + 1
    new_run_id = f"sample-identity-a{next_attempt}"
    run_root = root / ".agent" / "tasks" / old["task_id"] / "runs" / old["run_id"]
    completed_path = run_root / "completed.json"
    if read_json(completed_path).get("status") != "failed":
        parser.error("the parent Coder run must be completed with status failed")
    state = read_json(
        root / ".agent" / "coordinator" / old["feature_id"] / "state.json"
    )
    if (
        state["sequence"] != 2 * old["attempt"] - 1
        or state["units"][old["unit_id"]]["phase"] != "running"
    ):
        parser.error("the frozen parent run is not at the expected recovery boundary")
    new_path = root / ".agent" / f"packet-a{next_attempt}.json"
    if new_path.exists():
        parser.error("the next rework packet already exists; never replay a run id")

    spec = importlib.util.spec_from_file_location(
        "frozen_rework_contract",
        STABILITY.KIT / ".local-agents" / "coordinator-contract.py",
    )
    assert spec is not None and spec.loader is not None
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)

    authorization_path = (
        root
        / ".agent"
        / "primary-reviews"
        / old["feature_id"]
        / "recovery"
        / f"{old['run_id']}.json"
    )
    STABILITY.write_json(
        authorization_path,
        {
            "schema_version": 1,
            "feature_id": old["feature_id"],
            "task_id": old["task_id"],
            "unit_id": old["unit_id"],
            "failed_run_id": old["run_id"],
            "new_run_id": new_run_id,
            "primary_plan_sha256": contract.authority_fingerprint(plan),
            "failed_packet_sha256": sha256(old_path),
            "archived_packet_sha256": sha256(run_root / "packet.json"),
            "completed_sha256": sha256(completed_path),
            "expected_sequence": state["sequence"],
            "decision": "REWORK_LOCAL",
            "reason_code": "focused-tests-failed"
            if next_attempt == 2
            else "diff-quality-failed",
            "primary_rationale": (
                "The archived focused tests fail because the current dedup payload "
                "retains sample_id and bypasses JSON-mode serialization; the prior "
                "fingerprint edit already satisfies its focused assertions."
                if next_attempt == 2
                else "The a2 semantic tests passed 6/6 independently, but its deterministic "
                "quality gate rejected introduced trailing whitespace; Ruff also reports "
                "an unused sample_dict binding. Rework only those exact source issues."
            ),
        },
    )
    if next_attempt == 2:
        guidance = (
            "Inherited rework from sample-identity-a1: inspect the current dedup "
            "payload and the archived failing JUnit before editing. The existing "
            "fingerprint loop removes VOLATILE_CONTENT_FIELDS and already passed "
            "its focused assertions; preserve it. In dedup, the hand-built sample "
            "mapping plus separate sample_id is wrong. Preserve every sample field "
            "except sample_id by serializing the model in JSON mode with that one "
            "field excluded. Do not change scorer/config payload or sorted-key JSON. "
            "Use a narrow current-source edit and rerun focused tests."
        )
        goal = "Repair score_reuse_key while preserving the passing content_fingerprint change."
        modify = old["scope"]["modify"]
        targets = old["edit_targets"]
    else:
        guidance = (
            "Inherited rework from sample-identity-a2: six focused tests pass. "
            "Change only src/evaluation_harness/evaluations/dedup.py. Remove the unused "
            "sample_dict assignment at line 26 and its redundant comment; remove the "
            "whitespace-only line at line 29. Keep the current JSON-mode model_dump "
            'exclude={"sample_id"} payload, scorer/config fields, and digest behavior. '
            "Validate with the configured quality and focused checks."
        )
        goal = "Clear the exact a2 diff-quality and Ruff defects without changing behavior."
        modify = ["src/evaluation_harness/evaluations/dedup.py"]
        targets = [{"path": modify[0], "anchor": "sample_dict = sample.model_dump"}]
    new_packet = contract.materialize_bounded_packet(
        plan,
        {
            "unit_id": old["unit_id"],
            "run_id": new_run_id,
            "attempt": next_attempt,
            "packet_revision": next_attempt,
            "goal": goal,
            "scope": {
                "read": old["scope"]["read"],
                "modify": modify,
                "create": old["scope"]["create"],
            },
            "edit_targets": targets,
            "focused_tests": old["focused_tests"],
            "supplemental_tests": old["supplemental_tests"],
            "implementation_guidance": [guidance],
        },
    )
    STABILITY.write_json(new_path, new_packet)
    route = STABILITY.KIT / ".local-agents" / "coordinator-localization.py"
    recovery = STABILITY.run_command(
        root,
        [
            sys.executable,
            str(route),
            "--plan",
            str(plan_path),
            "--packet",
            str(old_path),
            "--recover-terminal",
            "--authorization",
            str(authorization_path),
        ],
        90,
    )
    if recovery.returncode != 0:
        print(json.dumps({"stage": "recovery", "result": recovery.stdout[-1200:]}))
        return 2
    config_path = root / ".local-agents" / "config.json"
    report_path = root / ".agent" / "explorer-rework-report.json"
    exploration = STABILITY.run_command(
        root,
        [
            sys.executable,
            str(STABILITY.KIT / ".local-agents" / "local-explore.py"),
            "--task",
            request["question"],
            "--task-id",
            old["task_id"],
            "--config",
            str(config_path),
            "--report",
            str(report_path),
            "--full-report",
        ],
        600,
    )
    if exploration.returncode != 0:
        print(json.dumps({"stage": "explorer", "result": exploration.stdout[-1200:]}))
        return 2
    dispatch = STABILITY.run_command(
        root,
        [
            sys.executable,
            str(route),
            "--plan",
            str(plan_path),
            "--packet",
            str(new_path),
            "--request",
            str(request_path),
            "--explorer-report",
            str(report_path),
            "--authorization",
            str(authorization_path),
            "--config",
            str(config_path),
        ],
        1200,
    )
    test = STABILITY.run_command(
        root,
        [sys.executable, "-m", "pytest", "tests/test_sample_identity.py", "-q"],
        90,
    )
    print(
        json.dumps(
            {
                "snapshot": str(root),
                "recovery": json.loads(recovery.stdout),
                "explorer_status": read_json(report_path).get("status"),
                "dispatch_exit": dispatch.returncode,
                "dispatch": json.loads(dispatch.stdout),
                "independent_tests_passed": test.returncode == 0,
                "independent_test_tail": test.stdout[-500:],
            },
            ensure_ascii=False,
        )
    )
    return 0 if dispatch.returncode == 0 and test.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
