"""One focused inherited repair; never count it as fresh qualification."""

import argparse
import copy
import importlib.util

import tool_generator_fresh_trial as trial
from capability_fit import KIT, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

ROOT = trial.BASE / "candidate-1"


def prepare():
    report = read(ROOT / ".agent/coder.json")
    archive = ROOT / report["evidence_refs"]["run_archive"]
    parent = read(archive / "packet.json")
    if read(archive / "review.json")["decision"] != "rework":
        raise ValueError("immutable Primary rework decision required")
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
                "finding_id": "generator-and-opt-out-classification",
                "contract_id": "resolved-output",
                "source_anchor": "async def execute",
                "verify_in_review": True,
                "text": "Actual final validation still fails the generator-coroutine and plain mapping opt-out tests. Current bare hasattr accepts a disabled __await__ marker. A legal generator coroutine has no __await__ attribute; it is already awaitable and must be resolved once, not converted then consumed with an extra __next__. Reconcile current execute predicate with readable reference/awaitable_protocol.txt (actual CPython inspect predicate and opt-out rejection branch) and both failure messages. Make a minimal consistent classification repair, remove newly introduced redundant draft code, and validate all twenty-one protected tests and configured checks. Preserve thread/context ownership, one invocation/completion, direct async final identity, existing deadline, error causes and hooks. Do not edit tests, widen scope or raise budgets; another in-scope implementation satisfying the contract is permitted.",
            }
        ],
    )
    worker = load_worker(trial.SNAPSHOT)
    resolved = worker.resolve_inherited_packet(ROOT, child)
    worker.validate_packet(resolved)
    if resolved["_inheritance"]["parent_input_state"]["status"] != "unchanged":
        raise ValueError("parent draft drift")
    config = copy.deepcopy(read(ROOT / ".agent/config.json"))
    profile = config["validation_profiles"]["project-strict"]
    profile["pytest_argv"] = [
        "--basetemp=" + str(ROOT / ".agent/rework-a2-temp")
        if value.startswith("--basetemp=")
        else value
        for value in profile["pytest_argv"]
    ]
    write(ROOT / ".agent/generator-rework-a2.json", child)
    write(ROOT / ".agent/generator-config-a2.json", config)
    original = read(ROOT / ".agent/inputs.json")
    write(
        ROOT / ".agent/generator-rework-registration-a2.json",
        {
            "weekly_ceiling": 30,
            "credit": "Primary-guided inherited repair, not fresh success",
            "inputs": {
                name: digest(ROOT / name)
                for name in (
                    TARGET,
                    ".agent/generator-rework-a2.json",
                    ".agent/generator-config-a2.json",
                )
            },
            "protected": {
                path: sha
                for path, sha in original["protected"].items()
                if path != TARGET
            },
            "adapters": {
                name: digest(KIT / "benchmarks" / name)
                for name in (*trial.ADAPTERS, "tool_generator_rework.py")
            },
        },
    )


def run():
    registration = read(ROOT / ".agent/generator-rework-registration-a2.json")
    verify_hashes(ROOT, {**registration["inputs"], **registration["protected"]})
    verify_hashes(KIT / "benchmarks", registration["adapters"])
    verify_hashes(trial.SNAPSHOT, read(trial.SNAPSHOT / "freeze.json")["files"])
    result = command(
        ROOT,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks/coder_native_repair_history_adapter.py"),
            "--snapshot",
            str(trial.SNAPSHOT),
            "--packet",
            str(ROOT / ".agent/generator-rework-a2.json"),
            "--config",
            str(ROOT / ".agent/generator-config-a2.json"),
            "--report",
            str(ROOT / ".agent/coder-a2.json"),
        ],
        timeout=1500,
    )
    write(ROOT / ".agent/coder-invocation-a2.json", result)
    report = read(ROOT / ".agent/coder-a2.json")
    verify_hashes(ROOT, registration["protected"])
    if result["exit"] == 0 and report["status"] == "ready_for_review":
        spec = importlib.util.spec_from_file_location(
            "generator_rework_unit", trial.SNAPSHOT / ".local-agents/local-unit.py"
        )
        unit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unit)
        identity = unit.verify_handoff(ROOT, report)
        write(
            ROOT / ".agent/review-request-a2.json",
            {
                "schema_version": 1,
                **identity,
                "review_id": identity["run_id"] + "-review",
            },
        )
        review = command(
            ROOT,
            [
                str(PYTHON),
                "-B",
                str(KIT / "benchmarks/reviewer_retained_evidence_v4_adapter.py"),
                "--snapshot",
                str(trial.SNAPSHOT),
                "--request",
                str(ROOT / ".agent/review-request-a2.json"),
                "--config",
                str(ROOT / ".agent/generator-config-a2.json"),
                "--report",
                str(ROOT / ".agent/reviewer-a2.json"),
            ],
            timeout=900,
        )
        write(ROOT / ".agent/reviewer-invocation-a2.json", review)
    verify_hashes(ROOT, registration["protected"])
    print(
        {
            "coder_status": report["status"],
            "inherited_repair": True,
            "fresh_credit": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    {"prepare": prepare, "run": run}[args.action]()
