"""Restricted v2.1 route from a verified locator report to one local unit.

This entry point never accepts a feature or supplies a semantic verdict.
Primary supplies the plan, packet, and full Explorer report. A separate
Explorer invocation must have used ``explorer_mode=locate``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CONTRACT = _load("coordinator_localization_contract", "coordinator-contract.py")
UNIT = _load("coordinator_localization_unit", "local-unit.py")


def _object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _dispatch_record_path(repo_root: Path, plan: dict, packet: dict) -> Path:
    feature_id = CONTRACT.identifier(plan["feature_id"], "feature_id")
    run_id = CONTRACT.identifier(packet["run_id"], "run_id")
    return repo_root / ".agent" / "coordinator" / feature_id / "dispatches" / f"{run_id}.json"


def _record_dispatch(
    repo_root: Path,
    plan: dict,
    packet: dict,
    packet_path: Path,
    request: dict,
    explorer_report: dict,
    state_sequence: int,
    source_refs: list[dict],
) -> Path:
    path = _dispatch_record_path(repo_root, plan, packet)
    CONTRACT._state_path(repo_root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT._state_path(repo_root, path)
    record = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "task_id": packet["task_id"],
        "unit_id": packet["unit_id"],
        "run_id": packet["run_id"],
        "primary_plan_sha256": CONTRACT.authority_fingerprint(plan),
        "packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        "explorer_report_sha256": hashlib.sha256(
            json.dumps(explorer_report, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "capability": request["capability"],
        "state_sequence_before": state_sequence,
        "source_refs": [
            {key: ref[key] for key in ("path", "start_line", "end_line", "kind", "source_hash")}
            for ref in source_refs
        ],
    }
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError("Coordinator run_id already has a dispatch record") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return path


def _recovery_authorization(repo_root: Path, plan: dict, path: Path, failed_run_id: str) -> dict:
    expected = (
        repo_root
        / ".agent"
        / "primary-reviews"
        / CONTRACT.identifier(plan["feature_id"], "feature_id")
        / "recovery"
        / f"{CONTRACT.identifier(failed_run_id, 'failed_run_id')}.json"
    )
    if path.absolute() != expected.absolute():
        raise ValueError("recovery authorization must use the Primary review path")
    CONTRACT._state_path(repo_root, path)
    value = _object(path)
    fields = {
        "schema_version",
        "feature_id",
        "task_id",
        "unit_id",
        "failed_run_id",
        "new_run_id",
        "primary_plan_sha256",
        "failed_packet_sha256",
        "archived_packet_sha256",
        "completed_sha256",
        "expected_sequence",
        "decision",
        "reason_code",
        "primary_rationale",
    }
    if set(value) != fields or value["schema_version"] != 1:
        raise ValueError("recovery authorization shape is invalid")
    if (
        value["feature_id"] != plan["feature_id"]
        or value["task_id"] != plan["task_id"]
        or value["failed_run_id"] != failed_run_id
        or value["primary_plan_sha256"] != CONTRACT.authority_fingerprint(plan)
        or value["decision"] != "REWORK_LOCAL"
    ):
        raise ValueError("recovery authorization differs from Primary plan or failed run")
    CONTRACT.identifier(value["unit_id"], "unit_id")
    CONTRACT.identifier(value["new_run_id"], "new_run_id")
    CONTRACT.identifier(value["reason_code"], "reason_code")
    if value["new_run_id"] == failed_run_id:
        raise ValueError("recovery requires a fresh run_id")
    if type(value["expected_sequence"]) is not int or value["expected_sequence"] < 1:
        raise ValueError("recovery expected_sequence is invalid")
    if not isinstance(value["primary_rationale"], str) or not value["primary_rationale"].strip():
        raise ValueError("recovery needs a Primary rationale")
    return value


def run_localization_unit(
    *,
    repo_root: Path,
    plan: dict,
    packet_path: Path,
    request: dict,
    explorer_report: dict,
    state_path: Path,
    run_refs: dict,
    config_path: Path,
    coder_report_path: Path,
    review_report_path: Path,
    recovery_authorization_path: Path | None = None,
    unit_runner: Callable[..., tuple[int, dict]] = UNIT.run_unit,
) -> tuple[int, dict]:
    """Route exactly one validated packet; leave acceptance to Primary."""
    packet = _object(packet_path)
    evidence = CONTRACT.validate_localization_dispatch(
        plan, packet, request, explorer_report, repo_root=repo_root
    )
    state = CONTRACT.load_coordinator_state(plan, repo_root, state_path)
    phase = state["units"][packet["unit_id"]]["phase"]
    if phase not in {"pending", "rework"}:
        raise ValueError("unit is already running or escalated; Primary recovery required")
    if phase == "rework":
        if recovery_authorization_path is None:
            raise ValueError("rework dispatch needs Primary recovery authorization")
        failed_run_id = recovery_authorization_path.stem
        authorization = _recovery_authorization(
            repo_root, plan, recovery_authorization_path, failed_run_id
        )
        if (
            authorization["unit_id"] != packet["unit_id"]
            or authorization["new_run_id"] != packet["run_id"]
            or authorization["expected_sequence"] + 1 != state["sequence"]
        ):
            raise ValueError("rework dispatch differs from Primary recovery authorization")
        old_root = repo_root / ".agent" / "tasks" / packet["task_id"] / "runs" / failed_run_id
        old_path = old_root / "packet.json"
        completed_path = old_root / "completed.json"
        if (
            not old_path.is_file()
            or not completed_path.is_file()
            or hashlib.sha256(old_path.read_bytes()).hexdigest()
            != authorization["archived_packet_sha256"]
            or hashlib.sha256(completed_path.read_bytes()).hexdigest()
            != authorization["completed_sha256"]
            or _object(completed_path).get("status") != "failed"
        ):
            raise ValueError("rework parent archive is stale or not terminal failed")
        old_packet = CONTRACT.validate_unit_packet(plan, _object(old_path))
        new_packet = CONTRACT.validate_unit_packet(plan, packet)
        for key in ("read", "modify", "create"):
            if not set(new_packet["scope"][key]) <= set(old_packet["scope"][key]):
                raise ValueError(f"rework packet expands prior {key} scope")
        for key in ("readonly", "forbidden"):
            if not set(old_packet["scope"][key]) <= set(new_packet["scope"][key]):
                raise ValueError(f"rework packet weakens prior {key} protection")
    elif recovery_authorization_path is not None:
        raise ValueError("initial dispatch must not use recovery authorization")
    decision = {"decision": "CONTINUE", "unit_id": packet["unit_id"]}
    CONTRACT.apply_coordinator_decision(
        plan,
        state,
        decision,
        expected_sequence=state["sequence"],
        repo_root=repo_root,
        run_refs=run_refs,
    )
    dispatch_record = _record_dispatch(
        repo_root,
        plan,
        packet,
        packet_path,
        request,
        explorer_report,
        state["sequence"],
        evidence["source_refs"],
    )
    updated = CONTRACT.persist_coordinator_transition(
        plan,
        repo_root,
        state_path,
        expected_sequence=state["sequence"],
        transition=lambda current: CONTRACT.apply_coordinator_decision(
            plan,
            current,
            decision,
            expected_sequence=current["sequence"],
            repo_root=repo_root,
            run_refs=run_refs,
        ),
    )
    try:
        code, result = unit_runner(
            repo_root, packet_path, config_path, coder_report_path, review_report_path
        )
    except Exception as exc:
        # The unit may have launched before this exception. Record the failure,
        # but leave it running so only Primary can inspect archives and recover.
        failed = CONTRACT.persist_coordinator_transition(
            plan,
            repo_root,
            state_path,
            expected_sequence=updated["sequence"],
            transition=lambda current: CONTRACT.record_infra_failure(
                plan, current, packet["unit_id"], "unit-launch-failure"
            ),
        )
        return 2, {
            "status": "primary_attention_required",
            "capability": evidence["capability"],
            "unit_id": packet["unit_id"],
            "state_sequence": failed["sequence"],
            "stage": "unit_launch",
            "reason": f"{type(exc).__name__}: {exc}",
            "unit_phase": "running",
            "dispatch_record": str(dispatch_record),
            "next_action_required": "primary_inspect_archives_before_recovery",
        }
    return code, {
        "status": "primary_review_required" if code == 0 else "primary_attention_required",
        "capability": evidence["capability"],
        "unit_id": packet["unit_id"],
        "state_sequence": updated["sequence"],
        "dispatch_record": str(dispatch_record),
        "explorer_source_refs": len(evidence["source_refs"]),
        "unit_result": result,
    }


def inspect_running_dispatch(
    *, repo_root: Path, plan: dict, packet_path: Path, state_path: Path
) -> dict:
    """Read-only restart reconciliation; never retry or accept a unit."""
    packet = _object(packet_path)
    CONTRACT.validate_unit_packet(plan, packet)
    state = CONTRACT.load_coordinator_state(plan, repo_root, state_path)
    if state["units"][packet["unit_id"]]["phase"] != "running":
        raise ValueError("unit is not running")
    record_path = _dispatch_record_path(repo_root, plan, packet)
    record = _object(record_path)
    if (
        record.get("schema_version") != 1
        or record.get("primary_plan_sha256") != CONTRACT.authority_fingerprint(plan)
        or record.get("packet_sha256") != hashlib.sha256(packet_path.read_bytes()).hexdigest()
        or record.get("task_id") != packet["task_id"]
        or record.get("unit_id") != packet["unit_id"]
        or record.get("run_id") != packet["run_id"]
        or record.get("capability") != "localization_only"
        or type(record.get("state_sequence_before")) is not int
        or state["sequence"] <= record["state_sequence_before"]
    ):
        raise ValueError("dispatch record is stale or inconsistent")
    result = {
        "unit_id": packet["unit_id"],
        "run_id": packet["run_id"],
        "state_sequence": state["sequence"],
        "dispatch_record": str(record_path),
        "automatic_retry_allowed": False,
    }
    run_root = repo_root / ".agent" / "tasks" / packet["task_id"] / "runs" / packet["run_id"]
    completed_path = run_root / "completed.json"
    if not completed_path.is_file():
        return {
            **result,
            "status": "archive_missing_or_incomplete",
            "next_action_required": "primary_inspect_process_and_archive",
        }
    completed = _object(completed_path)
    if completed.get("status") != "ready_for_review":
        return {
            **result,
            "status": "coder_not_ready",
            "next_action_required": "primary_inspect_failed_run",
        }
    try:
        UNIT.verify_handoff(
            repo_root,
            {
                "status": "ready_for_review",
                "identity": {
                    "task_id": packet["task_id"],
                    "unit_id": packet["unit_id"],
                    "run_id": packet["run_id"],
                },
            },
        )
    except (UNIT.HandoffError, OSError, ValueError) as exc:
        return {
            **result,
            "status": "handoff_invalid",
            "reason": str(exc),
            "next_action_required": "primary_inspect_handoff",
        }
    review_decisions = []
    for name in ("auto-review-request.json", "auto-review-retry-request.json"):
        request_path = run_root / name
        if not request_path.is_file():
            continue
        review_id = _object(request_path).get("review_id")
        if not isinstance(review_id, str) or not review_id.startswith("auto-"):
            continue
        try:
            CONTRACT.identifier(review_id, "review_id")
        except ValueError:
            continue
        review_path = (
            repo_root
            / ".agent"
            / "tasks"
            / packet["task_id"]
            / "reviews"
            / review_id
            / "handoff.json"
        )
        if review_path.is_file():
            review = _object(review_path)
            identity = review.get("identity") or {}
            if (
                all(identity.get(key) == packet[key] for key in ("task_id", "unit_id", "run_id"))
                and identity.get("review_id") == review_id
            ):
                review_decisions.append(review.get("decision"))
    if "pass_to_primary" in review_decisions:
        return {
            **result,
            "status": "reviewed_for_primary",
            "next_action_required": "primary_review_by_risk_route",
        }
    return {
        **result,
        "status": "review_missing_or_attention_required",
        "review_decisions": review_decisions,
        "next_action_required": "primary_inspect_reviewer_archive",
    }


def recover_terminal_failed_unit(
    *,
    repo_root: Path,
    plan: dict,
    failed_packet_path: Path,
    state_path: Path,
    authorization_path: Path,
    run_refs: dict,
) -> dict:
    """Apply one Primary-authorized rework transition, never launch a worker."""
    failed_packet = _object(failed_packet_path)
    inspection = inspect_running_dispatch(
        repo_root=repo_root,
        plan=plan,
        packet_path=failed_packet_path,
        state_path=state_path,
    )
    if inspection["status"] != "coder_not_ready":
        raise ValueError("only a completed failed Coder run may enter terminal rework")
    run_root = (
        repo_root / ".agent" / "tasks" / failed_packet["task_id"] / "runs" / failed_packet["run_id"]
    )
    completed_path = run_root / "completed.json"
    if _object(completed_path).get("status") != "failed":
        raise ValueError("terminal recovery requires completed Coder status failed")
    authorization = _recovery_authorization(
        repo_root, plan, authorization_path, failed_packet["run_id"]
    )
    state = CONTRACT.load_coordinator_state(plan, repo_root, state_path)
    if (
        authorization["unit_id"] != failed_packet["unit_id"]
        or authorization["expected_sequence"] != state["sequence"]
        or authorization["failed_packet_sha256"]
        != hashlib.sha256(failed_packet_path.read_bytes()).hexdigest()
        or authorization["completed_sha256"]
        != hashlib.sha256(completed_path.read_bytes()).hexdigest()
    ):
        raise ValueError("recovery authorization is stale or names different archive evidence")
    archived_packet_path = run_root / "packet.json"
    if (
        not archived_packet_path.is_file()
        or authorization["archived_packet_sha256"]
        != hashlib.sha256(archived_packet_path.read_bytes()).hexdigest()
        or CONTRACT.validate_unit_packet(plan, _object(archived_packet_path))
        != CONTRACT.validate_unit_packet(plan, failed_packet)
    ):
        raise ValueError("recovery authorization does not match canonical packet archive")
    reason_code = authorization["reason_code"]
    updated = CONTRACT.persist_coordinator_transition(
        plan,
        repo_root,
        state_path,
        expected_sequence=state["sequence"],
        transition=lambda current: CONTRACT.apply_coordinator_decision(
            plan,
            current,
            {
                "decision": "REWORK_LOCAL",
                "unit_id": failed_packet["unit_id"],
                "reason_code": reason_code,
            },
            expected_sequence=current["sequence"],
            repo_root=repo_root,
            run_refs=run_refs,
        ),
    )
    return {
        "status": "primary_authorized_rework",
        "unit_id": failed_packet["unit_id"],
        "failed_run_id": failed_packet["run_id"],
        "authorized_new_run_id": authorization["new_run_id"],
        "state_sequence": updated["sequence"],
        "next_action_required": "primary_supply_new_bounded_packet_and_fresh_locator_evidence",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--explorer-report", type=Path)
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--recover-terminal", action="store_true")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--run-refs", type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--state", type=Path)
    parser.add_argument(
        "--coder-report", type=Path, default=Path(".agent/last-local-coder-report.json")
    )
    parser.add_argument(
        "--review-report", type=Path, default=Path(".agent/last-local-review-report.json")
    )
    args = parser.parse_args()
    root = Path.cwd().resolve()
    plan = _object(args.plan)
    state_path = args.state or root / ".agent" / "coordinator" / plan["feature_id"] / "state.json"
    try:
        if args.inspect_only and args.recover_terminal:
            parser.error("choose either --inspect-only or --recover-terminal")
        if args.inspect_only:
            result = inspect_running_dispatch(
                repo_root=root,
                plan=plan,
                packet_path=args.packet.resolve(),
                state_path=state_path,
            )
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.recover_terminal:
            if args.authorization is None:
                parser.error("--recover-terminal requires --authorization")
            result = recover_terminal_failed_unit(
                repo_root=root,
                plan=plan,
                failed_packet_path=args.packet.resolve(),
                state_path=state_path,
                authorization_path=args.authorization.resolve(),
                run_refs=_object(args.run_refs) if args.run_refs else {},
            )
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.request is None or args.explorer_report is None:
            parser.error("dispatch requires --request and --explorer-report")
        code, result = run_localization_unit(
            repo_root=root,
            plan=plan,
            packet_path=args.packet.resolve(),
            request=_object(args.request),
            explorer_report=_object(args.explorer_report),
            state_path=state_path,
            run_refs=_object(args.run_refs) if args.run_refs else {},
            config_path=args.config.resolve(),
            coder_report_path=args.coder_report.resolve(),
            review_report_path=args.review_report.resolve(),
            recovery_authorization_path=(
                args.authorization.resolve() if args.authorization else None
            ),
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 3
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
