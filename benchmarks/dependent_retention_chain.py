"""Primary-supervised dependent units; no Coordinator or automatic acceptance."""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import WORK, load_worker, write

BASE = WORK / "roleq-dependent-retention-2"
SNAPSHOT = WORK / "roleq-budget-next-baseline-1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract():
    spec = importlib.util.spec_from_file_location(
        "chain_contract", SNAPSHOT / ".local-agents/coordinator-contract.py"
    )
    contract = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = contract
    spec.loader.exec_module(contract)
    return contract


def prepare(*, config_path=None, batch="chain1"):
    BASE.mkdir(exist_ok=False)
    corpus = read(MIXED.CORPUS)
    case = next(c for c in corpus["cases"] if c["case_id"] == "bounded-report")
    # New protected cross-unit forms, not a change to any historical fixture.
    case["files"]["tests/test_config.py"] += """

@pytest.mark.parametrize("value", ["１２", "²", "١٢", [], {}])
def test_non_ascii_and_containers(value):
    with pytest.raises(ValueError):
        parse_limit(value)
"""
    case["files"]["tests/test_report.py"] += """

@pytest.mark.parametrize("value", ["１２", " 2", "+2", None, False])
def test_exact_form_rejection(value):
    with pytest.raises(ValueError):
        build_report([], value)


def test_leading_zero_roundtrip_and_stable_ties():
    rows = [{"id": "b", "tag": 0}, {"id": "a", "tag": 1}, {"id": "a", "tag": 2}]
    assert build_report(rows, "002") == rows[1:]
    assert rows[0]["id"] == "b"
"""
    write(BASE / "corpus.json", {"cases": [case]})
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    worker = load_worker(SNAPSHOT)
    contract = load_contract()
    cells = []
    for repetition in (1, 2):
        root = Path(
            MIXED.prepare(
                "bounded-report",
                repetition,
                config_path or SNAPSHOT / ".local-agents/config.json",
                batch,
            )["root"]
        )
        for unit in case["units"]:
            packet = read(root / f".agent/{unit['unit_id']}-reference.json")
            plan = read(root / ".agent/feature-plan.json")
            packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
            packet = contract.validate_unit_packet(plan, packet)
            worker.validate_packet(packet)
            write(root / f".agent/{unit['unit_id']}-bound.json", packet)
        cells.append(
            {
                "round": repetition,
                "root": str(root),
                "hashes": {
                    p.relative_to(root).as_posix(): digest(p)
                    for p in root.rglob("*")
                    if p.is_file()
                    and (
                        p.suffix == ".py"
                        or p.name.endswith("-reference.json")
                        or p.name.endswith("-bound.json")
                        or p.name
                        in ("config.json", "feature-plan.json", "pyproject.toml")
                    )
                },
            }
        )
    write(
        BASE / "manifest.json",
        {
            "classification": "Known development fixture, fresh dependent-chain replication; not unseen qualification",
            "feature_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Qualification evidence integrity; functional units remain medium",
            "contracts": [
                "protected-inputs",
                "accepted-dependency-before-consumer",
                "independent-role-evidence",
            ],
            "cells": cells,
            "runtime": str(SNAPSHOT),
            "driver_sha256": digest(Path(__file__)),
            "criterion": "Two fresh chains: each unit validated, independently reviewed and Primary accepted; final full integration passes",
            "stop": "First failed unit stops this cohort, including second round. No unchanged retries.",
            "max_calls": "4 Coder plus automatic Reviewer on successes",
            "explorer": "Not called: paths and question already known; no Explorer success credit",
            "coordinator_started": False,
            "weekly_used_ceiling": 40,
        },
    )
    print(BASE)


def run(repetition, unit):
    manifest = read(BASE / "manifest.json")
    if digest(Path(__file__)) != manifest["driver_sha256"]:
        raise ValueError("driver changed")
    for relative, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        if digest(SNAPSHOT / relative) != sha:
            raise ValueError("runtime changed")
    for cell in manifest["cells"]:
        for result in Path(cell["root"]).glob(".agent/*-result.json"):
            if read(result)["exit"] != 0:
                raise ValueError("cohort stopped by prior failure")
    cell = next(c for c in manifest["cells"] if c["round"] == repetition)
    root = Path(cell["root"])
    packet = read(root / f".agent/{unit}-bound.json")
    contract = load_contract()
    contract.validate_unit_packet(read(root / ".agent/feature-plan.json"), packet)
    refs = {}
    for dependency in packet["dependencies"]:
        parent = read(root / f".agent/{dependency}-bound.json")
        refs[dependency] = {"task_id": parent["task_id"], "run_id": parent["run_id"]}
    accepted = contract.accepted_units_from_archives(
        read(root / ".agent/feature-plan.json"), root, refs
    )
    if not set(packet["dependencies"]) <= accepted:
        raise ValueError("dependency lacks verified Primary acceptance")
    # Accepted dependency files are verified by the archive gate; all other
    # sources, protected tests and authority files must match preparation.
    dependency_paths = set()
    for dependency in accepted:
        parent = read(root / f".agent/{dependency}-bound.json")
        archive = root / ".agent/tasks" / parent["task_id"] / "runs" / parent["run_id"]
        for changed in read(archive / "handoff.json")["changed_files"]:
            if digest(root / changed["path"]) != changed["final_sha256"]:
                raise ValueError("accepted dependency source drift")
        dependency_paths.update(
            read(root / f".agent/{dependency}-reference.json")["scope"]["modify"]
        )
    for relative, sha in cell["hashes"].items():
        if relative not in dependency_paths and digest(root / relative) != sha:
            raise ValueError("frozen input changed: " + relative)
    marker = root / f".agent/{unit}-started.json"
    write(
        marker, {"accepted_dependencies": sorted(accepted), "started_at": time.time()}
    )
    started = time.monotonic()
    result = subprocess.run(
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
        cwd=root,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    summary = {
        "exit": result.returncode,
        "seconds": round(time.monotonic() - started, 2),
        "output": result.stdout + result.stderr,
        "primary_accepted": False,
    }
    write(root / f".agent/{unit}-result.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--round", type=int, choices=(1, 2))
    parser.add_argument("--unit", choices=("limit-contract", "report-roundtrip"))
    parser.add_argument("--cohort", default=BASE.name)
    parser.add_argument("--snapshot", default=SNAPSHOT.name)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--batch", default="chain1")
    args = parser.parse_args()
    for label in (args.cohort, args.snapshot):
        if not label or any(
            c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
        ):
            parser.error("invalid cohort or snapshot")
    BASE, SNAPSHOT = WORK / args.cohort, WORK / args.snapshot
    if args.prepare:
        prepare(config_path=args.config, batch=args.batch)
    elif args.round and args.unit:
        SNAPSHOT = Path(read(BASE / "manifest.json")["runtime"])
        run(args.round, args.unit)
    else:
        parser.error("choose prepare or round/unit")
