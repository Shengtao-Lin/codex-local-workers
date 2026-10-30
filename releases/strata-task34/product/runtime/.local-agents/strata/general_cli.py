"""Explicit general-task commands. No Git, model management or cloud fallback."""

import argparse
import importlib.util
import json
from pathlib import Path

from general_host import GeneralHost
from general_native import run_native
from general_prepare import RUNTIME, W, load_contract, prepare, sha
from general_state import BudgetExhausted, StateError, TaskLedger, fingerprint, read
from strata_artifacts import save


def provider(config):
    spec = importlib.util.spec_from_file_location(
        "strata_product_entry", RUNTIME / "strata-worker.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.checked_config(config)
    module.verify_installation()
    return module.residency(config)


def execute(
    root,
    task_id,
    attempt_id,
    *,
    resume=False,
    mode="live",
    actions=None,
    feedback=None,
    continuation_feedback=None,
):
    _, material = load_contract(root, task_id)
    host_type = GeneralHost
    if material["config"].get("experimental_native_tools_trial"):
        from native_trial_host import NativeTrialHost

        host_type = NativeTrialHost
    if material["config"].get("experimental_strata_capabilities"):
        from capability_host import CapabilityCoderHost

        host_type = CapabilityCoderHost
    host = host_type(root, task_id, attempt_id, resume=resume, primary_feedback=feedback)
    host.continuation_feedback = continuation_feedback
    try:
        if mode == "live":
            host.config["strata_instance_id"] = provider(host.config)["id"]
        host.open()
        run_native(host, mode, actions)
        return host.finish()
    except BudgetExhausted as exc:
        return host.finish("budget_exhausted", str(exc))
    except W.InvocationInterrupted as exc:
        return host.finish(
            "cancelled" if exc.reason_code == "cancel_requested" else "interrupted",
            str(exc),
        )
    except (KeyboardInterrupt, TimeoutError):
        return host.finish("interrupted", "Interrupted; inspect canonical task state")
    except (StateError, W.PolicyViolation) as exc:
        return host.finish("conflicted", str(exc))
    except (ValueError, OSError, W.WorkerError) as exc:
        return host.finish("failed", str(exc))


def export_task(root, task_id, destination):
    lock = W.RepoWriteLock(Path(root), "export-" + task_id)
    lock.acquire()
    host = None
    try:
        host = GeneralHost(root, task_id, "export-inspection")
        host.assert_bound()
        if host.ledger.state["active"]:
            raise StateError("Cannot export active task")
        target = Path(destination)
        if target.exists():
            raise StateError("Export destination already exists")
        latest = host.ledger.state.get("latest_check")
        if latest and (
            sha(host.repo_root / latest["path"]) != latest["sha256"]
            or latest["inputs"] != host.current_hashes()
        ):
            raise StateError("Current check receipt changed/stale")
        patch = host.task_diff()
        payloads = {"changes.diff": patch.encode("utf-8")}
        for path in host.material["packet"]["scope"]["modify"]:
            payloads["preimages/" + path] = (host.ledger.path / "preimages" / path).read_bytes()
        receipts = {}
        for event in sorted(host.ledger.events.glob("*.json")):
            check = read(event)["state"].get("latest_check")
            if check:
                receipts[check["path"]] = check["sha256"]
        runs = host.ledger.path.parent / "runs"
        for path, digest in receipts.items():
            source = host.repo_root / path
            relative = source.relative_to(runs)
            if sha(source) != digest:
                raise StateError("Export check receipt changed: " + path)
            payloads["checks/" + relative.as_posix()] = source.read_bytes()
            receipt = read(source)
            junit = receipt["validation"]["focused_tests"].get("junit", {})
            if junit.get("path"):
                junit_file = host.repo_root / junit["path"]
                junit_relative = junit_file.relative_to(runs)
                if sha(junit_file) != receipt.get("junit_sha256"):
                    raise StateError("Export JUnit evidence changed")
                payloads["checks/" + junit_relative.as_posix()] = junit_file.read_bytes()
        host.assert_bound()
        target.mkdir(parents=True)
        inventory = {}
        for name, raw in payloads.items():
            output = target / name
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(raw)
            inventory[name] = sha(output)
        save(
            target / "evidence.json",
            {
                "status": host.ledger.state["status"],
                "task_id": task_id,
                "ledger": host.ledger.current(),
                "archive": str(host.ledger.path.parent / "runs"),
                "acceptance": False,
                "current_hashes": host.current_hashes(),
                "initial_hashes": host.policy["initial_hashes"],
                "created_paths": host.policy["create"],
                "contract_sha256": fingerprint(host.material),
                "packet": host.material["packet"],
                "files": inventory,
                "complete": True,
            },
        )
        return {"status": "exported", "path": str(target), "acceptance": False}
    finally:
        if host:
            host.close()
        lock.release()


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("mode", choices=["prepare", "run", "resume", "status", "cancel", "export"])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--task", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--attempt-id")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--feedback", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.feedback and args.mode != "resume":
        parser.error("--feedback is only for one Primary-confirmed return via resume")
    root = args.project.resolve(strict=True)
    if args.mode == "prepare":
        if not args.task or not args.config:
            parser.error("prepare requires --task and --config")
        value = prepare(root, read(args.task), read(args.config), apply=args.apply)
    else:
        if not args.task_id:
            parser.error("command requires --task-id")
        if args.mode in {"run", "resume"}:
            if not args.attempt_id:
                parser.error("run/resume requires unique --attempt-id")
            value = execute(
                root,
                args.task_id,
                args.attempt_id,
                resume=args.mode == "resume",
                feedback=read(args.feedback) if args.feedback else None,
            )
        elif args.mode == "status":
            ledger, _ = load_contract(root, args.task_id)
            value = ledger.current()
        elif args.mode == "cancel":
            ledger = TaskLedger(root, args.task_id)
            ledger.cancel()
            value = {"status": "cancel_requested", "task_id": args.task_id}
        else:
            if not args.output:
                parser.error("export requires --output")
            value = export_task(root, args.task_id, args.output)
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return (
        0
        if value["status"]
        in {"ready_for_primary", "preview", "prepared", "exported", "cancel_requested"}
        or args.mode == "status"
        else 2
    )
