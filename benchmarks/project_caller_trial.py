"""Fixed installed integration batch; no production defaults or sibling writes."""

import argparse
import ast
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

import prepared_task_matrix as M
import project_caller_tasks as TASKS

S, T, P = M.S, M.T, M.P
BATCH = P.I.BASE / "project-callers-20261022-2"
ORDER = ["message-1", "hash-1", "hash-2", "message-2"]
ORIGINAL_RUN, ORIGINAL_COMMAND = T.run, P.command
EXCLUDED = ("__pycache__", ".pytest_cache", ".ruff_cache", "pytest-owned")


def run_check(argv, root, timeout=120):
    args = [str(a) for a in argv]
    if "pytest" in args:
        # Fresh owned scratch per independent command, never a historical artifact.
        scratch = Path("C:/Users/Lin/.codex/local-workers") / (
            "caller-check-" + uuid.uuid4().hex
        )
        assert not scratch.exists()
        args.extend(["-m", "not integration", "--basetemp=" + str(scratch)])
    if (
        "ruff" in args
        and ("--check" in args or "check" in args)
        and args[-2:] == ["src", "tests"]
    ):
        args.extend(["examples", "scripts"])
    return ORIGINAL_RUN(args, root, timeout=timeout)


def command(root, mode="unit", replay=None):
    args = ORIGINAL_COMMAND(root, mode=mode, replay=replay)
    if mode == "unit":
        args.append("--compact-output")
    return args


def function_source(path, symbol):
    source = path.read_text(encoding="utf-8")
    node = next(
        n
        for n in ast.parse(source).body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == symbol
    )
    return "\n".join(source.splitlines()[node.lineno - 1 : node.end_lineno]) + "\n"


def copy_project(origin, destination):
    shutil.copytree(
        origin, destination, ignore=shutil.ignore_patterns(*EXCLUDED, "*.pyc")
    )


