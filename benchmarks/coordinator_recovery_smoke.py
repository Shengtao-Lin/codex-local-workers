"""Explicit Primary-authorized recovery of a real diagnostic failed run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import localization_route_smoke as SMOKE
import stability_e2e as STABILITY


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TypeError("expected object")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--authorize-terminal", action="store_true")
    args = parser.parse_args()
    if not args.authorize_terminal:
        parser.error("explicit Primary terminal recovery authorization required")
    root = args.workspace.resolve()
    if not root.is_relative_to(STABILITY.WORK.resolve()):
        parser.error("diagnostic recovery must remain inside benchmark work")
    observed = read(root / "route-result.json")
    if (
        not observed.get("diagnostic_fault_injection")
        or observed["route"]["unit_result"]["status"] != "failed"
    ):
        raise ValueError("requires a real terminal failed fault-injection run")
    spec = importlib.util.spec_from_file_location(
        "recovery_smoke_entry",
        STABILITY.KIT / ".local-agents/coordinator-supervised.py",
    )
    assert spec and spec.loader
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    plan = read(root / ".agent/feature-plan.json")
    old_path = Path(observed["coordinator"]["archive"]) / "packet.json"
    entry.CONTRACT._state_path(root, old_path)
    old = read(old_path)
    state_path = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    inspection = entry.ROUTE.inspect_running_dispatch(
        repo_root=root, plan=plan, packet_path=old_path, state_path=state_path
    )
    if inspection["status"] != "coder_not_ready":
        raise ValueError(
            "run is not recoverable; inspect process/archive rather than replay"
        )
    parent = root / ".agent/tasks" / old["task_id"] / "runs" / old["run_id"]
    if read(parent / "completed.json")["status"] != "failed":
        raise ValueError("unknown/interrupted runs are not retryable")
    marker = root / ".agent/recovery-smoke"
    entry.CONTRACT._state_path(root, marker / "result.json")
    marker.mkdir(exist_ok=False)
    state = entry.CONTRACT.load_coordinator_state(plan, root, state_path)
    identity = {
        "unit_id": old["unit_id"],
        "run_id": old["unit_id"] + "-a2",
        "attempt": old["attempt"] + 1,
        "packet_revision": old["packet_revision"] + 1,
    }
    authorization = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "task_id": plan["task_id"],
        "unit_id": old["unit_id"],
        "failed_run_id": old["run_id"],
        "new_run_id": identity["run_id"],
        "primary_plan_sha256": entry.CONTRACT.authority_fingerprint(plan),
        "failed_packet_sha256": digest(old_path),
        "archived_packet_sha256": digest(parent / "packet.json"),
        "completed_sha256": digest(parent / "completed.json"),
        "expected_sequence": state["sequence"],
        "decision": "REWORK_LOCAL",
        "reason_code": "diagnostic-turn-limit",
        "primary_rationale": "Primary inspected terminal failed archive and actual cumulative diff; restore normal budget for bounded recovery diagnostics only.",
    }
    auth_path = (
        root
        / ".agent/primary-reviews"
        / plan["feature_id"]
        / "recovery"
        / f"{old['run_id']}.json"
    )
    entry.CONTRACT._state_path(root, auth_path)
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    entry._write_once(auth_path, authorization)
    recovery = entry.ROUTE.recover_terminal_failed_unit(
        repo_root=root,
        plan=plan,
        failed_packet_path=old_path,
        state_path=state_path,
        authorization_path=auth_path,
        run_refs={},
    )
    entry._write_once(marker / "recovery-transition.json", recovery)
    config = read(root / ".local-agents/config.json")
    normal = read(STABILITY.KIT / ".local-agents/config.json")
    for key in (
        "max_model_turns",
        "hard_max_model_turns",
        "repair_turn_reserve",
        "prevalidation_edit_turn_reserve",
    ):
        config[key] = normal[key]
    config_path = marker / "normal-budget-config.json"
    entry._write_once(config_path, config)
    provenance = SMOKE.runtime_manifest(config)
    provenance["recovery_runner_sha256"] = digest(Path(__file__))
    context = {
        "identity": identity,
        "goal": old["goal"],
        "navigation_targets": old["edit_targets"],
        "inherited_rework": {
            "failed_run_id": old["run_id"],
            "reason": "one-turn diagnostic budget exhausted before validation",
        },
    }
    entry._write_once(marker / "context.json", context)
    request = read(root / ".agent/localization-request.json")
    explorer = read(Path(observed["explorer_report"]))
    client = entry.MODEL.WORKER.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        structured_output=False,
        timeout=config.get("coordinator_request_timeout_seconds", 360),
        max_tokens=config.get("coordinator_max_tokens", 4096),
        context_length=config["coordinator_context_length"],
    )
    code, result = entry.run_step(
        root=root,
        plan=plan,
        context=context,
        request=request,
        explorer=explorer,
        run_refs={},
        config=config,
        config_path=config_path,
        authorized=True,
        expected_sequence=recovery["state_sequence"],
        client=client,
        manage_exploration=True,
        recovery_authorization_path=auth_path,
    )
    tests = STABILITY.run_command(
        root, [sys.executable, "-m", "pytest", *old["focused_tests"], "-q"], 90
    )
    lint = STABILITY.run_command(
        root, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
    )
    fmt = STABILITY.run_command(
        root, [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"], 90
    )
    drift = (
        SMOKE.runtime_manifest(config)["runtime_sha256"] != provenance["runtime_sha256"]
        or digest(Path(__file__)) != provenance["recovery_runner_sha256"]
    )
    passed = (
        code == 0
        and result["status"] == "primary_review_required"
        and result["unit_result"]["unit_result"]["reviewer_decision"]
        == "pass_to_primary"
        and tests.returncode == lint.returncode == fmt.returncode == 0
        and not drift
    )
    final = {
        "status": "recovery_diagnostic_passed"
        if passed
        else "primary_attention_required",
        "scope": "terminal-failure-mechanics-only",
        "feature_accepted": False,
        "counts_as_normal_model_success": False,
        "result": result,
        "independent_tests_passed": tests.returncode == 0,
        "independent_static_passed": lint.returncode == fmt.returncode == 0,
        "runtime_changed": drift,
        "provenance": provenance,
    }
    entry._write_once(marker / "result.json", final)
    print(json.dumps(final, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
