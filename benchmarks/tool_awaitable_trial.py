"""Immutable sibling-source trial: synchronous tools returning awaitables."""

import argparse
import copy
import json
import shutil
import xml.etree.ElementTree as ET

from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes

BASE = WORK / "tool-awaitable-5"
FROZEN = KIT / "benchmarks/fixtures/tool-awaitable-v5"
SOURCE = KIT.parent / "agent-runtime-kit"
SNAPSHOT = WORK / "tool-awaitable-runtime-2"
PYTHON = KIT.parent / "agent-evaluation-harness/.venv/Scripts/python.exe"
TARGET = "src/agent_runtime/tools/registry.py"
EXTRA = "tests/unit/test_awaitable.py"
ARMS = ("fresh-1", "fresh-2")


def role_overrides():
    return {
        "python": str(PYTHON),
        "coordinator_enabled": False,
        "explorer_mode": "locate",
        "coder_repair_focus_retention": "latest",
        "coder_post_edit_validation_hint": True,
        "autoformat_on_diff_whitespace": True,
        "explorer_output_limit_recovery": True,
        "explorer_duplicate_action_report_recovery": True,
    }


def freeze_fixture():
    if not SNAPSHOT.exists():
        freeze(SNAPSHOT.name)
    FROZEN.mkdir(parents=True, exist_ok=False)
    paths = [p.relative_to(SOURCE).as_posix() for p in (SOURCE / "src").rglob("*.py")]
    paths += ["pyproject.toml", "LICENSE", "tests/unit/test_tools.py"]
    for path in paths:
        target = FROZEN / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / path, target)
    shutil.copyfile(
        KIT / "benchmarks/fixtures/tool-awaitable-extra/test_awaitable.py",
        FROZEN / EXTRA,
    )
    write(
        FROZEN / "provenance.json",
        {
            "source": str(SOURCE),
            "original_files": {p: digest(SOURCE / p) for p in paths},
            "files": {p: digest(FROZEN / p) for p in paths + [EXTRA]},
            "task": "New capability extension in frozen copy, not a sibling production fix",
        },
    )
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "weekly_ceiling": 23,
            "coordinator": False,
            "models": "Unchanged E oss / C Qwen / R muse; single-model residency",
            "credit": "Two fresh complete chains; no proposal-only or synthetic Coder credit",
            "risk": "high: public tool result compatibility, deadline and cancellation lifecycle",
            "validation": "Original tools tests plus eight protected contracts; Ruff and strict changed module",
        },
    )


