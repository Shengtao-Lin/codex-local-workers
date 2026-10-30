"""R3 registration/installation and frozen fixtures. No model calls."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import shutil

import harness_convergence as B

BATCH = B.KIT / "benchmarks/work/harness-convergence/r3-host-20261015-1"
R0 = B.KIT / "benchmarks/work/harness-convergence/r1-r2-20261013-2"
R2 = B.KIT / "benchmarks/work/harness-convergence/r2-boundary-20261014-1"
PRESENCE = (
    B.KIT
    / "benchmarks/work/system-convergence/single-function-terminal-20261012-1/presence-1/isolated"
)
PYTHON = B.KIT.parent / "agent-evaluation-harness/.venv/Scripts/python.exe"
ORDER = [
    f"{task}-{arm}-{repeat}"
    for repeat in range(1, 4)
    for task in ("repair", "presence")
    for arm in (("baseline", "candidate") if repeat != 2 else ("candidate", "baseline"))
]


def copy_inputs(source, root):
    root.mkdir(parents=True, exist_ok=False)
    for folder in ("src", "tests"):
        shutil.copytree(
            source / folder,
            root / folder,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache"
            ),
        )
    shutil.copyfile(source / "pyproject.toml", root / "pyproject.toml")


def prepare():
    B.save(
        BATCH / "registration.json",
        {
            "stage": "R3",
            "feature_id": "host-proposal-v1",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "rationale": "New versioned execution/acceptance boundary; high risk remains high in isolated fixtures",
            "dependencies": [
                "R2 owned qualified",
                "all offline controls and installation before live",
                "R4 holdouts frozen before live",
            ],
            "owned_contract_ids": [
                "scope-preservation",
                "actual-current-validation",
                "unknown-is-not-confirmed",
                "independent-review",
                "immutable-history",
            ],
            "order": ORDER,
            "registered": 12,
            "candidate_denominator": 6,
            "gate": "candidate six complete-chain Primary accepts, each task three; zero protection/safety failures",
            "stop": "First candidate quality failure makes gate unreachable; retain remaining NOT_RUN. No second candidate; usage >=30 stops new calls.",
            "usage_start": 0,
            "usage_ceiling": 30,
            "r4_live_authorized": False,
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
            },
            "single_model_residency": True,
            "budgets": {
                "model_requests": 6,
                "effective_patches": 3,
                "checks_including_baseline_and_format_recheck": 3,
                "repairs": 2,
                "request_seconds": 180,
                "unit_seconds": 900,
                "reviewer_calls_per_unit": 1,
            },
            "r2_to_r3_input_delta": "Same literal renderer, strict whole JSON parser, plain transport, prompt and terminal boundary. Generic complete packet fields plus current host checks and deterministic receipts replace task-specific frozen R2 diagnostics. Initial fresh check consumes one of three checks, not a free preflight.",
            "baseline": "R0 checkpoint runtime and receiver; budget-only local-code wrapper, six hard turns with no reserve. No baseline prompt/algorithm edits.",
            "reviewer": "Same frozen model, prompt, checks and semantic candidate. New receiver accepts only verified host facts, not fabricated contract_check. No startup retry/token-budget change.",
            "primary_intervention": "Only preparation and independent final review; no live semantic hints or production code repair",
            "primary_active_seconds": None,
        },
    )
    staging = BATCH / "install-source"
    staging.mkdir()
    shutil.copyfile(B.KIT / "AGENTS.md", staging / "AGENTS.md")
    shutil.copytree(
        B.KIT / ".local-agents",
        staging / ".local-agents",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "config.json"),
    )
    target = BATCH / "install-target"
    target.mkdir()
    spec = importlib.util.spec_from_file_location(
        "r3_installer", B.KIT / "scripts/install_local_agents.py"
    )
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    preview = installer.install(staging, target)
    installed = installer.install(staging, target, apply=True)
    again = installer.install(staging, target)
    assert not again["copy"] and not again["conflict"]
    assert not (target / ".local-agents/config.json").exists()
    for name in (
        "host-proposal.py",
        "host-proposal-protocol.py",
        "proposal-interface.py",
    ):
        assert B.sha(target / ".local-agents" / name) == B.sha(
            B.KIT / ".local-agents" / name
        )
    B.save(
        BATCH / "installation.json",
        {
            "preview": preview,
            "installed": installed,
            "idempotent": again,
            "default_enabled": False,
        },
    )
    cases = {}
    for name in ORDER:
        task, arm, _ = name.split("-")
        source = R2 / "cases/raw-1/isolated" if task == "repair" else PRESENCE
        root = BATCH / "cases" / name / "isolated"
        copy_inputs(source, root)
        packet = B.read(source / ".agent/packet.json")
        if task == "repair":
            # Use the already-qualified matched R2 task statement, not the
            # older packet's stale 159-character line hint. Same in both arms.
            packet["goal"] = B.read(R2 / "cases/owned-1/rendered-request.json")[
                "facts"
            ]["goal"]
        if task == "presence":
            old_run = (
                source / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
            )
            for item in B.read(old_run / "preimages.json"):
                if item["path"] in packet["scope"]["modify"]:
                    assert B.sha(source / item["archive_path"]) == item["sha256"]
                    shutil.copyfile(source / item["archive_path"], root / item["path"])
        config = B.read(R0 / "cases/failed-draft-formal-1/isolated/.agent/config.json")
        config["coder_single_function"] = B.read(source / ".agent/config.json")[
            "coder_single_function"
        ]
        if task == "presence":
            presence_config = B.read(source / ".agent/config.json")
            config["validation_profiles"] = presence_config["validation_profiles"]
        packet["task_id"] = "r3-" + task
        packet["run_id"] = "r3-20261015-" + name
        packet.setdefault("limits", {}).update(
            max_model_turns=6,
            hard_max_model_turns=6,
            repair_turn_reserve=0,
            prevalidation_edit_turn_reserve=0,
            max_local_repairs=2,
        )
        config.update(
            max_model_turns=6,
            hard_max_model_turns=6,
            repair_turn_reserve=0,
            prevalidation_edit_turn_reserve=0,
            coordinator_enabled=False,
        )
        if arm == "candidate":
            config.update(
                host_proposal_enabled=True,
                host_proposal_isolated_high_risk_fixture=True,
                coder_structured_output=False,
                coder_typed_action_arguments=False,
                coder_single_function_patch_repair=False,
            )
            runtime_source = target / ".local-agents"
        else:
            runtime_source = R0 / "checkpoint/.local-agents"
        shutil.copytree(
            runtime_source,
            root / ".local-agents",
            ignore=shutil.ignore_patterns(
                "tests", "__pycache__", "*.pyc", "config.json"
            ),
        )
        if arm == "baseline":
            shutil.copyfile(
                B.KIT / "benchmarks/harness_r3_budget_entry.py",
                root / ".local-agents/local-code.py",
            )
        if arm == "baseline":
            shutil.copyfile(
                B.KIT / "benchmarks/harness_r3_baseline_unit.py",
                root / ".local-agents/r3-baseline-unit.py",
            )
        B.save(root / ".agent/packet.json", packet)
        B.save(root / ".agent/config.json", config)
        cases[name] = {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)}
    B.save(BATCH / "prepared-cases.json", cases)
    print(
        "Registered 12 cells; installed default-off modules; prepared paired inputs",
        flush=True,
    )


def holdouts():
    sibling = B.KIT.parent / "agent-evaluation-harness"
    prefix = "src/evaluation_harness/"
    common = prefix + "adapters/common.py"
    selected = [
        "__init__.py",
        "contracts.py",
        "canonical/__init__.py",
        "canonical/models.py",
        "canonical/fingerprint.py",
        "adapters/__init__.py",
        "adapters/common.py",
        "adapters/base.py",
        "adapters/agent_runtime_kit.py",
        "adapters/generic_otel.py",
        "adapters/registry.py",
        "errors.py",
        "trace_sources/__init__.py",
        "trace_sources/base.py",
    ]
    source = (sibling / common).read_text(encoding="utf-8")
    nodes = {
        node.name: node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef)
    }
    records = {}
    for name, symbol in (
        ("message_id", "stable_message_id"),
        ("datetime", "_datetime"),
        ("collect_tools", "collect_tools"),
    ):
        folder = BATCH / "holdouts-v2" / name
        reference = folder / "private-reference"
        visible = folder / "visible"
        for root in (reference, visible):
            for relative in selected:
                dest = root / prefix / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(sibling / prefix / relative, dest)
            (root / "tests").mkdir()
            shutil.copyfile(
                B.KIT / f"benchmarks/fixtures/harness-r4-v1/test_{name}.py",
                root / f"tests/test_{name}.py",
            )
            shutil.copyfile(PRESENCE / "pyproject.toml", root / "pyproject.toml")
        node = nodes[symbol]
        lines = source.splitlines(keepends=True)
        if name == "message_id":
            mutated = (
                "".join(lines[: node.body[0].lineno - 1])
                + '    """'
                + "Stable identifiers must preserve supplied values and deterministic canonical fallback. "
                * 3
                + '"""\n'
                + "".join(lines[node.body[0].lineno - 1 :])
            )
            goal = "Repair only this function's observed E501 docstring; preserve existing exact identifier/fallback semantics, signature and unrelated code."
        else:
            stub = "    return default\n" if name == "datetime" else "    return []\n"
            mutated = (
                "".join(lines[: node.body[0].lineno - 1])
                + stub
                + "".join(lines[node.end_lineno :])
            )
            goal = (
                "Restore datetime identity, parse ISO strings including Z; attach UTC only to naive parsed strings, retain explicit offsets, propagate invalid-string ValueError, return the exact default for every non-string/non-datetime including falsy values."
                if name == "datetime"
                else "Collect ToolCallPart into insertion-ordered call-id map using real CanonicalToolCall. Requests replace existing values without moving order. ToolResultPart updates an existing call via model_copy with exact result (including falsy) and succeeded; unknown result ignored. Preserve input, ignore other parts, fresh result list, original signature/imports/other functions unchanged."
            )
        (visible / common).write_text(mutated, encoding="utf-8", newline="\n")
        checks = {}
        for arm, root in (("reference", reference), ("mutation", visible)):
            output = B.command(
                [
                    str(PYTHON),
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "tests",
                    "--junitxml=" + str(folder / (arm + ".xml")),
                ],
                cwd=root,
            )
            lint = B.command(
                [str(PYTHON), "-B", "-m", "ruff", "check", common], cwd=root
            )
            checks[arm] = {"tests": output, "lint": lint}
        B.save(folder / "controls.json", checks)
        assert (
            checks["reference"]["tests"]["exit_code"] == 0
            and checks["reference"]["lint"]["exit_code"] == 0
        ), name
        assert (
            checks["mutation"]["lint"]["exit_code"] != 0
            if name == "message_id"
            else checks["mutation"]["tests"]["exit_code"] != 0
        ), name
        records[name] = {
            "symbol": symbol,
            "path": common,
            "goal": goal,
            "gold_not_worker_readable": True,
            "source_sha256": B.sha(sibling / common),
            "files": {
                p.relative_to(folder).as_posix(): B.sha(p) for p in B.files(folder)
            },
            "visible_test_file": f"tests/test_{name}.py",
            "reference_and_mutation_control_passed": True,
        }
    B.save(
        BATCH / "holdouts-freeze.json",
        {
            "cases": records,
            "sibling_head": B.command(["git", "rev-parse", "HEAD"], cwd=sibling),
            "not_used_to_tune_candidate": True,
            "live_not_started": True,
        },
    )
    print(
        "Three holdouts frozen with real dependency/reference/mutation controls",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "holdouts"])
    parser.add_argument("--preparation-name", choices=["preparation-v2"])
    args = parser.parse_args()
    if args.preparation_name:
        BATCH = BATCH / args.preparation_name
        BATCH.mkdir(exist_ok=False)
    (prepare if args.action == "prepare" else holdouts)()
