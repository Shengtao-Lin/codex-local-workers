"""Unified trusted contract entry for bounded Strata work."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "strata"))
from general_state import StateError, read
from report_delivery import public_output
from task_workflow import cancel, prepare, resume, run, status


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("mode", choices=["prepare", "run", "resume", "status", "cancel"])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--attempt-id")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--feedback", type=Path)
    args = parser.parse_args()
    if args.feedback and args.mode != "resume":
        parser.error("--feedback requires resume")
    root = args.project.resolve(strict=True)
    try:
        if args.mode == "prepare":
            if not args.contract or not args.config:
                parser.error("prepare requires --contract and --config")
            value = prepare(root, read(args.contract), read(args.config), apply=args.apply)
        else:
            if not args.task_id:
                parser.error("task identity required")
            if args.mode in {"run", "resume"}:
                if not args.attempt_id:
                    parser.error("run requires unique attempt identity")
                if args.mode == "resume":
                    if not args.feedback:
                        parser.error("resume requires bound feedback")
                    value = resume(root, args.task_id, args.attempt_id, read(args.feedback))
                else:
                    value = run(root, args.task_id, args.attempt_id)
            else:
                value = (status if args.mode == "status" else cancel)(root, args.task_id)
    except (StateError, ValueError, OSError) as exc:
        value = {"status": "blocked", "reason": str(exc), "acceptance": False}
    print(json.dumps(public_output(value), ensure_ascii=False, indent=2))
    return (
        0
        if value.get("status") in {"prepared", "preview", "ready_for_primary", "cancel_requested"}
        or (args.mode == "status" and "reason" not in value)
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
