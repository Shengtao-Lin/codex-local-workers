"""Run and persist model-by-role protocol compatibility evidence."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import live_smoke

KIT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "v1.2"

REQUIRED_ACTIONS = {
    "explorer": {"SEARCH", "REGEX_SEARCH", "READ_FILE", "TRACE", "FINISH_SUCCESS"},
    "coder": {"READ_FILE", "SEARCH", "SAFE_CREATE", "SAFE_REPLACE", "VALIDATE"},
    "reviewer": {
        "READ_FILE",
        "SEARCH",
        "RUN_APPROVED_TEST",
        "RUN_APPROVED_STATIC_CHECK",
        "REPORT",
    },
}


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    return value if isinstance(value, dict) else {}


def _events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    result = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            result.append(item)
    return result


def _event_actions(events: list[dict[str, Any]]) -> set[str]:
    actions = set()
    for item in events:
        if item.get("event") not in {"tool_action", "diagnostic_action"}:
            continue
        facts = item.get("facts", {})
        action = facts.get("action") if isinstance(facts, dict) else None
        if isinstance(action, str) and (
            facts.get("status") in {"ok", "passed"}
            or (action == "VALIDATE" and facts.get("status") == "failed")
        ):
            actions.add(action)
    return actions


def _capabilities(actions: set[str], required: set[str]) -> dict[str, str]:
    return {
        action: "pass" if action in actions else "not_exercised"
        for action in sorted(required)
    }


def evaluate(smoke: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    root = Path(str(smoke["workspace"]))
    explorer = _load(root / ".agent" / "local-explore.py.report.json")
    diagnostic = explorer.get("diagnostic_report")
    explorer_full = (
        _load(root / str(diagnostic)) if isinstance(diagnostic, str) else explorer
    )
    explorer_actions = {
        str(item.get("action"))
        for item in explorer_full.get("action_trace", [])
        if isinstance(item, dict) and isinstance(item.get("action"), str)
    }
    explorer_compat_path = smoke.get("explorer_compat_report")
    explorer_compat = (
        _load(Path(str(explorer_compat_path))) if explorer_compat_path else {}
    )
    explorer_actions.update(
        str(item.get("action"))
        for item in explorer_compat.get("action_trace", [])
        if isinstance(item, dict) and isinstance(item.get("action"), str)
    )
    explorer_traces = [
        item
        for report in (explorer_full, explorer_compat)
        for item in report.get("action_trace", [])
        if isinstance(item, dict)
    ]
    if any(
        item.get("action") == "SEARCH" and item.get("mode") == "regex"
        for item in explorer_traces
    ):
        explorer_actions.add("REGEX_SEARCH")

    coder = _load(root / ".agent" / "last-local-coder-report.json")
    archive = (coder.get("evidence_refs") or {}).get("run_archive")
    coder_events = _events(root / str(archive) / "events.jsonl") if archive else []
    coder_actions = _event_actions(coder_events)

    review_path = smoke.get("review_report")
    review = _load(Path(str(review_path))) if review_path else {}
    review_archive = (review.get("evidence_refs") or {}).get("archive")
    if not review_archive:
        identity = review.get("identity") or {}
        task_id = identity.get("task_id")
        review_id = identity.get("review_id")
        if task_id and review_id:
            review_archive = f".agent/tasks/{task_id}/reviews/{review_id}"
    reviewer_events = (
        _events(root / str(review_archive) / "events.jsonl") if review_archive else []
    )
    reviewer_actions = _event_actions(reviewer_events)
    if review.get("decision") in {"pass_to_primary", "rework", "escalate"} and any(
        item.get("event") == "deferred_report_finalized" for item in reviewer_events
    ):
        reviewer_actions.add("REPORT")

    observed = {
        "explorer": explorer_actions,
        "coder": coder_actions,
        "reviewer": reviewer_actions,
    }
    core = {
        "explorer": smoke.get("explorer_status") == "success"
        and smoke.get("explorer_compat_status", "success") == "success",
        "coder": smoke.get("coder_status") == "ready_for_review"
        and smoke.get("independent_pytest_exit") == 0,
        "reviewer": smoke.get("reviewer_decision")
        in {"pass_to_primary", "rework", "escalate"},
    }
    roles = {}
    for role in ("explorer", "coder", "reviewer"):
        coverage = _capabilities(observed[role], REQUIRED_ACTIONS[role])
        complete = all(value == "pass" for value in coverage.values())
        infra = None
        if role == "reviewer":
            infra = review.get("infra_failure")
        elif role == "explorer":
            infra = explorer.get("infra_failure") or explorer_compat.get(
                "infra_failure"
            )
        elif role == "coder":
            reason = coder.get("failure_reason")
            if isinstance(reason, str) and "LM Studio request failed" in reason:
                infra = {
                    "reason_code": "model_server_http_400"
                    if "HTTP Error 400" in reason
                    else "model_server_request_failed",
                    "reason": reason,
                    "source": "coder_report",
                }
        if (
            isinstance(infra, dict)
            and "timed out" in str(infra.get("reason", "")).lower()
        ):
            infra = {**infra, "reason_code": "model_request_timeout"}
        not_run = role == "reviewer" and not review_path
        roles[role] = {
            "model": config.get(f"{role}_model"),
            "context_length": config.get(f"{role}_context_length"),
            "core_protocol_pass": core[role],
            "result": "not_run"
            if not_run
            else "infra_failure"
            if infra
            else "pass"
            if core[role] and complete
            else "incomplete"
            if core[role]
            else "fail",
            "observed_actions": sorted(observed[role]),
            "fixture_results": coverage,
            "infra_failure": infra,
            "startup_retry_attempts": (
                smoke.get("review_attempts", []) if role == "reviewer" else []
            ),
            "compat_failure_reason": (
                "Reviewer handoff was not reached"
                if not_run
                else infra.get("reason")
                if isinstance(infra, dict)
                else None
                if core[role] and complete
                else "required actions were not all exercised"
                if core[role]
                else "role did not complete the core live fixture"
            ),
        }
    return {
        "protocol_version": PROTOCOL_VERSION,
        "explorer_mode": smoke.get("explorer_mode", "investigate"),
        "tested_at": datetime.now(UTC).isoformat(),
        "shared_lmstudio_base_url": config.get("lmstudio_base_url"),
        "roles": roles,
        "summary": {
            "compat_runs": 3,
            "compat_pass": sum(item["result"] == "pass" for item in roles.values()),
            "compat_incomplete": sum(
                item["result"] == "incomplete" for item in roles.values()
            ),
            "compat_fail": sum(item["result"] == "fail" for item in roles.values()),
            "compat_infra_failure": sum(
                item["result"] == "infra_failure" for item in roles.values()
            ),
            "compat_not_run": sum(
                item["result"] == "not_run" for item in roles.values()
            ),
            "reviewer_infra_attempts": sum(
                bool(item.get("infra_failure"))
                for item in smoke.get("review_attempts", [])
                if isinstance(item, dict)
            ),
        },
        "source_smoke": smoke,
    }


def store(result: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"role-compat-{stamp}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    shutil.copyfile(path, output_dir / "latest.json")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qualify active models against role protocols"
    )
    parser.add_argument(
        "--config", type=Path, default=KIT / ".local-agents" / "config.json"
    )
    parser.add_argument("--explorer-mode", choices=("investigate", "locate"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=KIT / "benchmarks" / "results" / "role-compat",
    )
    parser.add_argument(
        "--reevaluate-latest",
        action="store_true",
        help="Re-extract evidence from the latest stored smoke without model calls.",
    )
    args = parser.parse_args()
    config = _load(args.config.resolve())
    latest = args.output_dir.resolve() / "latest.json"
    if args.reevaluate_latest:
        smoke = _load(latest).get("source_smoke")
        if not isinstance(smoke, dict) or not smoke.get("workspace"):
            raise SystemExit("latest result has no reusable source_smoke")
        if (
            args.explorer_mode
            and smoke.get("explorer_mode", "investigate") != args.explorer_mode
        ):
            raise SystemExit("stored smoke has a different Explorer capability mode")
    else:
        smoke = live_smoke.run(args.config.resolve(), explorer_mode=args.explorer_mode)
    result = evaluate(smoke, config)
    result["result_path"] = str(store(result, args.output_dir.resolve()))
    print(json.dumps(result, indent=2))
    return (
        0
        if result["summary"]["compat_fail"] == 0
        and result["summary"]["compat_infra_failure"] == 0
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
