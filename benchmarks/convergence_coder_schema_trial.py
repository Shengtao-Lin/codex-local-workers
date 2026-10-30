"""Two Coder schema constraints; frozen Reviewer and unchanged real-slice replay."""

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
BASE = KIT / "benchmarks/work/system-convergence/coder-schema-20261011-1"
PREVIOUS = KIT / "benchmarks/work/system-convergence/citation-binding-20261011-1"
ROOT = BASE / "isolated"
PYTHON = KIT.parent / "agent-evaluation-harness/.venv/Scripts/python.exe"
KIT_PYTHON = KIT / "benchmarks/work/stability-v1/.venv-diagnostics/Scripts/python.exe"
FEATURE = "real-trace-batch-pilot"
RUN = "real-trace-batch-pilot-coder-schema-unit-1-a1"
SOURCE = "src/evaluation_harness/trace_sources/mlflow.py"
CHANGED = [".local-agents/worker-runtime.py"]
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def files(directory):
    for parent, dirs, names in os.walk(directory, followlinks=False):
        dirs[:] = [
            d
            for d in dirs
            if d not in {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
        ]
        for name in names:
            path = Path(parent) / name
            if path.is_file() and not path.is_symlink() and path.suffix != ".pyc":
                yield path


def checkpoint():
    BASE.mkdir(exist_ok=False, parents=True)
    tracked = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard"],
        cwd=KIT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    paths = {KIT / p for p in tracked if (KIT / p).is_file()}
    paths.add(KIT / ".local-agents/config.json")
    paths.update(p for p in files(BASE.parent) if not p.is_relative_to(BASE))
    for sibling in (
        KIT.parent / "agent-evaluation-harness",
        KIT.parent / "agent-runtime-kit",
    ):
        for directory in ("src", "tests", ".agent", ".local-agents", "docs"):
            paths.update(files(sibling / directory))
        paths.update(
            p
            for p in (
                sibling / "AGENTS.md",
                sibling / "pyproject.toml",
                sibling / "config.json",
            )
            if p.is_file()
        )
    for relative in CHANGED:
        target = BASE / "preimages" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KIT / relative, target)
    save(BASE / "baseline.json", {str(p): sha(p) for p in sorted(paths)})
    save(
        BASE / "authorization.json",
        {
            "weekly_used_start": 7,
            "weekly_used_ceiling": 15,
            "candidate_files": CHANGED,
            "Reviewer_and_citation_binding": "frozen byte-identical",
            "hard_contract_and_tests": "identical to citation-binding-20261011-1",
            "models_config_sampling_budgets": "unchanged",
            "single_model_residency": True,
            "max_live_calls": {"Coordinator": 1, "Coder": 1, "Reviewer": 1},
            "separate_schema_preflight_requests": 2,
            "external_rework": 0,
            "brothers": "read-only",
            "commit_push": False,
            "candidate": "Packet-aware required VALIDATE.contract_check, single-line schema excludes every CR/LF. No new tools, verdict defaults, prompt, model, sampling or budget changes.",
        },
    )
    print("checkpoint preserved", len(paths), "files", flush=True)


def command(argv, name, *, root=ROOT, python=PYTHON):
    path = BASE / name
    if path.exists():
        raise FileExistsError(path)
    started = time.perf_counter()
    result = subprocess.run(
        [str(python), "-B", *map(str, argv)],
        cwd=root,
        env=ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    save(
        path,
        {
            "exit": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "wall_seconds": time.perf_counter() - started,
            "cloud_tokens": None,
            "Primary_active_seconds": None,
        },
    )
    print(
        name, result.returncode, result.stdout[-1600:], result.stderr[-700:], flush=True
    )
    return result.returncode


def api():
    return load("binding_primary_entry", ROOT / ".local-agents/coordinator-limited.py")


def frozen():
    registration = read(BASE / "registration.json")
    for path, digest in registration["runtime_hashes"].items():
        assert sha(ROOT / path) == digest, path
    for name in ("brief", "context", "config"):
        assert (
            sha(ROOT / (".agent/" + name + ".json")) == registration[name + "_sha256"]
        )
    brief = read(ROOT / ".agent/brief.json")
    for path, digest in brief["source_hashes"].items():
        if path != SOURCE:
            assert sha(ROOT / path) == digest, path


def setup():
    ROOT.mkdir(exist_ok=False)
    dist = BASE / "distribution"
    dist.mkdir(exist_ok=False)
    installer = load("binding_installer", KIT / "scripts/install_local_agents.py")
    for path in installer.inventory(KIT):
        target = dist / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KIT / path, target)
    save(BASE / "installation.json", installer.install(dist, ROOT, apply=True))
    prior_root = PREVIOUS / "isolated"
    old = read(prior_root / ".agent/brief.json")
    for path, digest in old["source_hashes"].items():
        source = (
            KIT / "benchmarks/fixtures/real-trace-batch-v1/original" / path
            if path == SOURCE
            else prior_root / path
        )
        assert sha(source) == digest
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert sha(target) == digest
    brief = copy.deepcopy(old)
    # Preserve the already-qualified citation binding and all business contract metadata.
    save(ROOT / ".agent/brief.json", brief)
    shutil.copyfile(prior_root / ".agent/context.json", ROOT / ".agent/context.json")
    shutil.copyfile(prior_root / ".agent/config.json", ROOT / ".agent/config.json")
    save(ROOT / ".agent/accepted-refs.json", {})
    api().BRIEF.validate_brief(brief)
    save(
        BASE / "registration.json",
        {
            "runtime_hashes": {
                p.relative_to(ROOT).as_posix(): sha(p)
                for p in files(ROOT / ".local-agents")
            },
            "brief_sha256": sha(ROOT / ".agent/brief.json"),
            "context_sha256": sha(ROOT / ".agent/context.json"),
            "config_sha256": sha(ROOT / ".agent/config.json"),
            "driver_sha256": sha(Path(__file__)),
            "old_source_test_profile_hashes_identical": True,
            "contract_metadata_unchanged": True,
        },
    )
    shutil.copyfile(Path(__file__), BASE / "frozen-driver.py")
    print("unchanged slice prepared", ROOT, flush=True)