def prepare(used):
    assert not BATCH.exists(), "create-only batch"
    started = time.monotonic()
    specs = TASKS.tasks()
    snapshot = TASKS.SNAPSHOT
    snapshot_hashes = {
        p.relative_to(snapshot).as_posix(): S.sha(p)
        for p in snapshot.rglob("*")
        if p.is_file() and not set(p.parts) & set(EXCLUDED)
    }
    S.save(
        BATCH / "preparation.json",
        {
            "feature_id": "full-project-caller-compatibility",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "snapshot": str(snapshot),
            "origin": S.read(snapshot.parent / "registration.json"),
            "snapshot_hashes": snapshot_hashes,
            "authorization": "Current autonomous isolated experiments, no weekly cap, no production/sibling changes",
            "exposure": "Two exposed local-function contracts in a frozen complete project; hash wording explicitly clarifies items() references after prior Reviewer ambiguity. Not an old-contract rerun or novel semantic holdout.",
            "gate": "4/4 independent acceptance, current fresh Reviewer, protected drift zero; full project unit/static checks and real callers. No PostgreSQL/concurrency/migration qualification.",
            "Primary": "Reviewed contracts, prepared public/private integration cases and reference; no algorithm/repair hint during live. Precise active time/cloud tokens unknown.",
        },
    )
    materials = {}
    for topic, spec in specs.items():
        root = BATCH / "templates" / topic
        copy_project(snapshot, root)
        test = "tests/unit/test_local_worker_" + topic + ".py"
        T.write(root / test, spec["public"])
        private = BATCH / "private" / topic / "test_independent.py"
        T.write(private, spec["private"])
        for sub in (("check", "--select", "I", "--fix"), ("format",)):
            assert (
                T.run([S.PYTHON, "-B", "-m", "ruff", *sub, test], root)["exit_code"]
                == 0
            )
        reference = BATCH / "references" / topic
        copy_project(root, reference)
        target = reference / spec["target"]
        source = target.read_text(encoding="utf-8")
        old = function_source(target, spec["symbol"])
        assert source.count(old) == 1
        # Reference construction only, isolated from every Worker workspace.
        target.write_text(source.replace(old, spec["reference"], 1), encoding="utf-8")
        assert (
            T.run([S.PYTHON, "-B", "-m", "ruff", "format", spec["target"]], reference)[
                "exit_code"
            ]
            == 0
        )
        control = {
            "baseline": M.L.checks(root, private),
            "reference": M.L.checks(reference, private),
        }
        S.save(BATCH / "task-controls" / (topic + ".json"), control)
        assert control["baseline"][0]["exit_code"] == 1, control
        assert all(c["exit_code"] == 0 for c in control["baseline"][1:]), control
        assert all(c["exit_code"] == 0 for c in control["reference"]), control
        materials[topic] = root, private, reference, test
    rows = {}
    for cell in ORDER:
        topic = cell.split("-")[0]
        spec = specs[topic]
        template, private, reference, test = materials[topic]
        root = BATCH / "cells" / cell / "isolated"
        copy_project(template, root)
        with tempfile.TemporaryDirectory(prefix="caller-installed-") as directory:
            stage = Path(directory)
            M.INSTALL.install(S.KIT, stage, apply=True)
            shutil.copytree(stage / ".local-agents", root / ".local-agents")
            shutil.copyfile(stage / "AGENTS.md", root / "AGENTS.md")
        identity = {
            k: BATCH.name + "-" + cell for k in ("task_id", "unit_id", "run_id")
        }
        packet = S.read(P.SEED / ".agent/packet.json")
        packet.update(
            identity,
            feature_id="project-caller-" + topic,
            goal=spec["contract"],
            primary_plan_sha256=S.sha(__file__),
        )
        packet["risk"]["reasons"] = [
            "Identity/idempotency public compatibility, one function owns the invariant; full Primary review and actual caller integration required."
        ]
        packet["scope"] = {
            "read": ["src", "tests", "pyproject.toml", "acceptance"],
            "readonly": [
                "tests",
                "pyproject.toml",
                "acceptance",
                *[
                    p.relative_to(root).as_posix()
                    for p in (root / "src").rglob("*.py")
                    if p != root / spec["target"]
                ],
            ],
            "modify": [spec["target"]],
            "create": [],
            "forbidden": [".agent", ".git", ".local-agents", "AGENTS.md"],
        }
        packet["focused_tests"] = [test]
        packet["owned_contract_ids"] = [topic]
        packet["required_behavior"] = [
            {
                "id": topic,
                "text": spec["contract"],
                "risk_floor": "high",
                "implementation_ref": {
                    "path": spec["target"],
                    "symbol": spec["symbol"],
                },
            }
        ]
        packet["edit_targets"] = [
            {"path": spec["target"], "anchor": "def " + spec["symbol"] + "("}
        ]
        packet["acceptance_criteria"] = [
            {
                "id": topic,
                "text": "Exact supplied identity/hash semantics, input preservation, caller round-trip and unchanged complete package checks",
            }
        ]
        packet["acceptance_scenarios"] = [
            {"id": k, "text": v}
            for k, v in (
                ("normal", "Requested new identity behavior reaches the real caller"),
                (
                    "boundary",
                    "Legacy falsey/nested/Unicode values retain exact semantics",
                ),
                (
                    "error",
                    "Existing rejection/conflict rules and input preservation remain intact",
                ),
            )
        ]
        packet["review_feedback"] = []
        config = S.read(P.SEED / ".agent/config.json")
        dependencies = (
            function_source(
                root / "src/evaluation_harness/canonical/fingerprint.py",
                "canonical_json",
            )
            if topic == "hash"
            else function_source(root / spec["target"], "parse_message")
        )
        config["coder_single_function"] = {
            "path": spec["target"],
            "symbol": spec["symbol"],
            "dependencies": "Protected actual dependency/caller source (not implementation guidance):\n"
            + dependencies,
        }
        for check in config["validation_profiles"][packet["validation_profile"]][
            "commands"
        ]:
            if check["id"] in {"ruff-format", "ruff-check"}:
                check["argv"].extend(["examples", "scripts"])
        sources = [p.relative_to(root).as_posix() for p in (root / "src").rglob("*.py")]
        sources += ["pyproject.toml", "tests/__init__.py", "tests/conftest.py", test]
        capture = {
            "schema_version": 1,
            "target": {
                "path": spec["target"],
                "module": spec["module"],
                "symbol": spec["symbol"],
            },
            "source_paths": sources,
            "family": "json-call-model-dump-v1",
            "cases": spec["cases"],
        }
        for name, value in (
            ("packet", packet),
            ("config", config),
            ("capture-spec", capture),
        ):
            S.save(root / (".agent/" + name + ".json"), value)
        argv = [
            S.PYTHON,
            "-B",
            root / ".local-agents/local-bounded-prepare.py",
            "--packet",
            ".agent/packet.json",
            "--config",
            ".agent/config.json",
            "--capture-spec",
            ".agent/capture-spec.json",
            "--apply",
        ]
        result = T.run(argv, root)
        S.save(BATCH / "preflight" / (cell + "-prepare.json"), result)
        assert result["exit_code"] == 0, result
        preflight = command(root, mode="preflight")
        preflight[preflight.index("--report") + 1] = str(root / ".agent/preflight.json")
        result = T.run(preflight, root)
        S.save(BATCH / "preflight" / (cell + ".json"), result)
        assert result["exit_code"] == 0, result
        if cell in ORDER[:2]:
            proof = BATCH / "replay" / topic / "isolated"
            copy_project(root, proof)
            replay = proof.parent / "reference.json"
            S.save(
                replay,
                [
                    {
                        "kind": "replacement",
                        "content": function_source(
                            reference / spec["target"], spec["symbol"]
                        ),
                    }
                ],
            )
            result = T.run(command(proof, replay=replay), proof, timeout=240)
            S.save(proof.parent / "process.json", result)
            assert result["exit_code"] == 0, result
        rows[cell] = {
            "root": str(root),
            "identity": identity,
            "topic": topic,
            "arm": "installed-project",
            "target": spec["target"],
            "private_tests": str(private),
            "start_sha256": S.sha(root / spec["target"]),
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file() and not set(p.parts) & set(EXCLUDED)
            },
        }
    assert all(S.sha(snapshot / p) == sha for p, sha in snapshot_hashes.items())
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 4,
            "weekly_used_start": used,
            "weekly_cap": None,
            "candidate": "Current installed bounded-v1/flat-v1 and same contract-first direct Reviewer, explicit compact output; no recovery codec/extra role/default change",
            "model": "Qwen qwen/qwen3-coder-30b; Muse meta/muse-glimmer; 24576 context, existing sampling/quantization, serial one resident",
            "roles_not_run": "Explorer target already located; Coordinator one cohesive invariant per independent unit, not a dependency chain",
            "budget": "C12requests/3edits/1initial+3postchecks/900s/4096 output; R16requests/4errors/600s/4096; cell2220s batch5400s",
            "exposure": "2 known behavior tasks, 2 repeats each in full frozen upstream package. Hash contract clarification and new caller checks registered before live; old ambiguity/HOLD retained unchanged.",
            "gate": "4/4 current fresh Reviewer and Primary independently accepted with full project tests/statics, no drift, assistance or takeover; not general qualification",
            "continue_rule": "Ordinary failure HOLD but complete fixed order. Infrastructure/safety/protected drift/deadline/user stop halts. No reroll/replacement or changed contract inside batch.",
            "not_tested": [
                "persisted hash upgrade migration",
                "PostgreSQL concurrency",
                "external MLflow",
                "unknown tasks",
                "broad Coordinator decomposition",
                "cost savings",
            ],
            "preparation_seconds": time.monotonic() - started,
            "pins": M.pins(
                BATCH,
                Path(__file__),
                Path(TASKS.__file__),
                *[m[1] for m in materials.values()],
                *list((BATCH / "task-controls").glob("*.json")),
            ),
        },
    )
    print("4 full-project caller cells frozen; zero live", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    T.run = run_check
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        P.BATCH, P.ORDER, P.command = BATCH, ORDER, command
        row = S.read(BATCH / "cells.json")[args.cell]
        P.TARGET = row["target"]
        P.run(args.cell, args.weekly_used)
