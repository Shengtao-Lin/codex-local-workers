from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent


def load_run_state() -> Any:
    spec = importlib.util.spec_from_file_location("local_worker_review_state", SCRIPT_DIR / "run-state.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load run-state.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUN_STATE = load_run_state()


def identifier(value: str, name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise ValueError(f"invalid {name}")
    return value


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def passing_local_review(
    task_root: Path, task_id: str, unit_id: str, run_id: str
) -> dict[str, Any] | None:
    reviews_root = task_root / "reviews"
    if not reviews_root.is_dir():
        return None
    for handoff_path in sorted(reviews_root.glob("*/handoff.json")):
        try:
            handoff = load_object(handoff_path)
        except (OSError, ValueError):
            continue
        identity = handoff.get("identity", {})
        completed_path = handoff_path.with_name("completed.json")
        try:
            completed = load_object(completed_path)
        except (OSError, ValueError):
            continue
        if (
            identity.get("task_id") == task_id
            and identity.get("unit_id") == unit_id
            and identity.get("run_id") == run_id
            and handoff.get("decision") == "pass_to_primary"
            and completed.get("decision") == "pass_to_primary"
        ):
            return handoff
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Record an immutable Primary review for a Coder run.")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--decision", required=True, choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--summary", required=True)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    try:
        task_id = identifier(args.task_id, "task-id")
        run_id = identifier(args.run_id, "run-id")
        summary = args.summary.strip()
        if not summary:
            raise ValueError("summary must not be empty")
        repo_root = Path(args.repo).resolve()
        task_root = repo_root / ".agent" / "tasks" / task_id
        run_root = task_root / "runs" / run_id
        completed = load_object(run_root / "completed.json")
        handoff = load_object(run_root / "handoff.json")
        state_path = task_root / "state.json"
        state = load_object(state_path)
        identity = handoff.get("identity", {})
        if identity.get("task_id") != task_id or identity.get("run_id") != run_id:
            raise ValueError("handoff identity does not match requested task/run")
        unit_id = identity.get("unit_id")
        if not isinstance(unit_id, str):
            raise ValueError("handoff is missing unit identity")
        local_review = passing_local_review(task_root, task_id, unit_id, run_id)
        if (
            args.decision == "accept"
            and handoff.get("next_action_required") == "local_review"
            and local_review is None
        ):
            raise ValueError("accept requires a passing Local Reviewer report for this run")
        reviews = state.setdefault("reviews", [])
        completed_units = state.setdefault("completed_units", [])
        attempts = state.setdefault("recent_attempts", [])
        if not isinstance(reviews, list) or not isinstance(completed_units, list) or not isinstance(attempts, list):
            raise ValueError("task review fields must be arrays")
        review = {
            "schema_version": 1,
            "task_id": task_id,
            "unit_id": unit_id,
            "run_id": run_id,
            "worker_status": completed.get("status"),
            "decision": args.decision,
            "summary": summary,
            "local_review_id": (
                (local_review.get("identity") or {}).get("review_id")
                if local_review is not None
                else None
            ),
            "reviewed_at": RUN_STATE.utc_now(),
        }
        RUN_STATE.write_json_once(run_root / "review.json", review)
        reviews.append(review)
        if args.decision == "accept" and not any(
            item.get("run_id") == run_id for item in completed_units if isinstance(item, dict)
        ):
            completed_units.append(
                {
                    "unit_id": unit_id,
                    "run_id": run_id,
                    "accepted_at": review["reviewed_at"],
                    "summary": summary,
                }
            )
        result_by_decision = {
            "accept": "accepted",
            "rework": "quality_failed",
            "replan": "replan",
            "takeover": "takeover",
        }
        for attempt in reversed(attempts):
            if (
                isinstance(attempt, dict)
                and attempt.get("run_id") == run_id
                and attempt.get("worker") == "coder"
            ):
                attempt["primary_review"] = args.decision
                attempt["result"] = result_by_decision[args.decision]
                attempt["progress"] = True if args.decision == "accept" else False
                break
        attempts.append(
            {
                "run_id": run_id,
                "unit_id": unit_id,
                "worker": "primary",
                "result": result_by_decision[args.decision],
                "primary_review": args.decision,
                "progress": True if args.decision == "accept" else False,
                "recorded_at": review["reviewed_at"],
            }
        )
        if len(attempts) > 50:
            del attempts[:-50]
        state["updated_at"] = review["reviewed_at"]
        RUN_STATE.atomic_json(state_path, state)
        RUN_STATE.atomic_json(
            repo_root / ".agent" / "current-task.json",
            {
                "schema_version": 1,
                "task_id": task_id,
                "unit_id": unit_id,
                "latest_run_id": run_id,
                "task_state": state_path.relative_to(repo_root).as_posix(),
                "usage": state.get("usage", {}),
                "recent_attempts": attempts,
                "fallback_policy": state.get("fallback_policy", {}),
                "open_issues": state.get("open_issues", []),
                "updated_at": review["reviewed_at"],
            },
        )
    except (OSError, ValueError, RUN_STATE.RunStateError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "ok", "review": review}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
