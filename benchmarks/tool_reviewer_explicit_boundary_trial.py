"""Correctly placed actual-wire budget over the frozen generic analogy."""

import argparse
import copy
import difflib
import shutil
import xml.etree.ElementTree as ET

from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET

BASE = WORK / "reviewer-explicit-boundary-14"
SNAPSHOT = WORK / "reviewer-all-lines-runtime-16"
OLD = WORK / "tool-native-nudge-1/fresh-2"
GOOD = WORK / "tool-deadline-fresh-1/candidate-1"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v10"
REFERENCE = KIT / "benchmarks/fixtures/tool-library-reference-v2"
THREAD_REFERENCE = KIT / "benchmarks/fixtures/tool-library-reference-v1"
ARMS = (
    "hidden-candidate-1",
    "clean-candidate-1",
    "clean-candidate-2",
    "hidden-candidate-2",
)
ADAPTERS = (
    "tool_reviewer_explicit_boundary_trial.py",
    "reviewer_assembled_request_adapter.py",
    "reviewer_boundary_analogy_adapter.py",
    "fixtures/reviewer-protocol-analogy-v1.json",
    "fixtures/reviewer_protocol_analogy_v1.py",
    "reviewer_wire_budget_adapter.py",
    "reviewer_investigation_phase_adapter.py",
    "reviewer_contract_test_read_adapter.py",
    "reviewer_anchored_catalog_adapter.py",
    "reviewer_catalog_staged_adapter.py",
    "reviewer_evidence_catalog_adapter_v2.py",
    "reviewer_dependency_evidence_adapter.py",
    "reviewer_dependency_investigation_adapter.py",
    "reviewer_range_staged_adapter.py",
    "reviewer_staged_assessment_adapter.py",
    "reviewer_staged_final_gate_adapter.py",
    "reviewer_required_tool_adapter.py",
    "reviewer_sampling_probe_adapter.py",
)


def parent_packet():
    report = read(OLD / ".agent/coder.json")
    return OLD / report["evidence_refs"]["packet"]


def register():
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(REFERENCE, read(REFERENCE / "provenance.json")["files"])
    verify_hashes(THREAD_REFERENCE, read(THREAD_REFERENCE / "provenance.json")["files"])
    write(
        BASE / "registration.json",
        {
            "arms": ARMS,
            "weekly_ceiling": 30,
            "axis": "Clarify the public plain-result boundary in required_behavior and a stable acceptance scenario: JSON-compatible mapping may explicitly disable await protocol and must remain a plain identity-preserved result. No implementation predicate or patch prescribed; model still independently checks actual source and dependency. This is contract-guided qualification, NOT blind discovery or unseen-boundary credit. Same assembled protocol, models and budgets.",
            "origin": "Synthetic canonical archive, no Coder or Explorer invoked. Protected eighteen tests and three configured checks actually executed; held-out plain mapping oracle distinguishes variants. Not real Coder/full-chain/Coordinator credit.",
            "expected": "Clean valid pass without invented defect; hidden source-backed bounded rejection of disabled-__await__ plain JSON mapping misclassification. Unknown/failed reports are not detections.",
            "files": {name: digest(KIT / "benchmarks" / name) for name in ADAPTERS},
            "reference_files": read(REFERENCE / "provenance.json")["files"],
            "thread_reference_files": read(THREAD_REFERENCE / "provenance.json")[
                "files"
            ],
            "fixture_files": read(FROZEN / "provenance.json")["files"],
            "parents": {
                str(path.relative_to(KIT)): digest(path)
                for path in (
                    parent_packet(),
                    OLD / ".agent/nudge-config.json",
                    OLD / ".agent/pyright.json",
                    OLD / TARGET,
                    GOOD / TARGET,
                    GOOD / ".agent/config.json",
                )
            },
        },
    )