def entry(action, extras, name):
    frozen()
    return command(
        [
            ROOT / ".local-agents/coordinator-limited.py",
            action,
            "--brief",
            ROOT / ".agent/brief.json",
            "--proposal",
            ROOT / ".agent/proposal.json",
            "--config",
            ROOT / ".agent/config.json",
            *extras,
        ],
        name,
    )


def packet():
    frozen()
    plan = read(ROOT / ".agent/approval.json")["approved_plan"]
    assert len(plan["units"]) == 1
    unit = plan["units"][0]
    assert unit["owner"] == "local-coder" and unit["risk"] == "high"
    materialized = api().CONTRACT.materialize_bounded_packet(
        plan,
        {
            "unit_id": "unit-1",
            "run_id": RUN,
            "attempt": 1,
            "packet_revision": 1,
            "goal": read(ROOT / ".agent/brief.json")["goal"],
            "scope": {
                "read": unit["scope_authority"]["read_roots"],
                "modify": [SOURCE],
                "create": [],
            },
            "edit_targets": [
                {"path": SOURCE, "anchor": "class MlflowTraceSource", "line_hint": 40}
            ],
            "focused_tests": unit["packet_contract"]["required_focused_tests"],
            "supplemental_tests": [],
            "implementation_guidance": [],
        },
    )
    old = read(PREVIOUS / "isolated/.agent/unit-1-packet.json")
    current = copy.deepcopy(materialized)
    for key in ("run_id", "primary_plan_sha256"):
        old.pop(key, None)
        current.pop(key, None)
    assert current == old, "Unapproved packet drift"
    save(ROOT / ".agent/unit-1-packet.json", materialized)


def integration():
    frozen()
    assert (
        command(
            [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests",
                "--junitxml",
                ROOT / ".agent/integration.xml",
            ],
            "integration-tests.json",
        )
        == 0
    )
    for check in ("check", "format"):
        assert (
            command(
                [
                    "-m",
                    "ruff",
                    check,
                    *(["--check"] if check == "format" else []),
                    "src",
                    "tests",
                ],
                "integration-ruff-" + check + ".json",
            )
            == 0
        )
    assert (
        command(["-m", "pyright", "--pythonpath", PYTHON], "integration-pyright.json")
        == 0
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "checkpoint",
            "setup",
            "propose",
            "approve",
            "packet",
            "dispatch",
            "integration",
        ],
    )
    parser.add_argument("--note")
    args = parser.parse_args()
    if args.action in {"checkpoint", "setup", "packet", "integration"}:
        globals()[args.action]()
    elif args.action == "propose":
        sys.exit(
            entry(
                "propose",
                ["--context", ROOT / ".agent/context.json", "--authorize-step"],
                "coordinator-propose.json",
            )
        )
    elif args.action == "approve":
        sys.exit(
            entry(
                "approve",
                [
                    "--approval",
                    ROOT / ".agent/approval.json",
                    "--authorize-step",
                    "--note",
                    args.note,
                ],
                "primary-approve.json",
            )
        )
    else:
        sys.exit(
            entry(
                "dispatch",
                [
                    "--approval",
                    ROOT / ".agent/approval.json",
                    "--refs",
                    ROOT / ".agent/accepted-refs.json",
                    "--packet",
                    ROOT / ".agent/unit-1-packet.json",
                    "--authorize-step",
                ],
                "unit-1-dispatch.json",
            )
        )
