"""One frozen Reviewer-only candidate; immutable screens and conditional rechecks."""

import argparse
import copy
import subprocess
import sys
from pathlib import Path

import qualification_controls as controls
import qualification_matrix as matrix
import supervised_scope_check as scope
from capability_fit import KIT, WORK, freeze, write
from inherited_context_recovery import digest, read

BASE = WORK / "reviewer-evidence-1"
SNAPSHOT = WORK / "reviewer-evidence-candidate-1"
OLD = WORK / "fixed-release-1/matrix"
PLAN = KIT / "docs/reviewer-evidence-candidate-plan.md"


def configure():
    matrix.BASE, matrix.SNAPSHOT = BASE, SNAPSHOT
    controls.BASE = BASE / "controls"
    scope.BASE, scope.SNAPSHOT = BASE, SNAPSHOT


def verify():
    configure()
    matrix.verify()
    registration = read(BASE / "registration.json")
    if digest(PLAN) != registration["plan_sha256"]:
        raise ValueError("plan drift")
    return registration


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    configure()
    write(BASE / "corpus.json", read(OLD / "corpus.json"))
    write(BASE / "primary-oracles.json", read(OLD / "primary-oracles.json"))
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "cells": [],
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (__file__, controls.__file__, matrix.__file__, scope.__file__)
            },
        },
    )
    original = matrix.MIXED.prepare

    def cli_prepare(case, repetition, config_path, batch, suite="v1"):
        config = read(config_path)
        config.update(
            model_load_backend="cli",
            model_load_cli_path="C:/Users/Lin/.lmstudio/bin/lms.exe",
        )
        path = BASE / "configs" / f"{case}-{batch}-{repetition}.json"
        write(path, config)
        return original(case, repetition, path, batch, suite)

    matrix.MIXED.prepare = cli_prepare
    controls.prepare()
    cells = read(controls.BASE / "manifest.json")["controls"]
    for cell in cells:
        cell["expected_decision"] = (
            "rework" if cell["has_defect_primary_only"] else "pass_to_primary"
        )
        cell["expected_category"] = (
            "contract_violation" if cell["has_defect_primary_only"] else None
        )
        cell["screen"] = "old"
    template = read(BASE / "corpus.json")["cases"][0]
    contract = "increment(x) returns x + 1 for every integer x, including negatives."
    specs = [
        ("optional-coverage", contract, "return x + 1", "pass_to_primary", None),
        (
            "required-coverage",
            contract
            + " This unit must also include a focused test asserting increment(-2) == -1; "
            "passing positive-only tests does not satisfy that explicit test obligation.",
            "return x + 1",
            "rework",
            "test_gap",
        ),
        (
            "conflicting-contract",
            contract
            + " For negative integers the same result is additionally required to equal x - 1.",
            "return x + 1",
            "escalate",
            None,
        ),
        (
            "negative-defect",
            contract,
            "return abs(x) + 1",
            "rework",
            "contract_violation",
        ),
    ]
    for identity, requirement, implementation, decision, category in specs:
        case = copy.deepcopy(template)
        case.update(case_id=identity, goal=requirement)
        case["files"] = {
            "src/product/__init__.py": "",
            "src/product/target.py": "def increment(x):\n    return 0\n",
            "tests/test_target.py": "from product.target import increment\n\ndef test_positive():\n    assert increment(2) == 3\n",
        }
        unit = case["units"][0]
        unit.update(
            contract=requirement,
            behavior=requirement,
            anchor="increment",
            anchors={"src/product/target.py": "increment"},
            acceptance_scenarios=[
                {
                    "id": "positive",
                    "text": "increment(2) == 3",
                    "observables": {"input": 2, "return_value": 3},
                },
                {
                    "id": "negative",
                    "text": "Negative integer behavior follows the owned requirement.",
                    "observables": {"input": -2},
                },
            ],
        )
        path = BASE / f"corpus-{identity}.json"
        write(path, {"cases": [case]})
        matrix.MIXED.CORPUS, matrix.MIXED.WORK = path, BASE / "extra-runs"
        for repetition in (1, 2):
            root = Path(
                matrix.MIXED.prepare(
                    identity,
                    repetition,
                    SNAPSHOT / ".local-agents/config.json",
                    "evidence",
                )["root"]
            )
            cells.append(
                {
                    "id": f"{identity}-r{repetition}",
                    "root": str(root),
                    "source": "def increment(x):\n    " + implementation + "\n",
                    "has_defect_primary_only": identity == "negative-defect",
                    "expected_defect": requirement if decision == "rework" else None,
                    "expected_decision": decision,
                    "expected_category": category,
                    "screen": "new",
                }
            )
    for cell in cells:
        root = Path(cell["root"])
        cell["protected_hashes"] = {
            p.relative_to(root).as_posix(): digest(p)
            for p in root.rglob("*")
            if p.is_file()
            and (
                p.suffix == ".py"
                or p.name
                in ("config.json", "pyproject.toml", "qual-unit-reference.json")
            )
        }
    write(
        BASE / "registration.json",
        {
            "plan_sha256": digest(PLAN),
            "weekly_used_start": 45,
            "weekly_used_ceiling": 50,
            "controls": cells,
            "criterion": "16/16 substantively correct, then 8/8 fresh real-unit reviews; Primary adjudication required",
            "one_candidate_only": True,
            "synthetic_coder_credit": False,
        },
    )
    print(
        "Registered 8 old + 8 new Reviewer controls, before model execution", flush=True
    )


def run(identity):
    registration = verify()
    cell = next(c for c in registration["controls"] if c["id"] == identity)
    root = Path(cell["root"])
    if (root / ".agent/reviewer.json").exists():
        raise FileExistsError("no replay")
    for p, sha in cell["protected_hashes"].items():
        if digest(root / p) != sha:
            raise ValueError("fixture drift: " + p)
    scope.verify = lambda: registration
    scope.control(identity)
    for p, sha in cell["protected_hashes"].items():
        if p != "src/product/target.py" and digest(root / p) != sha:
            raise ValueError("protected drift: " + p)


def recheck(identity, unit):
    verify()
    # Conditional stage requires an explicit Primary screen decision.
    if read(BASE / "primary-screen-decision.json")["decision"] != "pass":
        raise ValueError("screen not passed")
    cell = next(c for c in read(OLD / "manifest.json")["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    packet = read(root / f".agent/{unit}-bound.json")
    request = BASE / "real-rechecks" / f"{identity}-{unit}-request.json"
    report = BASE / "real-rechecks" / f"{identity}-{unit}-report.json"
    write(
        request,
        {
            "schema_version": 1,
            **{k: packet[k] for k in ("task_id", "unit_id", "run_id")},
            "review_id": "evidence-candidate-1",
        },
    )
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SNAPSHOT / ".local-agents/local-review.py"),
            "--request",
            str(request),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(report),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=1500,
        check=False,
    )
    write(
        BASE / "real-rechecks" / f"{identity}-{unit}-invocation.json",
        {"exit": process.returncode, "output": process.stdout + process.stderr},
    )
    print(read(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "run", "recheck"))
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="qual-unit")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "run":
        run(args.identity)
    else:
        recheck(args.identity, args.unit)
