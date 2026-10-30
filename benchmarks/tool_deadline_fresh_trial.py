"""Prospective fresh atomic units with twenty protected tests; no oracle patch."""

import argparse
import copy
import importlib.util
import shutil

from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "tool-deadline-fresh-1"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v14"
SNAPSHOT = WORK / "reviewer-all-lines-runtime-16"
TEMPLATE = WORK / "tool-plain-result-3/fresh-1/.agent"
REFERENCE = KIT / "benchmarks/fixtures/tool-library-reference-v1"
ARMS = ("control-1", "candidate-1", "candidate-2", "control-2")
TEST = "tests/unit/test_deadline_registration.py"
ADAPTERS = (
    "native_coder_adapter.py",
    "coder_native_block_adapter.py",
    "coder_native_history_adapter.py",
    "coder_native_repair_history_adapter.py",
    "reviewer_required_tool_adapter.py",
    "reviewer_sampling_probe_adapter.py",
    "reviewer_staged_assessment_adapter.py",
    "reviewer_staged_final_gate_adapter.py",
    "reviewer_range_staged_adapter.py",
    "reviewer_dependency_evidence_adapter.py",
    "reviewer_dependency_investigation_adapter.py",
    "reviewer_catalog_staged_adapter.py",
    "reviewer_evidence_catalog_adapter_v2.py",
    "tool_deadline_fresh_trial.py",
)


def register():
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    facts = read(WORK / "tool-deadline-fixture-2/registration.json")
    if not all(item["passed_preflight"] for item in facts["facts"].values()):
        raise ValueError("actual twenty-test positive/negative preflight required")
    write(
        BASE / "registration.json",
        {
            "arms": ARMS,
            "weekly_ceiling": 30,
            "fixture": "v14 original source with twenty unchanged protected tests",
            "risk": "High feature/unit/integration: atomic public result/deadline/cancellation/context boundary; no split of invariant or lowered risk.",
            "axis": "Same correlated-native Coder and fresh canonical handoff; actual-read evidence IDs with monolithic versus staged Reviewer. Both require dependency investigation/citations and successful approved focused-tests plus configured checks. Same models, sampling, total budgets, readonly tests and single model residency. Candidate remains experimental until qualification; no retroactive credit for prior Reviewer cohorts.",
            "explorer": "Already located same ToolRegistry and answered dependency semantics; no duplicate investigation or fabricated Explorer credit.",
            "credit": "New fresh C/R units, not replay of incomplete old source or guided recovery. Keep all prior failures and independent reviewer-negative denominators; no Coordinator release or savings inferred.",
            "files": {name: digest(KIT / "benchmarks" / name) for name in ADAPTERS},
            "template_files": {
                name: digest(TEMPLATE / name)
                for name in ("plain-packet.json", "plain-config.json", "pyright.json")
            },
            "reference_files": read(REFERENCE / "provenance.json")["files"],
            "fixture_files": read(FROZEN / "provenance.json")["files"],
        },
    )


