"""Explicit optional read-only entry. Uses the same native provider and host reader."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "strata"))
from general_cli import provider
from general_native import run_native
from general_prepare import W, load_contract
from general_state import BudgetExhausted, read
from readonly_host import ReadonlyHost, prepare


def execute(root, task_id, attempt_id, *, mode="live", actions=None, resume=False, feedback=None):
    _, material = load_contract(root, task_id)
    host_type = ReadonlyHost
    if material["config"].get("experimental_strata_capabilities"):
        from capability_host import CapabilityHost

        host_type = CapabilityHost
    host = host_type(root, task_id, attempt_id, resume=resume)
    host.continuation_feedback = feedback
    try:
        if mode == "live":
            host.config["strata_instance_id"] = provider(host.config)["id"]
        host.open()
        run_native(host, mode, actions)
        return host.finish()
    except BudgetExhausted as exc:
        return host.finish("budget_exhausted", str(exc))
    except W.InvocationInterrupted as exc:
        return host.finish("cancelled", str(exc))
    except (ValueError, OSError, TimeoutError, KeyboardInterrupt) as exc:
        return host.finish("failed", str(exc))


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("--project", type=Path, default=Path.cwd())
    p.add_argument("--request", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument("--task-id")
    p.add_argument("--attempt-id")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    if a.mode == "prepare":
        if not a.request or not a.config:
            p.error("prepare requires request/config")
        result = prepare(a.project, read(a.request), read(a.config), apply=a.apply)
    else:
        if not a.task_id or not a.attempt_id:
            p.error("run requires task/attempt identity")
        result = execute(a.project, a.task_id, a.attempt_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"prepared", "preview", "ready_for_primary"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