def prepare(arm):
    if arm not in ARMS:
        raise ValueError("model arms only; oracle is independently prepared")
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
    config = read(KIT / ".local-agents/config.json")
    config.update(role_overrides())
    pytest_args = [
        "-B",
        "-m",
        "pytest",
        "-o",
        "pythonpath=src",
        "-p",
        "no:cacheprovider",
    ]
    config["validation_profiles"]["project-strict"] = {
        "python": str(PYTHON),
        "compile": True,
        "pytest_argv": pytest_args + ["--basetemp=" + str(root / ".agent/worker-temp")],
        "commands": [
            {
                "id": "ruff-format",
                "argv": [
                    "{python}",
                    "-B",
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    TARGET,
                    EXTRA,
                ],
            },
            {
                "id": "ruff-check",
                "argv": ["{python}", "-B", "-m", "ruff", "check", TARGET, EXTRA],
            },
            {
                "id": "pyright",
                "argv": [
                    "{python}",
                    "-B",
                    "-m",
                    "pyright",
                    "--project",
                    ".agent/pyright.json",
                    "--pythonpath",
                    str(PYTHON),
                ],
            },
        ],
    }
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
    template = WORK / "limit-sampling-1/semantic-control-2/.agent/packet.json"
    packet = {
        k: v for k, v in copy.deepcopy(read(template)).items() if not k.startswith("_")
    }
    identity = BASE.name + "-" + arm
    contracts = [
        (
            "resolved-output",
            "Resolve a sync callable's returned awaitable exactly once; return its final value in ToolResult. Support coroutine, Future and custom awaitable. Invoke handler once, keep ordinary sync work off the event-loop thread, preserve direct async and plain sync behavior.",
        ),
        (
            "shared-deadline",
            "Use the existing single execution deadline for both sync factory work and returned awaitable completion, never reset a separate timeout. Timeout remains ToolTimeoutError; no success hook on failure.",
        ),
        (
            "failure-cancellation",
            "Deferred errors use the existing ToolExecutionError mapping with the identical original cause. CancelledError propagates, without wrapping or after_tool. Preserve validation, hooks and telemetry behavior outside this extension.",
        ),
        (
            "hook-result-roundtrip",
            "before_tool precedes handler; awaitable resolves before constructing successful result and after_tool; after_tool receives final JSON-roundtrippable value. Do not return or serialize a pending awaitable.",
        ),
    ]
    packet.update(
        task_id=identity,
        feature_id=identity,
        unit_id="awaitable-tools",
        run_id=identity + "-a1",
        goal="Support synchronous tool factories returning awaitables in the real frozen ToolRegistry.",
        risk={
            "feature": "high",
            "unit": "high",
            "integration": "high",
            "reasons": [
                "Public result boundary, shared deadlines, cancellation and hooks remain atomic."
            ],
        },
        owned_contract_ids=[p[0] for p in contracts],
        required_behavior=[
            {"id": ident, "text": text, "risk_floor": "high"}
            for ident, text in contracts
        ],
        scope={
            "read": ["src", "tests"],
            "modify": [TARGET],
            "create": [],
            "readonly": [p for p in provenance["files"] if p != TARGET],
            "forbidden": [".agent", ".local-agents", "AGENTS.md"],
        },
        edit_targets=[
            {"path": TARGET, "anchor": "async def execute", "line_hint": 101}
        ],
        focused_tests=["tests/unit/test_tools.py", EXTRA],
        supplemental_tests=[],
        required_order=[
            "before_tool then handler invocation then awaitable completion then result construction then after_tool"
        ],
        forbidden_orderings=[
            "No success result or after_tool before awaitable completion, or on timeout, deferred error or cancellation"
        ],
        acceptance_scenarios=[
            {
                "id": "normal",
                "text": "sync factory, Future and custom awaitable resolve once",
                "observables": {"output": "final value", "calls": "one"},
            },
            {
                "id": "error",
                "text": "deferred ValueError and cancellation",
                "observables": {"cause": "identical", "after_hook": "absent"},
            },
            {
                "id": "boundary",
                "text": "factory and await each fit but their sum exceeds one timeout",
                "observables": {"error": "ToolTimeoutError"},
            },
            {
                "id": "integration",
                "text": "final hook output serializes through real ToolResult",
                "observables": {"roundtrip": "equal final value"},
            },
        ],
        implementation_guidance=[],
        review_feedback=[],
    )
    load_worker(SNAPSHOT).validate_packet(packet)
    write(root / ".agent/packet.json", packet)
    write(
        root / ".agent/manifest.json",
        {
            "files": provenance["files"],
            "packet_sha256": digest(root / ".agent/packet.json"),
            "config_sha256": digest(root / ".agent/config.json"),
        },
    )
    result = command(
        root,
        [
            str(PYTHON),
            *pytest_args,
            *packet["focused_tests"],
            "-q",
            "--basetemp=.agent/baseline-temp",
            "--junitxml=.agent/baseline.xml",
        ],
    )
    write(root / ".agent/baseline.json", result)
    print(json.dumps(result))


