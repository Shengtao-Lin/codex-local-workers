"""Focused inherited repair of real frozen failures; not fresh-chain credit."""

import argparse
import copy
import json

from capability_fit import WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import KIT, PYTHON, SOURCE, TARGET

BASE = WORK / "tool-awaitable-5"
SNAPSHOT = WORK / "tool-awaitable-runtime-3"
FEEDBACK = {
    "fresh-1": "Actual failed thread assertions and current diff show tool.handler(**values) executes on the event-loop thread. Sending lambda: result to a thread afterwards does not move the handler execution. Repair the responsible call while preserving invoke-once, all returned-awaitable kinds, existing shared deadline, causes and hooks. Do not edit already-correct unrelated behavior.",
    "fresh-2": "Actual tests and current diff show the original outer wait_for deadline was removed: direct async tools have no timeout, and sync factory time is excluded by a fresh timeout around its returned awaitable. Repair shared deadline ownership while preserving off-thread handler invocation, invoke-once, awaitable resolution, causes, cancellation and hooks. Two individually short phases must still fail when their total exceeds the one registered deadline.",
}


def prepare(arm):
    if not SNAPSHOT.exists():
        freeze(SNAPSHOT.name)
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    root = BASE / arm
    report = read(root / ".agent/coder.json")
    parent_run = root / report["evidence_refs"]["run_archive"]
    parent = read(parent_run / "packet.json")
    if read(parent_run / "review.json")["decision"] != "rework":
        raise ValueError("Primary rework decision required")
    child = {key: parent[key] for key in ("schema_version", "task_id", "unit_id")}
    child.update(
        run_id=parent["run_id"].removesuffix("-a1") + "-a2",
        parent_run_id=parent["run_id"],
        preserve_contract=True,
        attempt=2,
        packet_revision=parent["packet_revision"] + 1,
        plan_revision=1,
        review_feedback=[
            {
                "finding_id": "real-awaitable-" + arm,
                "contract_id": "resolved-output"
                if arm == "fresh-1"
                else "shared-deadline",
                "source_anchor": "async def execute"
                if arm == "fresh-1"
                else "with self._telemetry.span",
                "verify_in_review": True,
                "text": FEEDBACK[arm],
            }
        ],
    )
    worker = load_worker(SNAPSHOT)
    resolved = worker.resolve_inherited_packet(root, child)
    worker.validate_packet(resolved)
    if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
        raise ValueError("parent draft drift")
    config = copy.deepcopy(read(root / ".agent/config.json"))
    config["validation_profiles"]["project-strict"]["pytest_argv"][-1] = (
        "--basetemp=" + str(root / ".agent/worker-a2-temp")
    )
    write(root / ".agent/rework-a2.json", child)
    write(root / ".agent/rework-config-a2.json", config)
    write(
        root / ".agent/rework-registration-a2.json",
        {
            "runtime": str(SNAPSHOT),
            "weekly_ceiling": 23,
            "parent_source_sha256": digest(root / TARGET),
            "parent_run": str(parent_run),
            "packet_sha256": digest(root / ".agent/rework-a2.json"),
            "config_sha256": digest(root / ".agent/rework-config-a2.json"),
            "credit": "Primary-guided inherited repair, not independent fresh success or cloud savings",
            "unchanged": "Complete contract, readable/write scope, protected tests, model and budgets",
        },
    )
    print(json.dumps({"prepared": arm, "run_id": child["run_id"]}))


def run(arm):
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    provenance = read(KIT / "benchmarks/fixtures/tool-awaitable-v5/provenance.json")
    verify_hashes(SOURCE, provenance["original_files"])
    root = BASE / arm
    result = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/rework-a2.json"),
            "--config",
            str(root / ".agent/rework-config-a2.json"),
            "--coder-report",
            str(root / ".agent/coder-a2.json"),
            "--review-report",
            str(root / ".agent/reviewer-a2.json"),
        ],
        timeout=1500,
    )
    write(root / ".agent/invocation-a2.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--arm", choices=tuple(FEEDBACK), required=True)
    args = parser.parse_args()
    (prepare if args.action == "prepare" else run)(args.arm)
