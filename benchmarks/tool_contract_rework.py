"""Narrow real inherited repairs; never relabel them as fresh qualification."""

import argparse
import importlib.util

import tool_awaitable_rework as rework
from capability_fit import KIT, WORK, freeze, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "tool-contract-scope-1"
SNAPSHOT = WORK / "tool-evidence-runtime-8"
FIXTURE_VERSION = 9
FEEDBACK = (
    "Primary inspected your actual diff: direct async final values are now preserved. "
    "The remaining off-thread regression is the synchronous handler invocation inside "
    "execute: tool.handler(**values) runs immediately on the event-loop thread. "
    "Moving only an already-computed result elsewhere cannot move that invocation. "
    "Locate that actual call and repair its thread ownership, keeping invocation exactly "
    "once, returned-awaitable resolution, the one existing deadline, errors, hooks and "
    "all async final-object preservation unchanged. This is a focused repair of your "
    "current draft, not a rewrite or a request to change protected tests."
)


def configure():
    rework.BASE, rework.SNAPSHOT = BASE, SNAPSHOT
    rework.FEEDBACK = {arm: FEEDBACK for arm in ("fresh-1", "fresh-2")}


def prepare(arm):
    configure()
    if not SNAPSHOT.exists():
        freeze(SNAPSHOT.name)
    # Both failed units own the same resolved-output/thread-invocation invariant.
    rework.prepare(arm)
    root = BASE / arm
    child = read(root / ".agent/rework-a2.json")
    child["review_feedback"][0].update(
        contract_id="resolved-output", source_anchor="async def execute"
    )
    # Retain the helper's original preparation record; the actually used packet has
    # a new immutable path/hash rather than editing the a1 archive or that record.
    write(root / ".agent/scope-rework-a2.json", child)


def register_actual(arm):
    root = BASE / arm
    config = read(root / ".agent/compat-config.json")
    config["validation_profiles"]["project-strict"]["pytest_argv"][-1] = (
        "--basetemp=" + str(root / ".agent/worker-a2-temp")
    )
    write(root / ".agent/scope-rework-config-a2.json", config)
    write(
        root / ".agent/scope-rework-registration-a2.json",
        {
            "packet_sha256": digest(root / ".agent/scope-rework-a2.json"),
            "config_sha256": digest(root / ".agent/scope-rework-config-a2.json"),
            "parent_source_sha256": digest(root / TARGET),
            "snapshot": str(SNAPSHOT),
            "adapters": {
                p: digest(KIT / "benchmarks" / p)
                for p in (
                    "native_coder_adapter.py",
                    "coder_native_block_adapter.py",
                    "coder_native_history_adapter.py",
                    "coder_native_repair_history_adapter.py",
                )
            },
            "credit": "Primary-guided inherited repair, not fresh success; exact parent validation profile retained",
        },
    )


def run(arm):
    root = BASE / arm
    registration = read(root / ".agent/scope-rework-registration-a2.json")
    config = root / ".agent/scope-rework-config-a2.json"
    verify_hashes(
        root,
        {
            ".agent/scope-rework-a2.json": registration["packet_sha256"],
            ".agent/scope-rework-config-a2.json": registration["config_sha256"],
            TARGET: registration["parent_source_sha256"],
        },
    )
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(KIT / "benchmarks", registration["adapters"])
    provenance = read(
        KIT / f"benchmarks/fixtures/tool-awaitable-v{FIXTURE_VERSION}/provenance.json"
    )
    verify_hashes(
        root, {p: sha for p, sha in provenance["files"].items() if p != TARGET}
    )
    verify_hashes(KIT.parent / "agent-runtime-kit", provenance["original_files"])
    result = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks/coder_native_repair_history_adapter.py"),
            "--snapshot",
            str(SNAPSHOT),
            "--packet",
            str(root / ".agent/scope-rework-a2.json"),
            "--config",
            str(config),
            "--report",
            str(root / ".agent/coder-a2.json"),
        ],
        timeout=1500,
    )
    write(root / ".agent/coder-invocation-a2.json", result)
    report = read(root / ".agent/coder-a2.json")
    if report["status"] == "ready_for_review":
        spec = importlib.util.spec_from_file_location(
            "scope_rework_unit", SNAPSHOT / ".local-agents/local-unit.py"
        )
        unit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unit)
        identity = unit.verify_handoff(root, report)
        request = root / ".agent/review-request-a2.json"
        write(
            request,
            {
                "schema_version": 1,
                **identity,
                "review_id": identity["run_id"] + "-review",
            },
        )
        invoked = command(
            root,
            [
                str(PYTHON),
                "-B",
                str(SNAPSHOT / ".local-agents/local-review.py"),
                "--request",
                str(request),
                "--config",
                str(config),
                "--report",
                str(root / ".agent/reviewer-a2.json"),
            ],
            timeout=900,
        )
        write(root / ".agent/reviewer-invocation-a2.json", invoked)
    print({"arm": arm, "coder_status": report["status"], "fresh_success_credit": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "register-actual", "run"))
    parser.add_argument("--arm", choices=("fresh-1", "fresh-2"), required=True)
    args = parser.parse_args()
    {"prepare": prepare, "register-actual": register_actual, "run": run}[args.action](
        args.arm
    )
