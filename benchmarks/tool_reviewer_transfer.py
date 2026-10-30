"""Reviewer-only real deadline defect controls; no synthetic Coder credit."""

import argparse
import copy
import difflib
import json
import shutil
import xml.etree.ElementTree as ET

from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import EXTRA, PYTHON, SOURCE, TARGET

BASE = WORK / "tool-reviewer-transfer-1"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v5"
SNAPSHOT = WORK / "tool-awaitable-runtime-4"
ARMS = tuple(
    f"{mode}-{variant}-r{r}"
    for r in (1, 2)
    for mode in ("control", "challenge")
    for variant in ("hidden", "clean")
)


def register():
    write(
        BASE / "registration.json",
        {
            "arms_in_order": list(ARMS),
            "weekly_ceiling": 23,
            "family": "shared deadline lost/reset, real ToolRegistry model artifact",
            "control": "Current Reviewer",
            "candidate": "One-shot provisional-pass challenge",
            "models": "Same Muse/config/budgets, single residency, fresh context each call",
            "ordinary_tests": "Two original normal-path cases, not full sibling suite",
            "oracle": "Twelve protected tests including deferred/async timeout, outside readable scope",
            "grading": "Primary actual causal evidence adjudication, not keyword match",
            "credit": "Synthetic archives; Coder and Explorer not invoked, no feature acceptance or savings",
        },
    )