def run(arm, explorer=False, narrowed=False):
    if arm not in ARMS:
        raise ValueError("oracle must never reach a model")
    if not read(BASE / "primary-oracle/.agent/primary-verification.json")["passed"]:
        raise ValueError("positive fixture preflight required")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    root = BASE / arm
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(SOURCE, provenance["original_files"])
    if explorer:
        task = (
            "Locate the controlling execute branch in src/agent_runtime/tools/registry.py, the ToolResultContent construction containing result=tool_result.output in src/agent_runtime/adapters/native.py, and the COMPLETE test_factory_and_await_share_one_deadline in tests/unit/test_awaitable.py (include both delays, configured timeout and final assertion). Cite these three bounded ranges, total <=80 lines; do not substitute the outer invoke call for the output consumer. Return only read source_refs; no semantic verdict."
            if read(root / ".agent/config.json").get("explorer_mode") == "locate"
            else "In tools/registry.py execute, does awaiting asyncio.to_thread(handler) await a coroutine returned BY that sync handler, or only return the coroutine object? Read that controlling branch and NativeAgentInvoker's ToolResultContent(result=tool_result.output) consumer in adapters/native.py. Distinguish outer invoke completion from the nested output value; cite real lines and state uncertainty. Do not assume an async function's annotated ToolResult guarantees a resolved output."
            if narrowed
            else "Trace how NativeAgent consumes ToolRegistry.invoke output before the next model call. Start at src/agent_runtime/adapters/native.py and tools/registry.py. Provide real file/line evidence for the result consumer and whether returning an unresolved awaitable would cross its serialization boundary. One focused question; no editing."
        )
        argv = [
            str(PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--config",
            str(root / ".agent/config.json"),
            "--task-id",
            BASE.name + "-" + arm,
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
            "--task",
            task,
        ]
    else:
        argv = [
            str(PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(
                root
                / (
                    ".agent/packet-v2.json"
                    if (root / ".agent/packet-v2.json").exists()
                    else ".agent/packet.json"
                )
            ),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/coder.json"),
            "--review-report",
            str(root / ".agent/reviewer.json"),
        ]
    result = command(root, argv, timeout=1500)
    write(
        root
        / (".agent/explorer-invocation.json" if explorer else ".agent/invocation.json"),
        result,
    )
    print(json.dumps(result))


def condense(arm):
    root = BASE / arm
    if (root / ".agent/coder.json").exists():
        raise ValueError("cannot revise packet after this invocation")
    judgement = read(root / ".agent/explorer-primary.json")
    if not (
        judgement.get("semantic_answer_accepted")
        or judgement.get("primary_context_verified")
    ):
        raise ValueError("Primary source adjudication required")
    packet = read(root / ".agent/packet.json")
    packet["packet_revision"] += 1
    packet["implementation_guidance"] = [judgement["verified_context"]]
    load_worker(SNAPSHOT).validate_packet(packet)
    write(root / ".agent/packet-v2.json", packet)
    write(
        root / ".agent/packet-v2-provenance.json",
        {
            "previous_packet_sha256": digest(root / ".agent/packet.json"),
            "new_packet_sha256": digest(root / ".agent/packet-v2.json"),
            "explorer_report_sha256": digest(root / ".agent/explorer.json"),
            "primary_adjudication_sha256": digest(
                root / ".agent/explorer-primary.json"
            ),
            "scope_contract_tests_unchanged": True,
        },
    )


def verify(arm):
    root = BASE / arm
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(SOURCE, provenance["original_files"])
    verify_hashes(
        root, {p: sha for p, sha in provenance["files"].items() if p != TARGET}
    )
    commands = [
        [
            "pytest",
            "-o",
            "pythonpath=src",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=.agent/primary-verification-temp",
            "--junitxml=.agent/primary-verification.xml",
        ],
        ["ruff", "format", "--check", TARGET, EXTRA],
        ["ruff", "check", TARGET, EXTRA],
        ["pyright", "--project", ".agent/pyright.json", "--pythonpath", str(PYTHON)],
    ]
    if (root / ".agent/primary-verification.json").exists():
        raise ValueError("verification already exists")
    checks = [command(root, [str(PYTHON), "-B", "-m", *argv]) for argv in commands]
    cases = list(
        ET.parse(root / ".agent/primary-verification.xml").getroot().iter("testcase")
    )
    counts = {
        "tests": len(cases),
        **{
            tag: sum(case.find(tag) is not None for case in cases)
            for tag in ("failure", "error", "skipped")
        },
    }
    facts = {
        "checks": checks,
        "junit": counts,
        "source_sha256": digest(root / TARGET),
        "protected_unchanged": True,
        "sibling_unchanged": True,
        "passed": all(check["exit"] == 0 for check in checks)
        and counts == {"tests": 12, "failure": 0, "error": 0, "skipped": 0},
        "primary_acceptance": False,
        "scope": "Frozen tools closure, not complete sibling project",
    }
    write(root / ".agent/primary-verification.json", facts)
    print(json.dumps({"passed": facts["passed"], "junit": counts}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action", choices=("freeze", "prepare", "explore", "run", "condense", "verify")
    )
    parser.add_argument("--arm", choices=(*ARMS, "primary-oracle"))
    parser.add_argument("--narrowed", action="store_true")
    args = parser.parse_args()
    if args.action == "freeze":
        freeze_fixture()
    elif args.action == "prepare":
        prepare(args.arm)
    elif args.action == "condense":
        condense(args.arm)
    elif args.action == "verify":
        verify(args.arm)
    else:
        run(args.arm, explorer=args.action == "explore", narrowed=args.narrowed)