def prepare(arm):
    registration = read(BASE / "registration.json")
    verify_hashes(KIT, registration["parents"])
    verify_hashes(FROZEN, registration["fixture_files"])
    verify_hashes(REFERENCE, registration["reference_files"])
    verify_hashes(THREAD_REFERENCE, registration["thread_reference_files"])
    root = BASE / arm
    shutil.copytree(FROZEN, root)
    (root / "reference").mkdir()
    for name in registration["thread_reference_files"]:
        shutil.copyfile(THREAD_REFERENCE / name, root / "reference" / name)
    shutil.copyfile(
        REFERENCE / "awaitable_protocol.txt", root / "reference/awaitable_protocol.txt"
    )
    source = (GOOD / TARGET).read_text(encoding="utf-8")
    if arm.startswith("hidden"):
        source = (OLD / TARGET).read_text(encoding="utf-8")
        old = "return await asyncio.wait_for(result, timeout=tool.timeout_seconds)"
        if source.count(old) != 1:
            raise ValueError("single known inner timer required before isolation")
        source = source.replace(old, "return await result")
    (root / TARGET).write_text(source, encoding="utf-8")
    packet = copy.deepcopy(read(parent_packet()))
    task_id = BASE.name + "-" + arm
    packet.update(
        task_id=task_id,
        feature_id=task_id,
        run_id=task_id + "-synthetic",
        packet_revision=8,
    )
    packet["review_feedback"] = []
    packet["implementation_guidance"] = []
    for behavior in packet["required_behavior"]:
        if behavior["id"] == "resolved-output":
            behavior["text"] += (
                " A valid plain JSON-compatible mapping may explicitly disable participation in the await protocol (__await__ = None); it must be returned unchanged, not awaited or turned into an execution failure merely because that attribute exists."
            )
    packet["acceptance_scenarios"].append(
        {
            "id": "plain-result-protocol-opt-out",
            "text": "A synchronous handler returns a JSON-compatible mapping with an explicitly disabled await protocol. This is a plain successful result, not an awaitable.",
            "observables": {
                "handler_calls": 1,
                "output_identity": "same mapping object",
                "result_status": "succeeded",
                "spurious_execution_error": False,
            },
        }
    )
    for field in ("read", "readonly"):
        packet["scope"][field].append("reference/awaitable_protocol.txt")
    load_worker(SNAPSHOT).validate_packet(packet)
    config = copy.deepcopy(read(OLD / ".agent/nudge-config.json"))
    config["python"] = str(PYTHON)
    config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "caller-context",
            "path": "reference/asyncio_threads.py",
            "anchors": ["copy_context", "ctx.run"],
        },
        {
            "contract_id": "resolved-output",
            "path": "reference/awaitable_protocol.txt",
            "anchors": [
                "def isawaitable",
                "_check_methods(C,",
                "B.__dict__[method] is None",
            ],
        },
    ]
    config["reviewer_require_approved_execution"] = False
    config["reviewer_contract_test_reads"] = [
        {
            "contract_id": "resolved-output",
            "path": "tests/unit/test_async_preservation.py",
        },
        {
            "contract_id": "resolved-output",
            "path": "tests/unit/test_async_generality.py",
        },
    ]
    profile = config["validation_profiles"]["project-strict"]
    profile["python"] = str(PYTHON)
    profile["pytest_argv"] = [
        "--basetemp=" + str(root / ".agent/blind-temp-1")
        if item.startswith("--basetemp=")
        else item
        for item in profile["pytest_argv"]
    ]
    write(root / ".agent/config.json", config)
    write(root / ".agent/pyright.json", read(OLD / ".agent/pyright.json"))
    archive = root / ".agent/tasks" / task_id / "runs" / packet["run_id"]
    write(archive / "packet.json", packet)
    junit = archive / "pytest.xml"
    executions = []
    commands = [
        [
            str(PYTHON),
            *profile["pytest_argv"],
            *packet["focused_tests"],
            "--junitxml=" + str(junit),
        ]
    ]
    commands.extend(
        [
            [str(PYTHON) if value == "{python}" else value for value in item["argv"]]
            for item in profile["commands"]
        ]
    )
    for argv in commands:
        executions.append(command(root, argv, timeout=180))
    write(
        root / ".agent/blind-validation.json",
        {"synthetic_archive": True, "coder_invoked": False, "executions": executions},
    )
    cases = list(ET.parse(junit).getroot().iter("testcase"))
    if (
        any(result["exit"] for result in executions)
        or len(cases) != 18
        or any(
            case.find(tag) is not None
            for case in cases
            for tag in ("failure", "error", "skipped")
        )
    ):
        raise ValueError("real eighteen-test passing blind evidence required")
    write(
        archive / "validation.json",
        {
            "status": "passed",
            "focused_tests": {
                "status": "passed",
                "inputs_unchanged": True,
                "junit": {
                    "available": True,
                    "path": str(junit.relative_to(root)),
                    "executed": 18,
                },
            },
            "configured_checks": [
                {
                    "id": item["id"],
                    "status": "passed",
                    "exit_code": result["exit"],
                    "output": result["output"],
                }
                for item, result in zip(profile["commands"], executions[1:])
            ],
        },
    )
    paths = [
        name for name in registration["fixture_files"] if name != "provenance.json"
    ] + [
        "reference/asyncio_threads.py",
        "reference/PSF-LICENSE.txt",
        "reference/awaitable_protocol.txt",
    ]
    facts = {
        name: {
            "path": name,
            "exists": True,
            "kind": "file",
            "sha256": digest(root / name),
            "size": (root / name).stat().st_size,
        }
        for name in paths
    }
    write(archive / "post-state.json", {"validation_inputs": facts})
    write(archive / "handoff.json", {"status": "ready_for_review"})
    write(
        archive / "completed.json",
        {
            "status": "ready_for_review",
            "synthetic_benchmark_archive": True,
            "coder_invoked": False,
        },
    )
    baseline = (FROZEN / TARGET).read_text(encoding="utf-8")
    (archive / "cumulative.diff").write_text(
        "".join(
            difflib.unified_diff(
                baseline.splitlines(keepends=True),
                source.splitlines(keepends=True),
                fromfile="a/" + TARGET,
                tofile="b/" + TARGET,
            )
        ),
        encoding="utf-8",
    )
    write(
        root / ".agent/request.json",
        {
            "schema_version": 1,
            "task_id": task_id,
            "unit_id": packet["unit_id"],
            "run_id": packet["run_id"],
            "review_id": task_id + "-review",
        },
    )
    oracle = command(
        root,
        [
            str(PYTHON),
            "-B",
            "-m",
            "pytest",
            str(KIT / "benchmarks/fixtures/tool-awaitable-extra/test_plain_result.py"),
            "-o",
            "pythonpath=src",
            "-p",
            "no:cacheprovider",
            "--basetemp=" + str(root / ".agent/oracle-temp-1"),
            "--junitxml=" + str(root / ".agent/oracle-1.xml"),
            "-q",
        ],
        timeout=180,
    )
    write(root / ".agent/oracle-1.json", oracle)
    oracle_cases = list(
        ET.parse(root / ".agent/oracle-1.xml").getroot().iter("testcase")
    )
    failures = sum(case.find("failure") is not None for case in oracle_cases)
    if (
        len(oracle_cases) != 1
        or any(
            case.find("error") is not None or case.find("skipped") is not None
            for case in oracle_cases
        )
        or failures != int(arm.startswith("hidden"))
    ):
        raise ValueError(
            "held-out actual plain-result assertion must distinguish variant"
        )
    immutable_paths = [
        *paths,
        ".agent/config.json",
        ".agent/pyright.json",
        ".agent/request.json",
        ".agent/blind-validation.json",
        ".agent/oracle-1.json",
        ".agent/oracle-1.xml",
        *[
            path.relative_to(root).as_posix()
            for path in archive.iterdir()
            if path.is_file()
        ],
    ]
    write(
        root / ".agent/freeze.json",
        {
            "synthetic_archive": True,
            "files": {name: digest(root / name) for name in immutable_paths},
        },
    )


def run(arm):
    root = BASE / arm
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(KIT / "benchmarks", read(BASE / "registration.json")["files"])
    frozen = read(root / ".agent/freeze.json")["files"]
    verify_hashes(root, frozen)
    invocation = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks/reviewer_assembled_request_adapter.py"),
            "--snapshot",
            str(SNAPSHOT),
            "--request",
            str(root / ".agent/request.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/reviewer.json"),
        ],
        timeout=900,
    )
    write(root / ".agent/reviewer-invocation.json", invocation)
    verify_hashes(root, frozen)
    report = root / ".agent/reviewer.json"
    print(
        {
            "arm": arm,
            "decision": read(report)["decision"]
            if report.exists()
            else "missing_report",
            "seconds": invocation["seconds"],
            "synthetic_archive": True,
            "coder_invoked": False,
            "primary_acceptance": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    {
        "register": register,
        "prepare": lambda: prepare(args.arm),
        "run": lambda: run(args.arm),
    }[args.action]()