def run(arm):
    if arm not in ARMS:
        raise ValueError("unregistered arm")
    if not (BASE / "registration.json").exists():
        raise ValueError("register first")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    root = BASE / arm
    root.mkdir(parents=True, exist_ok=False)
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(SOURCE, provenance["original_files"])
    verify_hashes(FROZEN, provenance["files"])
    for path in provenance["files"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FROZEN / path, target)
    hidden = "-hidden-" in arm
    actual = (
        WORK
        / "tool-awaitable-5/fresh-2/.agent/tasks/tool-awaitable-5-fresh-2/runs/tool-awaitable-5-fresh-2-a2/preimages"
        / TARGET
        if hidden
        else WORK / "tool-awaitable-3/fresh-2" / TARGET
    )
    expected = (
        "28c50e04aae899c6b58776969b43ce31bb25e00dabdab3b2234cffbac2c01a58"
        if hidden
        else "578f1b8a83f4cedf5cbd46b3c8e19b60cecb7912c1edefb67d385761a77174c7"
    )
    if digest(actual) != expected:
        raise ValueError("actual artifact drift")
    shutil.copyfile(actual, root / TARGET)
    identity = "tool-reviewer-" + arm
    packet = copy.deepcopy(
        read(WORK / "tool-awaitable-5/fresh-1/.agent/packet-v2.json")
    )
    packet.update(
        task_id=identity,
        feature_id=identity,
        run_id=identity,
        implementation_guidance=[],
        review_feedback=[],
    )
    packet["scope"]["read"] = ["src", "tests/unit/test_tools.py"]
    packet["scope"]["readonly"] = [
        p
        for p in provenance["files"]
        if p != TARGET and (p.startswith("src/") or p == "tests/unit/test_tools.py")
    ]
    packet["scope"]["forbidden"].append(EXTRA)
    packet["focused_tests"] = [
        "tests/unit/test_tools.py::test_registry_validates_and_invokes_sync_tool",
        "tests/unit/test_tools.py::test_registry_invokes_async_tool",
    ]
    config = read(WORK / "tool-awaitable-5/fresh-1/.agent/config.json")
    config["reviewer_prepass_challenge"] = arm.startswith("challenge-")
    config["reviewer_finding_challenge"] = arm.startswith("falsify-")
    profile = config["validation_profiles"]["project-strict"]
    profile["pytest_argv"][-1] = "--basetemp=" + str(root / ".agent/reviewer-test-temp")
    for check in profile["commands"][:2]:
        check["argv"][-1] = "tests/unit/test_tools.py"
    write(root / ".agent/config.json", config)
    write(
        root / ".agent/pyright.json",
        {
            "include": ["../" + TARGET],
            "extraPaths": ["../src"],
            "typeCheckingMode": "strict",
            "pythonVersion": "3.11",
        },
    )
    worker = load_worker(SNAPSHOT)
    worker.validate_packet(packet)
    archive = root / ".agent/tasks" / identity / "runs" / identity
    write(archive / "packet.json", packet)
    checks = [
        command(
            root,
            [
                str(PYTHON),
                "-B",
                "-m",
                "pytest",
                "-o",
                "pythonpath=src",
                *packet["focused_tests"],
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=.agent/ordinary-temp",
                "--junitxml=" + str(archive / "pytest.xml"),
            ],
        )
    ]
    for check in profile["commands"]:
        checks.append(
            command(
                root,
                [str(PYTHON) if arg == "{python}" else arg for arg in check["argv"]],
            )
        )
    cases = list(ET.parse(archive / "pytest.xml").getroot().iter("testcase"))
    if (
        any(check["exit"] for check in checks)
        or len(cases) != 2
        or any(list(case) for case in cases)
    ):
        write(root / ".agent/preflight-failure.json", {"checks": checks})
        raise ValueError("ordinary preflight failed, no model call")
    oracle = command(
        root,
        [
            str(PYTHON),
            "-B",
            "-m",
            "pytest",
            "-o",
            "pythonpath=src",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=.agent/oracle-temp",
            "--junitxml=.agent/oracle.xml",
        ],
    )
    if (oracle["exit"] == 0) == hidden:
        raise ValueError("oracle did not distinguish actual artifact")
    write(archive / "preflight.json", {"checks": checks, "oracle": oracle})
    write(
        archive / "validation.json",
        {
            "status": "passed",
            "focused_tests": {
                "status": "passed",
                "inputs_unchanged": True,
                "junit": {"available": True, "executed": 2},
            },
            "configured_checks": [
                {"id": check["id"], "status": "passed", "exit_code": 0}
                for check in profile["commands"]
            ],
        },
    )
    facts = worker.RUN_STATE.facts_for_paths(
        root, [p for p in provenance["files"] if p != EXTRA]
    )
    write(archive / "post-state.json", {"validation_inputs": facts})
    write(
        archive / "handoff.json",
        {"status": "ready_for_review", "synthetic_benchmark_archive": True},
    )
    write(
        archive / "completed.json",
        {"status": "ready_for_review", "synthetic_benchmark_archive": True},
    )
    diff = "".join(
        difflib.unified_diff(
            (FROZEN / TARGET).read_text().splitlines(True),
            (root / TARGET).read_text().splitlines(True),
            fromfile="a/" + TARGET,
            tofile="b/" + TARGET,
        )
    )
    with (archive / "cumulative.diff").open("x", encoding="utf-8") as stream:
        stream.write(diff)
    write(
        root / ".agent/request.json",
        {
            "schema_version": 1,
            "task_id": identity,
            "unit_id": packet["unit_id"],
            "run_id": identity,
            "review_id": identity,
        },
    )
    invocation = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-review.py"),
            "--request",
            str(root / ".agent/request.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/reviewer.json"),
        ],
        timeout=900,
    )
    write(root / ".agent/invocation.json", invocation)
    report = read(root / ".agent/reviewer.json")
    write(
        BASE / (arm + ".json"),
        {
            "root": str(root),
            "decision": report["decision"],
            "findings": report.get("findings"),
            "source_sha256": expected,
            "ordinary_executed": 2,
            "oracle_exit": oracle["exit"],
            "effective_detection": None,
            "requires_primary_adjudication": True,
            "synthetic_coder_archive": True,
            "coder_invoked": False,
        },
    )
    print(
        json.dumps(
            {
                "arm": arm,
                "decision": report["decision"],
                "findings": report.get("findings"),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "run"))
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    register() if args.action == "register" else run(args.arm)