def prepare(arm):
    registration = read(BASE / "registration.json")
    verify_hashes(TEMPLATE, registration["template_files"])
    verify_hashes(FROZEN, registration["fixture_files"])
    verify_hashes(REFERENCE, registration["reference_files"])
    root = BASE / arm
    shutil.copytree(FROZEN, root)
    shutil.copytree(REFERENCE, root / "reference")
    packet = copy.deepcopy(read(TEMPLATE / "plain-packet.json"))
    task_id = BASE.name + "-" + arm
    packet.update(
        task_id=task_id, feature_id=task_id, run_id=task_id + "-a1", packet_revision=7
    )
    packet["focused_tests"].append(TEST)
    packet["scope"]["read"].append(TEST)
    packet["scope"]["readonly"].append(TEST)
    packet["acceptance_scenarios"].append(
        {
            "id": "one-registered-deadline",
            "text": "The synchronous factory and its returned completion use the existing single execution deadline; no separate timeout registration is introduced.",
            "observables": {
                "execution_timeout_registrations": "one, observed through public asyncio.Timeout on current CPython 3.12"
            },
        }
    )
    if (
        packet["review_feedback"]
        or digest(root / TARGET) != registration["fixture_files"][TARGET]
    ):
        raise ValueError(
            "fresh original source and no inherited repair recipe required"
        )
    load_worker(SNAPSHOT).validate_packet(packet)
    config = copy.deepcopy(read(TEMPLATE / "plain-config.json"))
    config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "caller-context",
            "path": "reference/asyncio_threads.py",
            "anchors": ["copy_context", "ctx.run"],
        }
    ]
    config["python"] = str(PYTHON)
    config["reviewer_require_approved_execution"] = True
    for profile in config["validation_profiles"].values():
        profile["python"] = str(PYTHON)
        profile["pytest_argv"] = [
            "--basetemp=" + str(root / ".agent/worker-temp-a1")
            if item.startswith("--basetemp=")
            else item
            for item in profile["pytest_argv"]
        ]
    for check in config["validation_profiles"]["project-strict"]["commands"][:2]:
        check["argv"].append(TEST)
    write(root / ".agent/packet.json", packet)
    write(root / ".agent/config.json", config)
    write(root / ".agent/pyright.json", read(TEMPLATE / "pyright.json"))
    protected = {
        **registration["fixture_files"],
        **{
            "reference/" + key: value
            for key, value in registration["reference_files"].items()
        },
    }
    write(
        root / ".agent/inputs.json",
        {
            "files": {
                name: digest(root / name)
                for name in (
                    ".agent/packet.json",
                    ".agent/config.json",
                    ".agent/pyright.json",
                )
            },
            "protected": protected,
        },
    )


def run(arm):
    root = BASE / arm
    registration = read(BASE / "registration.json")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(KIT / "benchmarks", registration["files"])
    inputs = read(root / ".agent/inputs.json")
    verify_hashes(root, {**inputs["files"], **inputs["protected"]})
    coder = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks/coder_native_repair_history_adapter.py"),
            "--snapshot",
            str(SNAPSHOT),
            "--packet",
            str(root / ".agent/packet.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/coder.json"),
        ],
        timeout=1500,
    )
    write(root / ".agent/coder-invocation.json", coder)
    report = read(root / ".agent/coder.json")
    verify_hashes(
        root, {name: sha for name, sha in inputs["protected"].items() if name != TARGET}
    )
    reviewer = None
    if coder["exit"] == 0 and report["status"] == "ready_for_review":
        spec = importlib.util.spec_from_file_location(
            "deadline_fresh_unit", SNAPSHOT / ".local-agents/local-unit.py"
        )
        unit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unit)
        identity = unit.verify_handoff(root, report)
        write(
            root / ".agent/review-request.json",
            {
                "schema_version": 1,
                **identity,
                "review_id": identity["run_id"] + "-review",
            },
        )
        adapter = "reviewer_catalog_staged_adapter.py"
        reviewer = command(
            root,
            [
                str(PYTHON),
                "-B",
                str(KIT / "benchmarks" / adapter),
                "--snapshot",
                str(SNAPSHOT),
                *(["--staged"] if arm.startswith("candidate") else []),
                "--request",
                str(root / ".agent/review-request.json"),
                "--config",
                str(root / ".agent/config.json"),
                "--report",
                str(root / ".agent/reviewer.json"),
            ],
            timeout=900,
        )
        write(root / ".agent/reviewer-invocation.json", reviewer)
    verify_hashes(
        root, {name: sha for name, sha in inputs["protected"].items() if name != TARGET}
    )
    facts = {
        "arm": arm,
        "coder_status": report["status"],
        "coder_seconds": coder["seconds"],
        "reviewer_decision": read(root / ".agent/reviewer.json")["decision"]
        if reviewer
        else None,
        "reviewer_seconds": reviewer["seconds"] if reviewer else None,
        "primary_acceptance": False,
        "explorer_invoked": False,
        "coordinator_invoked": False,
    }
    write(BASE / (arm + ".json"), facts)
    print(facts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    if args.action == "register":
        register()
    else:
        {"prepare": prepare, "run": run}[args.action](args.arm)
