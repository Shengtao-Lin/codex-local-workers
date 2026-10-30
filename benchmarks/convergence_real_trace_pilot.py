"""Frozen, isolated real-source pilot; never deploy or modify a sibling repository."""

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
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
BASE = KIT / "benchmarks/work/system-convergence/real-trace-pilot-20261011-3"
ROOT = BASE / "isolated"
PRIOR = KIT / "benchmarks/work/system-convergence/integration-delivery-20261011-3"
BROTHER = KIT.parent / "agent-evaluation-harness"
PYTHON = BROTHER / ".venv/Scripts/python.exe"
SOURCE = "src/evaluation_harness/trace_sources/mlflow.py"
FEATURE = "real-trace-batch-pilot"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def tree_files(directory):
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


def preservation_snapshot():
    tracked = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard"],
        cwd=KIT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    files = {KIT / p for p in tracked if (KIT / p).is_file()}
    files.add(KIT / ".local-agents/config.json")
    files.update(p for p in tree_files(BASE.parent) if not p.is_relative_to(BASE))
    for sibling in (BROTHER, KIT.parent / "agent-runtime-kit"):
        for directory in ("src", "tests", ".agent", ".local-agents", "docs"):
            files.update(tree_files(sibling / directory))
        files.update(
            p
            for p in (
                sibling / "AGENTS.md",
                sibling / "pyproject.toml",
                sibling / "config.json",
            )
            if p.is_file()
        )
    return {str(p): sha(p) for p in sorted(files)}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def command(argv, name, *, root=ROOT):
    output = BASE / name
    if output.exists():
        raise FileExistsError(output)
    started = time.perf_counter()
    result = subprocess.run(
        [str(PYTHON), "-B", *map(str, argv)],
        cwd=root,
        env=ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    save(
        output,
        {
            "exit": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "wall_seconds": time.perf_counter() - started,
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )
    print(
        name,
        result.returncode,
        result.stdout[-2000:],
        result.stderr[-1000:],
        flush=True,
    )
    return result.returncode


def api():
    return load("real_trace_primary_api", ROOT / ".local-agents/coordinator-limited.py")


def frozen():
    registration = read(BASE / "registration.json")
    assert sha(Path(__file__)) == registration["driver_sha256"]
    for relative, digest in registration["runtime_hashes"].items():
        assert sha(ROOT / relative) == digest, relative
    assert sha(ROOT / ".agent/config.json") == registration["config_sha256"]
    brief = read(ROOT / ".agent/brief.json")
    for relative, digest in brief["source_hashes"].items():
        if relative != SOURCE:
            assert sha(ROOT / relative) == digest, relative


def setup():
    import hashlib

    BASE.mkdir(parents=True, exist_ok=False)
    ROOT.mkdir()
    shutil.copyfile(Path(__file__), BASE / "frozen-driver.py")
    save(BASE / "preservation-baseline.json", preservation_snapshot())
    installer = load("real_trace_installer", KIT / "scripts/install_local_agents.py")
    # Use the previously installed/frozen distributable candidate, not benchmark adapters.
    for item in read(PRIOR / "registration.json")["runtime"]:
        if item["path"] != ".local-agents/config.json":
            assert sha(PRIOR / "installed" / item["path"]) == item["sha256"]
            assert sha(KIT / item["path"]) == item["sha256"]
    install = installer.install(PRIOR / "distribution", ROOT, apply=True)
    copied = [
        SOURCE,
        "src/evaluation_harness/trace_sources/base.py",
        "src/evaluation_harness/trace_sources/__init__.py",
        "src/evaluation_harness/__init__.py",
        "tests/test_mlflow_trace_source.py",
        "pyproject.toml",
    ]
    for relative in copied:
        source = BROTHER / relative
        target = ROOT / relative
        assert source.is_file() and not source.is_symlink()
        assert target.resolve().is_relative_to(ROOT.resolve()) and not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshot = BASE / "original" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, snapshot)
        assert sha(target) == sha(source) == sha(snapshot)
    acceptance = KIT / "benchmarks/fixtures/real-trace-batch-v1/test_get_many.py"
    shutil.copyfile(acceptance, ROOT / "tests/test_get_many.py")
    members = {}
    for node in ast.parse((ROOT / SOURCE).read_text()).body:
        if isinstance(node, ast.ClassDef) and node.name == "MlflowTraceSource":
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    members["MlflowTraceSource." + member.name] = hashlib.sha256(
                        ast.dump(member, include_attributes=False).encode()
                    ).hexdigest()
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            members[node.name] = hashlib.sha256(
                ast.dump(node, include_attributes=False).encode()
            ).hexdigest()
    assert "MlflowTraceSource.get_many" not in members
    save(ROOT / "tests/legacy_members.json", members)
    config = copy.deepcopy(read(PRIOR / "installed/.agent/config.json"))
    profile = copy.deepcopy(config["validation_profiles"]["mixed-strict"])
    profile["commands"].append(
        {
            "id": "pyright",
            "argv": ["{python}", "-m", "pyright", "--pythonpath", "{python}"],
        }
    )
    config["validation_profiles"] = {"real-trace-strict": profile}
    save(ROOT / ".agent/config.json", config)
    contract = (
        "Add async MlflowTraceSource.get_many(self, source_trace_ids: list[str]) -> list[SourceTrace]. "
        "Return a fresh list of the exact SourceTrace objects returned by awaiting self.get(id) "
        "once per input occurrence, sequentially in original order. Preserve duplicate IDs and input list; "
        "empty input returns a fresh empty list without calling get. Propagate the exact original exception "
        "including cancellation and stop without visiting later IDs. No retry, parallelism, deduplication, "
        "filtering, payload rewriting or new MLflow API. All pre-existing methods/functions and the TraceSource "
        "protocol remain unchanged. This is an additive convenience method in an isolated copy, not an "
        "existing bug claim or deployment."
    )
    sources = [*copied, "tests/test_get_many.py", "tests/legacy_members.json"]
    brief = {
        "schema_version": 1,
        "revision": 1,
        "feature_id": FEATURE,
        "task_id": FEATURE,
        "goal": contract,
        "feature_risk": "high",
        "integration_risk": "high",
        "risk_rationale": "Primary: additive public method has compatibility risk floor high. Exact known sequential-await collection, no new lifecycle/concurrency authority. Full Primary review required.",
        "contracts": [
            {"id": "sequential-trace-batch", "text": contract, "risk_floor": "high"}
        ],
        "authority": {
            "read_roots": ["src", "tests", "pyproject.toml"],
            "modify": [SOURCE],
            "create": [],
            "readonly": [p for p in sources if p != SOURCE],
            "forbidden": [".agent", ".git", ".local-agents", "AGENTS.md"],
        },
        "max_units": 1,
        "atomic_contract_groups": [],
        "contract_edges": [],
        "integration_tests": [
            "tests/test_get_many.py",
            "tests/test_mlflow_trace_source.py",
        ],
        "source_hashes": {p: sha(ROOT / p) for p in sources},
        "validation_profile": "real-trace-strict",
        "acceptance_catalog": {
            "sequential-trace-batch": {
                "acceptance_criteria": [
                    {"id": "sequential-trace-batch", "text": contract}
                ],
                "acceptance_scenarios": [
                    {
                        "id": "normal",
                        "text": "Preserve ordered duplicate IDs, exact returned objects and raw false values; real get/conversion round-trip.",
                        "observables": {
                            "tests": "test_batch_preserves_order_duplicates_and_identity; test_batch_roundtrip_uses_real_get_and_conversion"
                        },
                    },
                    {
                        "id": "error",
                        "text": "Identical error/cancellation propagates; no later get starts.",
                        "observables": {
                            "tests": "test_batch_stops_and_propagates_identical_exception"
                        },
                    },
                    {
                        "id": "boundary",
                        "text": "Empty fresh list, no calls, existing source method ASTs unchanged.",
                        "observables": {
                            "tests": "test_empty_batch_does_not_get_and_returns_fresh_list; test_legacy_members_are_unchanged"
                        },
                    },
                ],
                "required_order": [],
                "forbidden_orderings": [],
                "validation_profile": "real-trace-strict",
                "required_focused_tests": [
                    "tests/test_get_many.py",
                    "tests/test_mlflow_trace_source.py",
                ],
            }
        },
        "capability_catalog": {
            "sequential-trace-batch": {
                "owner": "local-coder",
                "route": "direct_local",
                "modify": [SOURCE],
                "evidence": str(PRIOR / "stage-decision-1.json"),
                "qualification": "Primary-reviewed transfer probe of the same sequential await/collect/stop algorithm, not an expansion to general async/MLflow/classification capability. Local pass is provisional until independent Primary acceptance.",
            }
        },
        "capability_route": {
            "authority": "Primary",
            "unknown_family": "reject local dispatch",
            "classification": "primary-owned",
        },
    }
    api().BRIEF.validate_brief(brief)
    save(ROOT / ".agent/brief.json", brief)
    save(
        ROOT / ".agent/context.json",
        {p: (ROOT / p).read_text() for p in copied if p.endswith(".py")},
    )
    save(ROOT / ".agent/accepted-refs.json", {})
    save(
        BASE / "preparation.json",
        {
            "installation": install,
            "origin": str(BROTHER),
            "copied_unchanged": {p: sha(BROTHER / p) for p in copied},
            "live_budget": {
                "coordinator_proposals": 1,
                "coder_calls": 1,
                "fresh_reviewer": 1,
                "external_rework": 0,
                "explorer": "NOT_CALLED: locations already independently read; no unanswered investigation",
            },
            "weekly_used_start": 6,
            "weekly_used_ceiling": 15,
            "baseline": "Correct original source; requested additive feature is absent",
            "classification": "Primary-owned; unchanged",
            "real_mlflow": "NOT_RUN; fake client only",
            "criteria": "Protected tests and project Ruff/Pyright pass, fresh Reviewer pass, full Primary diff review, current canonical integration. No new candidate/prompts/resampling.",
        },
    )
    save(
        BASE / "registration.json",
        {
            "driver_sha256": sha(Path(__file__)),
            "runtime_hashes": {
                str(p.relative_to(ROOT)): sha(p)
                for p in (ROOT / ".local-agents").rglob("*")
                if p.is_file()
            },
            "config_sha256": sha(ROOT / ".agent/config.json"),
            "brief_sha256": sha(ROOT / ".agent/brief.json"),
            "context_sha256": sha(ROOT / ".agent/context.json"),
        },
    )
    print("prepared", ROOT, flush=True)


def checks(prefix, *, legacy=False):
    frozen()
    selectors = ["tests/test_mlflow_trace_source.py"] if legacy else ["tests"]
    code = command(
        [
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            *selectors,
            "--junitxml",
            BASE / (prefix + ".xml"),
        ],
        prefix + "-tests.json",
    )
    for check in ("check", "format"):
        code |= command(
            [
                "-m",
                "ruff",
                check,
                *(["--check"] if check == "format" else []),
                "src",
                "tests",
            ],
            prefix + "-ruff-" + check + ".json",
        )
    code |= command(["-m", "pyright", "--pythonpath", PYTHON], prefix + "-pyright.json")
    return code


def controls():
    frozen()
    before = sha(ROOT / SOURCE)
    results = {}
    # Runtime-only oracles/mutants live outside worker-readable source and never edit it.
    variants = {
        "reference": "return [await self.get(key) for key in ids]",
        "deduplicate": "return [await self.get(key) for key in dict.fromkeys(ids)]",
        "parallel": "return await asyncio.gather(*(self.get(key) for key in ids))",
        "swallow": "\n    try:\n        return [await self.get(key) for key in ids]\n    except BaseException:\n        return []",
    }
    for name, body in variants.items():
        code = (
            "import sys, asyncio, pytest\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path('src').resolve()))\n"
            "from evaluation_harness.trace_sources.mlflow import MlflowTraceSource\n"
            "import evaluation_harness.trace_sources.mlflow as module\n"
            "assert Path(module.__file__).resolve().is_relative_to(Path.cwd())\n"
            + "exec("
            + repr("async def oracle(self, ids):\n    " + body + "\n")
            + ")\n"
            "MlflowTraceSource.get_many = oracle\n"
            "raise SystemExit(pytest.main(['tests', '-q', '-p', 'no:cacheprovider', '--junitxml', "
            + repr(str(BASE / ("control-" + name + ".xml")))
            + "]))\n"
        )
        results[name] = command(["-c", code], "control-" + name + ".json")
    assert results["reference"] == 0
    assert all(results[n] == 1 for n in variants if n != "reference")
    assert sha(ROOT / SOURCE) == before
    save(
        BASE / "test-control-decision.json",
        {
            "reference_passed": True,
            "wrong_algorithms_rejected": list(variants)[1:],
            "source_unchanged": True,
            "not_worker_successes": True,
            "results": results,
        },
    )


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
    result = api().CONTRACT.materialize_bounded_packet(
        plan,
        {
            "unit_id": "unit-1",
            "run_id": FEATURE + "-unit-1-a1",
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
    save(ROOT / ".agent/unit-1-packet.json", result)


def accept(note):
    frozen()
    step = ROOT / ".agent/limited" / FEATURE / "unit-1"
    coder, reviewer = read(step / "coder.json"), read(step / "reviewer.json")
    assert (
        coder["status"] == "ready_for_review"
        and reviewer["decision"] == "pass_to_primary"
    )
    api().load("real_trace_current_handoff", "local-unit.py").verify_handoff(
        ROOT, coder
    )
    packet_ = read(step / "packet.json")
    assert (
        command(
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
            "unit-1-primary-accept.json",
        )
        == 0
    )
    refs = {"unit-1": {"task_id": packet_["task_id"], "run_id": packet_["run_id"]}}
    save(ROOT / ".agent/accepted-refs-final.json", refs)
    api().accepted_state(
        ROOT,
        read(ROOT / ".agent/approval.json")["approved_plan"],
        read(ROOT / ".agent/brief.json")["source_hashes"],
        refs,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "setup",
            "baseline",
            "controls",
            "expected-red",
            "propose",
            "approve",
            "packet",
            "dispatch",
            "accept",
            "integration",
        ],
    )
    parser.add_argument("--note")
    args = parser.parse_args()
    if args.action == "setup":
        setup()
    elif args.action == "baseline":
        sys.exit(checks("baseline", legacy=True))
    elif args.action == "controls":
        controls()
    elif args.action == "expected-red":
        frozen()
        sys.exit(
            command(
                [
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "tests/test_get_many.py",
                    "--junitxml",
                    BASE / "expected-red.xml",
                ],
                "expected-red.json",
            )
        )
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
    elif args.action == "packet":
        packet()
    elif args.action == "dispatch":
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
    elif args.action == "accept":
        accept(args.note)
    else:
        sys.exit(checks("integration"))
