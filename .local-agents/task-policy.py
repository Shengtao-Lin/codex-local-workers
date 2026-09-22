from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_POLICY = {
    "same_failure_threshold": 3,
    "no_progress_threshold": 3,
    "explorer_quality_threshold": 3,
    "coder_quality_threshold": 3,
}


class PolicyError(ValueError):
    pass


def _threshold(policy: dict[str, Any], name: str) -> int:
    value = int(policy.get(name, DEFAULT_POLICY[name]))
    if value < 1:
        raise PolicyError(f"{name} must be at least 1")
    return value


def _same_unit(history: list[dict[str, Any]], latest: dict[str, Any]) -> list[dict[str, Any]]:
    worker = latest.get("worker")
    unit_id = latest.get("unit_id")
    return [item for item in history if item.get("worker") == worker and item.get("unit_id") == unit_id]


def _trailing_no_progress(items: list[dict[str, Any]]) -> int:
    count = 0
    for item in reversed(items):
        if item.get("progress") is True or item.get("result") in {"success", "accepted"}:
            break
        count += 1
    return count


def _trailing_same_failure(items: list[dict[str, Any]], signature: str | None) -> int:
    if not signature:
        return 0
    count = 0
    for item in reversed(items):
        if item.get("progress") is True:
            break
        if item.get("failure_signature") != signature:
            break
        count += 1
    return count


def _trailing_quality_failures(items: list[dict[str, Any]]) -> int:
    count = 0
    for item in reversed(items):
        if item.get("progress") is True or item.get("result") != "quality_failed":
            break
        count += 1
    return count


def evaluate_task_state(state: dict[str, Any]) -> dict[str, Any]:
    history = state.get("recent_attempts", [])
    if not isinstance(history, list):
        raise PolicyError("recent_attempts must be an array")
    if not history:
        return {"decision": "continue", "reason": "no attempts recorded", "streaks": {}}
    latest = history[-1]
    if not isinstance(latest, dict):
        raise PolicyError("each recent_attempts item must be an object")

    if latest.get("severity") in {"security", "unsafe", "out_of_scope"}:
        return {
            "decision": "takeover",
            "reason": f"immediate escalation severity: {latest.get('severity')}",
            "streaks": {},
        }
    if latest.get("result") == "policy_violation":
        return {
            "decision": "takeover",
            "reason": "runtime reported a policy violation",
            "streaks": {},
        }
    if latest.get("result") == "ready_for_review":
        return {
            "decision": "primary_review",
            "reason": "the worker result is ready for independent Primary review",
            "streaks": {},
        }
    if latest.get("result") in {"blocked", "interrupted"}:
        return {
            "decision": "primary_decision",
            "reason": "the latest run needs an environment, scope, or partial-state decision",
            "streaks": {},
        }
    if latest.get("result") in {"success", "accepted"} or latest.get("progress") is True:
        return {
            "decision": "continue",
            "reason": "the latest attempt produced accepted work or material progress",
            "streaks": {"same_failure": 0, "no_progress": 0, "quality_failures": 0},
        }

    policy = {**DEFAULT_POLICY, **state.get("fallback_policy", {})}
    items = _same_unit(history, latest)
    signature = latest.get("failure_signature")
    same_failure = _trailing_same_failure(items, signature)
    no_progress = _trailing_no_progress(items)
    quality_failures = _trailing_quality_failures(items)
    streaks = {
        "same_failure": same_failure,
        "no_progress": no_progress,
        "quality_failures": quality_failures,
    }

    worker = latest.get("worker")
    if worker == "coder" and quality_failures >= _threshold(policy, "coder_quality_threshold"):
        return {
            "decision": "takeover",
            "reason": "Coder repeatedly failed the same implementation quality gate",
            "streaks": streaks,
        }
    if worker == "explorer" and quality_failures >= _threshold(policy, "explorer_quality_threshold"):
        return {
            "decision": "fallback_primary",
            "reason": "Explorer repeatedly failed to provide acceptable evidence",
            "streaks": streaks,
        }
    if same_failure >= _threshold(policy, "same_failure_threshold"):
        return {
            "decision": "fallback_primary",
            "reason": "the same failure signature repeated without material progress",
            "streaks": streaks,
        }
    if no_progress >= _threshold(policy, "no_progress_threshold"):
        return {
            "decision": "fallback_primary",
            "reason": "the same work unit repeatedly made no material progress",
            "streaks": streaks,
        }
    return {
        "decision": "retry_with_change",
        "reason": "failure threshold not reached; retry only after a focused change in approach",
        "streaks": streaks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state")
    args = parser.parse_args()
    try:
        state = json.loads(Path(args.state).read_text(encoding="utf-8-sig"))
        if not isinstance(state, dict):
            raise PolicyError("task state root must be an object")
        result = evaluate_task_state(state)
    except (OSError, ValueError, PolicyError) as exc:
        print(json.dumps({"decision": "error", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
