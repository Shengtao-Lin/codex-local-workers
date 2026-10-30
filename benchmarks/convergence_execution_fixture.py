"""New D2 identity after deterministic protected-fixture lint preparation failed."""

import argparse
import ast
import copy
import subprocess
from pathlib import Path

import convergence_execution as core
from convergence_coder import KIT, PYTHON, save
from system_convergence import read_object, ref, sha256

OLD = core.BASE
BASE = KIT / "benchmarks/work/system-convergence/execution-20261011-2"
TARGET = BASE / "candidate-kit"
ORIGINAL_FIXTURES = core.fixtures


def bind():
    core.BASE, core.TARGET, core.RUNTIME = BASE, TARGET, TARGET / ".local-agents"


def normalized_fixtures():
    result = copy.deepcopy(ORIGINAL_FIXTURES())
    proof = []
    for case in result:
        root = BASE / "fixture-preparation" / case["id"]
        for path, text in case["files"].items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        (root / "pyproject.toml").write_text(
            (
                KIT / "benchmarks/fixtures/convergence-decomposition/pyproject.toml"
            ).read_text(),
            encoding="utf-8",
        )
        original = {p: v for p, v in case["files"].items() if p.startswith("tests/")}
        subprocess.run(
            [
                str(PYTHON),
                "-B",
                "-m",
                "ruff",
                "check",
                "--select",
                "I",
                "--fix",
                "tests",
            ],
            cwd=root,
            env=core.ENV,
            check=True,
            capture_output=True,
        )
        for path, text in original.items():
            normalized = (root / path).read_text()
            before, after = ast.parse(text), ast.parse(normalized)

            def split(tree):
                imports, behavior = [], []
                for node in tree.body:
                    value = ast.dump(node, include_attributes=False)
                    (
                        imports
                        if isinstance(node, (ast.Import, ast.ImportFrom))
                        else behavior
                    ).append(value)
                return sorted(imports), behavior

            assert split(before) == split(after), (
                "Import sort changed behavior or bindings"
            )
            case["files"][path] = normalized
            proof.append(
                {
                    "case": case["id"],
                    "path": path,
                    "imports_same_bindings": True,
                    "non_import_ast_unchanged": True,
                    "assertions_unchanged": True,
                    "original_frozen_identity": ref(
                        OLD / "features" / case["id"] / "B", path
                    ),
                }
            )
    save(BASE / "fixture-format-proof.json", proof)
    return result


def prepare():
    bind()
    core.fixtures = normalized_fixtures
    core.prepare()
    # No model or runtime change; frozen old driver remains separately executable.
    assert all(
        sha256(TARGET / ".local-agents" / p["path"]) == p["sha256"]
        for p in read_object(OLD / "registration.json")["runtime"]
    )


def register():
    bind()
    previous = read_object(OLD / "registration.json")
    assert read_object(BASE / "preflight.json")["all_reference_pass_and_mutants_fail"]
    for feature in read_object(BASE / "preparation.json")["features"]:
        for cell in feature["arms"]:
            root = Path(cell["root"])
            for argv in (
                ["-m", "ruff", "check", "src", "tests"],
                ["-m", "ruff", "format", "--check", "src", "tests"],
            ):
                name = (
                    "initial-ruff-lint.json"
                    if argv[2] == "check"
                    else "initial-ruff-format.json"
                )
                assert core.command(root, argv, root / ".agent" / name) == 0
    save(
        BASE / "registration.json",
        {
            **previous,
            "driver": ref(KIT, "benchmarks/convergence_execution.py"),
            "wrapper": ref(KIT, "benchmarks/convergence_execution_fixture.py"),
            "preparation": ref(BASE, "preparation.json"),
            "runtime": [
                ref(TARGET / ".local-agents", p["path"]) for p in previous["runtime"]
            ],
            "combined_full_regression": ref(OLD, "full-regression-2.xml"),
            "combined_runtime_exact_same_hashes_no_new_regression_claim": True,
            "initial_test_environment_failure_retained": ref(
                OLD, "full-regression-1.xml"
            ),
            "prior_invalid_fixture_registration": ref(OLD, "registration.json"),
            "prior_stage": ref(OLD, "stage-decision-1.json"),
            "same_three_features_no_replacement": True,
            "only_protected_test_import_order_fixed_before_new_live": ref(
                BASE, "fixture-format-proof.json"
            ),
            "new_runtime_candidate": False,
            "weekly_used_start": 3,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("prepare", "preflight", "register", "probe", "approve", "run"),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("unit", nargs="?")
    parser.add_argument("--note")
    args = parser.parse_args()
    bind()
    if (BASE / "registration.json").exists():
        assert (
            sha256(Path(__file__))
            == read_object(BASE / "registration.json")["wrapper"]["sha256"]
        )
    if args.action == "prepare":
        prepare()
    elif args.action == "preflight":
        core.preflight()
    elif args.action == "register":
        register()
    elif args.action == "probe":
        core.probe(args.identity)
    elif args.action == "approve":
        core.approve(args.identity, args.note)
    else:
        core.run(args.identity, args.unit)
