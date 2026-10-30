"""I1-limited installation and one frozen chain through the installed entry."""

import argparse
import ast
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

from convergence_coder import KIT, PYTHON, save
from system_convergence import junit_counts, read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/integration-delivery-20261011-3"
M1 = KIT / "benchmarks/work/system-convergence/mixed-execution-20261011-2"
ROOT = BASE / "installed"
DIST = BASE / "distribution"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def command(root, argv, output, python=PYTHON):
    if output.exists():
        raise FileExistsError(str(output))
    start = time.perf_counter()
    result = subprocess.run(
        [str(python), "-B", *map(str, argv)],
        cwd=root,
        env=ENV,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    save(
        output,
        {
            "exit": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "wall_seconds": time.perf_counter() - start,
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )
    print(
        output.name,
        result.returncode,
        result.stdout[-1000:],
        result.stderr[-500:],
        flush=True,
    )
    return result.returncode


def setup():
    BASE.mkdir(parents=True, exist_ok=True)
    installer = load("limited_installer", KIT / "scripts/install_local_agents.py")
    DIST.mkdir(exist_ok=False)
    ROOT.mkdir(exist_ok=False)
    for relative in installer.inventory(KIT):
        target = DIST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KIT / relative, target)
    # A source-private sentinel must not be copied by the real installer.
    save(DIST / ".local-agents/.agent/private.json", {"not_distributable": True})
    save(
        ROOT / ".local-agents/config.json", {"target_sentinel": "must remain unchanged"}
    )
    config_hash = sha256(ROOT / ".local-agents/config.json")
    preview = installer.install(DIST, ROOT)
    assert not (ROOT / "AGENTS.md").exists()
    installed = installer.install(DIST, ROOT, apply=True)
    repeated = installer.install(DIST, ROOT, apply=True)
    assert not repeated["copy"] and not repeated["conflict"]
    assert sha256(ROOT / ".local-agents/config.json") == config_hash
    assert not (ROOT / ".local-agents/.agent").exists()
    assert not (ROOT / "benchmarks").exists() and not (ROOT / ".agent").exists()
    conflict = BASE / "conflict-target"
    conflict.mkdir(exist_ok=False)
    (conflict / "AGENTS.md").write_text(
        "project-owned installation conflict sentinel\n", encoding="utf-8"
    )
    blocked = installer.plan(DIST, conflict)
    try:
        installer.install(DIST, conflict, apply=True)
        raise AssertionError("conflict install accepted")
    except installer.InstallError:
        assert not (conflict / ".local-agents").exists()
    save(
        BASE / "installation-1.json",
        {
            "preview": preview,
            "apply": installed,
            "repeat": repeated,
            "conflict": blocked,
            "config_preserved": True,
            "history_not_copied": True,
            "source": str(DIST),
            "target": str(ROOT),
            "entry_is_installed_not_benchmark": True,
        },
    )
    prior = M1 / "features/async-receipt/B"
    brief = read_object(prior / ".agent/brief.json")
    context = read_object(prior / ".agent/context.json")
    # Context is text-normalized. Preserve original bytes (including CRLF) from
    # canonical preimages instead of reconstructing frozen files from model text.
    for path, digest in brief["source_hashes"].items():
        source = prior / path
        if path in brief["authority"]["modify"]:
            candidates = [
                prior / image["archive_path"]
                for manifest in (prior / ".agent/tasks").glob("*/runs/*/preimages.json")
                for image in json.loads(manifest.read_text())
                if image["path"] == path and image["sha256"] == digest
            ]
            source = next(p for p in candidates if sha256(p) == digest)
        assert sha256(source) == digest, path
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert sha256(target) == digest
    brief = copy.deepcopy(brief)
    brief["feature_id"] = brief["task_id"] = "i1-limited-async-receipt"
    config = read_object(prior / ".agent/config.json")
    for path, value in {
        "brief.json": brief,
        "context.json": context,
        "config.json": config,
        "accepted-refs.json": {},
    }.items():
        save(ROOT / ".agent" / path, value)
    for file in (
        "coordinator-limited.py",
        "coordinator-supervised.py",
        "local-unit.py",
    ):
        assert (
            command(
                ROOT,
                [ROOT / ".local-agents" / file, "--help"],
                BASE / (file + "-help.json"),
            )
            == 0
        )
    save(
        BASE / "preparation.json",
        {
            "fixture_origin": str(prior),
            "source_hashes": brief["source_hashes"],
            "registered_live": {
                "Coordinator": 1,
                "Coder": 2,
                "Reviewer": 2,
                "Explorer": 0,
            },
            "Explorer_not_called_reason": "Same frozen question and locations already independently verified in M1; no new investigation",
            "external_rework": 0,
            "one_chain_only": True,
            "root": str(ROOT),
            "user_authorized_stage": "formal entry, install, frozen dependency smoke",
            "classification_primary_owned": True,
            "old_failures_unchanged": True,
        },
    )


def freeze():
    counts = junit_counts(BASE / "combined-regression-3.xml")
    assert not counts["failures"] and not counts["errors"] and counts["executed"] > 1000
    for name in (
        "runtime-ruff-check",
        "runtime-ruff-format",
        "driver-ruff-check",
        "driver-ruff-format",
        "entry-pyright",
    ):
        assert read_object(BASE / (name + ".json"))["exit"] == 0
    save(
        BASE / "registration.json",
        {
            "stage": "I1-limited",
            "entry": "installed/.local-agents/coordinator-limited.py",
            "runtime": [
                ref(ROOT, p.relative_to(ROOT).as_posix())
                for p in (ROOT / ".local-agents").rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            ],
            "inputs": [
                ref(ROOT, ".agent/" + p)
                for p in ("brief.json", "context.json", "config.json")
            ],
            "driver": ref(KIT, "benchmarks/convergence_limited_delivery.py"),
            "controls": ref(BASE, "entry-controls-3.xml"),
            "full_regression": ref(BASE, "combined-regression-3.xml"),
            "installation": ref(BASE, "installation-1.json"),
            "live_budget": {"Coordinator": 1, "Coder": 2, "Reviewer": 2, "Explorer": 0},
            "external_rework": 0,
            "failure_means_HOLD": True,
            "old_M1": ref(M1, "stage-decision-1.json"),
        },
    )


def frozen():
    registration = read_object(BASE / "registration.json")
    for item in registration["runtime"] + registration["inputs"]:
        assert sha256(ROOT / item["path"]) == item["sha256"], (
            "installed candidate drift"
        )
    assert (
        sha256(KIT / registration["driver"]["path"]) == registration["driver"]["sha256"]
    )
    return registration


def entry(action, output, extras=()):
    frozen()
    argv = [
        ROOT / ".local-agents/coordinator-limited.py",
        action,
        "--brief",
        ROOT / ".agent/brief.json",
        "--proposal",
        ROOT / ".agent/proposal.json",
        "--config",
        ROOT / ".agent/config.json",
        *extras,
    ]
    return command(ROOT, argv, BASE / output)


def packet(unit_id):
    frozen()
    api = load("i1_primary_materializer", ROOT / ".local-agents/coordinator-limited.py")
    brief = read_object(ROOT / ".agent/brief.json")
    proposal = read_object(ROOT / ".agent/proposal.json")["proposal"]
    plan = read_object(ROOT / ".agent/approval.json")["approved_plan"]
    unit = next(u for u in plan["units"] if u["unit_id"] == unit_id)
    targets = []
    for path in unit["scope_authority"]["modify"]:
        function = next(
            n
            for n in ast.parse((ROOT / path).read_text()).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        targets.append(
            {"path": path, "anchor": function.name, "line_hint": function.lineno}
        )
    result = api.CONTRACT.materialize_bounded_packet(
        plan,
        {
            "unit_id": unit_id,
            "run_id": brief["task_id"] + "-" + unit_id + "-a1",
            "attempt": 1,
            "packet_revision": 1,
            "goal": next(
                u["goal"]
                for u in proposal["units"]
                if u["contracts"] == unit["owned_contract_ids"]
            ),
            "scope": {
                "read": unit["scope_authority"]["read_roots"],
                "modify": unit["scope_authority"]["modify"],
                "create": [],
            },
            "edit_targets": targets,
            "focused_tests": unit["packet_contract"]["required_focused_tests"],
            "supplemental_tests": [],
            "implementation_guidance": [],
        },
    )
    save(ROOT / (".agent/" + unit_id + "-packet.json"), result)


def accept(unit_id, note):
    frozen()
    api = load("i1_primary_accept", ROOT / ".local-agents/coordinator-limited.py")
    step = ROOT / ".agent/limited/i1-limited-async-receipt" / unit_id
    coder, reviewer = (
        read_object(step / "coder.json"),
        read_object(step / "reviewer.json"),
    )
    assert (
        coder["status"] == "ready_for_review"
        and reviewer["decision"] == "pass_to_primary"
    )
    gate = api.load("i1_current_handoff", "local-unit.py")
    gate.verify_handoff(ROOT, coder)
    packet_ = read_object(step / "packet.json")
    assert (
        command(
            ROOT,
            [
                ROOT / ".local-agents/record-review.py",
                "--task-id",
                packet_["task_id"],
                "--run-id",
                packet_["run_id"],
                "--decision",
                "accept",
                "--summary",
                note,
                "--repo",
                ROOT,
            ],
            BASE / (unit_id + "-accept.json"),
        )
        == 0
    )
    # Each step supplies a new immutable refs file instead of updating historical refs.
    refs = (
        read_object(ROOT / ".agent/accepted-refs.json")
        if unit_id == "unit-1"
        else read_object(ROOT / ".agent/accepted-refs-unit-1.json")
    )
    refs[unit_id] = {"task_id": packet_["task_id"], "run_id": packet_["run_id"]}
    save(ROOT / (".agent/accepted-refs-" + unit_id + ".json"), refs)
    plan = read_object(ROOT / ".agent/approval.json")["approved_plan"]
    api.accepted_state(
        ROOT, plan, read_object(ROOT / ".agent/brief.json")["source_hashes"], refs
    )


def integration():
    frozen()
    assert (
        entry(
            "inspect",
            "final-inspect.json",
            [
                "--approval",
                ROOT / ".agent/approval.json",
                "--refs",
                ROOT / ".agent/accepted-refs-unit-2.json",
            ],
        )
        == 0
    )
    assert (
        command(
            ROOT,
            [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml",
                ROOT / ".agent/integration.xml",
            ],
            BASE / "integration.json",
        )
        == 0
    )
    for check in ("check", "format"):
        argv = [
            "-m",
            "ruff",
            check,
            *(["--check"] if check == "format" else []),
            "src",
            "tests",
        ]
        assert command(ROOT, argv, BASE / ("integration-ruff-" + check + ".json")) == 0
    assert junit_counts(ROOT / ".agent/integration.xml")["executed"] == 4


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("setup", "freeze", "packet", "accept", "integration")
    )
    parser.add_argument("unit", nargs="?")
    parser.add_argument("--note")
    args = parser.parse_args()
    if args.action in {"setup", "freeze", "integration"}:
        globals()[args.action]()
    elif args.action == "packet":
        packet(args.unit)
    else:
        accept(args.unit, args.note)
