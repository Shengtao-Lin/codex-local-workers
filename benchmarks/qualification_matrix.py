"""Frozen six-case E/C/R qualification. Never automatically accepts a run."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import dependent_retention_chain as CHAIN
import qualification_matrix_cases as CASES
import supervised_scope_check as SCOPE
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-matrix-2"
SNAPSHOT = WORK / "qualification-matrix-baseline-2"
MIXED = SCOPE.FA.MIXED


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    data, oracles = CASES.corpus(
        read(KIT / "benchmarks/fixtures/mixed-features-v1.json")["cases"][0]
    )
    write(BASE / "corpus.json", data)
    write(BASE / "primary-oracles.json", oracles)
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    CHAIN.SNAPSHOT = SNAPSHOT
    worker, contract = load_worker(SNAPSHOT), CHAIN.load_contract()
    cells = []
    for repetition in (1, 2):
        for case in data["cases"]:
            root = Path(
                MIXED.prepare(
                    case["case_id"],
                    repetition,
                    SNAPSHOT / ".local-agents/config.json",
                    "qualification",
                )["root"]
            )
            plan = read(root / ".agent/feature-plan.json")
            for unit in case["units"]:
                packet = read(root / f".agent/{unit['unit_id']}-reference.json")
                packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
                packet = contract.validate_unit_packet(plan, packet)
                worker.validate_packet(packet)
                write(root / f".agent/{unit['unit_id']}-bound.json", packet)
            cells.append(
                {
                    "id": f"{case['case_id']}-r{repetition}",
                    "case": case["case_id"],
                    "round": repetition,
                    "root": str(root),
                    "units": [u["unit_id"] for u in case["units"]],
                    "explorer_required": case["case_id"]
                    in ("label-rollup", "async-receipt"),
                    "hashes": {
                        p.relative_to(root).as_posix(): digest(p)
                        for p in root.rglob("*")
                        if p.is_file()
                        and (
                            p.suffix == ".py"
                            or p.name
                            in ("pyproject.toml", "config.json", "feature-plan.json")
                            or p.name.endswith("-bound.json")
                        )
                    },
                }
            )
    write(
        BASE / "manifest.json",
        {
            "feature_id": "supervised-formal-qualification",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Evidence provenance and qualification authority; functional units medium.",
            "owned_contract_ids": [
                "immutable-evidence",
                "independent-role-evidence",
                "qualification-before-coordinator",
            ],
            "runtime": str(SNAPSHOT),
            "cells": cells,
            "drivers": {
                str(p): digest(p)
                for p in (
                    Path(__file__).resolve(),
                    Path(CASES.__file__),
                    Path(SCOPE.__file__),
                    Path(CHAIN.__file__),
                )
            },
            "weekly_used_ceiling": 70,
            "criterion": "All six cases in two fresh rounds, actual Coder validation plus independent Reviewer plus Primary acceptance, both Explorer-dependent chains and final integration; two Reviewer defect families hidden/clean twice. Old failed cohorts unchanged. No Coordinator invocation until gate is met.",
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    print("Prepared twelve independent cases / fourteen real Coder units", flush=True)


def verify():
    manifest = read(BASE / "manifest.json")
    SCOPE.FA.LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    for path, sha in manifest["drivers"].items():
        if digest(Path(path)) != sha:
            raise ValueError("driver drift")
    return manifest


def preflight():
    """References and two mutants execute outside worker-readable roots."""
    verify()
    data = read(BASE / "corpus.json")
    oracles = read(BASE / "primary-oracles.json")
    observations = []
    for case in data["cases"]:
        for label, changes in [
            ("reference", oracles[case["case_id"]]["reference"]),
            *[
                (f"mutant-{n}", m)
                for n, m in enumerate(oracles[case["case_id"]]["mutants"])
            ],
        ]:
            root = BASE / "oracle-checks" / case["case_id"] / label
            root.mkdir(parents=True, exist_ok=False)
            for path, text in {**case["files"], **changes}.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            (root / "pyproject.toml").write_text(
                '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff]\nline-length=100\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
                encoding="utf-8",
            )
            subprocess.run(
                [sys.executable, "-m", "ruff", "format", "src", "tests"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            checks = SCOPE.FA.LAYER.check(root, label)
            okay = (
                checks["all_checks_pass"]
                if label == "reference"
                else not checks["semantic_pass"]
                and checks["tests_executed"] > 0
                and checks["static_pass"]
            )
            observations.append(
                {
                    "case": case["case_id"],
                    "variant": label,
                    "okay": okay,
                    "checks": checks,
                }
            )
    result = {
        "observations": observations,
        "all_pass": all(o["okay"] for o in observations),
    }
    write(BASE / "preflight-1.json", result)
    print(json.dumps({"all_pass": result["all_pass"], "variants": len(observations)}))
    if not result["all_pass"]:
        raise ValueError("fixture preflight failed")


def explore(identity):
    manifest = verify()
    cell = next(c for c in manifest["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    SCOPE.FA.LAYER.verify_hashes(root, cell["hashes"])
    if not cell["explorer_required"]:
        raise ValueError("not a required Explorer case")
    question = (
        "Trace summarize_labels in src/product to its normalization helper, and identify the protected test requiring count of normalized rather than input labels. Read caller, helper and test; provide real path/line evidence for this one question."
        if cell["case"] == "label-rollup"
        else "Trace the public run_receipt entry in src/product to the async receipt and collector helpers. Locate the protected integration test retaining None, False, zero and empty string, and identify the collector-order test. Investigate this call chain only, with real file/line evidence."
    )
    packet = read(root / f".agent/{cell['units'][0]}-bound.json")
    SCOPE.invoke(
        root,
        "explorer",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--task",
            question,
            "--task-id",
            packet["task_id"],
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
        ],
    )
    print(json.dumps(read(root / ".agent/explorer.json")), flush=True)


def run(identity, unit):
    manifest = verify()
    if not read(BASE / "preflight-1.json")["all_pass"]:
        raise ValueError("preflight missing")
    cell = next(c for c in manifest["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    if unit not in cell["units"]:
        raise ValueError("unknown unit")
    packet = read(root / f".agent/{unit}-bound.json")
    CHAIN.SNAPSHOT = SNAPSHOT
    contract = CHAIN.load_contract()
    plan = read(root / ".agent/feature-plan.json")
    contract.validate_unit_packet(plan, packet)
    refs = {}
    dependency_paths = set()
    for dependency in packet["dependencies"]:
        dep = read(root / f".agent/{dependency}-bound.json")
        refs[dependency] = {k: dep[k] for k in ("task_id", "run_id")}
        archive = root / ".agent/tasks" / dep["task_id"] / "runs" / dep["run_id"]
        for change in read(archive / "handoff.json")["changed_files"]:
            if digest(root / change["path"]) != change["final_sha256"]:
                raise ValueError("accepted dependency changed")
            dependency_paths.add(change["path"])
    accepted = contract.accepted_units_from_archives(plan, root, refs)
    if not set(packet["dependencies"]) <= accepted:
        raise ValueError("dependency lacks Primary acceptance")
    SCOPE.FA.LAYER.verify_hashes(
        root, {p: sha for p, sha in cell["hashes"].items() if p not in dependency_paths}
    )
    SCOPE.invoke(
        root,
        unit + "-unit",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / f".agent/{unit}-bound.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / f".agent/{unit}-coder.json"),
            "--review-report",
            str(root / f".agent/{unit}-reviewer.json"),
        ],
    )
    # For producer units only the focused suite is valid before consumer implementation.
    if packet["dependencies"] or len(cell["units"]) == 1:
        checks = SCOPE.FA.LAYER.check(root, unit + "-primary")
        write(root / f".agent/{unit}-primary-checks.json", checks)
    print(json.dumps(read(root / f".agent/{unit}-coder.json")), flush=True)
    reviewer = root / f".agent/{unit}-reviewer.json"
    if reviewer.exists():
        print(json.dumps(read(reviewer)), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "preflight", "explore", "unit"))
    parser.add_argument("identity", nargs="?")
    parser.add_argument("unit", nargs="?", default="qual-unit")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "preflight":
        preflight()
    elif args.action == "explore":
        explore(args.identity)
    else:
        run(args.identity, args.unit)
