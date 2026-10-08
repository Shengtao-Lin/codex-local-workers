"""Two fresh mixed numeric-key chains with protected rejection-before-I/O tests."""

import argparse
import copy
import json
import sys
from pathlib import Path

import coordinator_label_evidence as evidence
import coordinator_label_pilot as pilot
import coordinator_numeric_case as fixture
from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-numeric-pilot-1"
SNAPSHOT = WORK / "coordinator-loader-baseline-1"


def configure():
    pilot.BASE, pilot.SNAPSHOT, pilot.fixture = BASE, SNAPSHOT, fixture
    return pilot.configure()


def prepare():
    contract = configure()
    BASE.mkdir(exist_ok=False)
    case = fixture.case()
    write(BASE / "corpus.json", {"cases": [case]})
    write(
        BASE / "primary-oracles.json",
        {
            "labelled-receipt": {
                "reference": fixture.REFERENCE,
                "mutants": [
                    {
                        **fixture.REFERENCE,
                        "src/product/schema.py": fixture.INITIAL[
                            "src/product/schema.py"
                        ],
                    },
                    {
                        **fixture.REFERENCE,
                        "src/product/labels.py": fixture.INITIAL[
                            "src/product/labels.py"
                        ],
                    },
                    {
                        **fixture.REFERENCE,
                        "src/product/collector.py": fixture.INITIAL[
                            "src/product/collector.py"
                        ],
                    },
                    {
                        **fixture.REFERENCE,
                        "src/product/target.py": fixture.INITIAL[
                            "src/product/target.py"
                        ],
                    },
                ],
            }
        },
    )
    source = WORK / "coordinator-mixed-resume-1/runs/control-r2/.agent/config.json"
    config = read(source)
    config["explorer_required_citation_paths"] = [
        "src/product/entry.py",
        "src/product/target.py",
        "src/product/labels.py",
        "src/product/schema.py",
        "src/product/collector.py",
        "tests/test_target.py",
    ]
    cells = []
    for arm in ("control", "coordinator"):
        settings = copy.deepcopy(config)
        settings["coordinator_enabled"] = arm == "coordinator"
        config_path = BASE / f"{arm}-config.json"
        write(config_path, settings)
        root = Path(
            pilot.matrix.MIXED.prepare(
                "labelled-receipt", 1, config_path, "numeric1-" + arm
            )["root"]
        )
        plan = read(root / ".agent/feature-plan.json")
        paths = [
            *case["files"],
            "pyproject.toml",
            ".agent/config.json",
            ".agent/feature-plan.json",
        ]
        for unit in plan["units"]:
            uid = unit["unit_id"]
            packet = read(root / f".agent/{uid}-reference.json")
            packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
            packet = contract.validate_unit_packet(plan, packet)
            load_worker(SNAPSHOT).validate_packet(packet)
            write(root / f".agent/{uid}-bound.json", packet)
            paths.append(f".agent/{uid}-bound.json")
        cells.append(
            {
                "id": arm + "-r1",
                "arm": arm,
                "case": "labelled-receipt",
                "root": str(root),
                "units": [u["unit_id"] for u in plan["units"]],
                "explorer_required": True,
                "hashes": {p: digest(root / p) for p in paths},
            }
        )
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "cells": cells,
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (__file__, fixture.__file__, pilot.__file__, evidence.__file__)
            },
            "qualification_risk": "high",
            "functional_risk": "medium",
        },
    )
    write(
        BASE / "registration.json",
        {
            "order": ["control-r1", "coordinator-r1"],
            "weekly_used_ceiling": 10,
            "classification": "New numeric boundary plus two-file parser unit and async receipt, one fresh paired repetition, not unseen repository transfer or causal cost estimate",
            "coverage": [
                "two-file modification",
                "string-to-integer exact roundtrip",
                "malformed input rejected before fetching",
                "duplicates/false values/error identity",
                "fresh six-path Explorer",
                "proposal without full packet",
            ],
            "hard_plan_owner": "Primary",
            "model_or_budget_changes": False,
            "required_before_writers": "Both fresh Explorers Primary accepted and reference/four mutants verified",
        },
    )
    pilot.matrix.preflight()


def explore(identity):
    cell = next(c for c in pilot.matrix.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, cell["hashes"])
    packet = read(root / ".agent/normalize-unit-bound.json")
    pilot.matrix.SCOPE.invoke(
        root,
        "explorer",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--task",
            "Locate run_batch through labelled_receipt, normalize_labels, parse_code and collect_values, plus protected numeric roundtrip and malformed-input-before-fetch assertions in tests/test_target.py. Cite actual entry, target, labels, schema, collector and tests (six real paths). One call-chain question only, no repairs or validation predictions.",
            "--task-id",
            packet["task_id"],
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
        ],
    )
    print(json.dumps(read(root / ".agent/explorer.json")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "adjudicate",
            "run",
            "check",
            "record",
            "integrate",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="normalize-unit")
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        prepare()
    elif args.action == "explore":
        explore(args.identity)
    elif args.action == "run":
        for cell in pilot.matrix.verify()["cells"]:
            if not read(
                Path(cell["root"]) / ".agent/explorer-primary-adjudication.json"
            )["success"]:
                raise ValueError("both fresh Explorers must be accepted before writing")
        pilot.run(args.identity, args.unit)
    elif args.action == "check":
        evidence.unit_check(args.identity, args.unit)
    elif args.action == "integrate":
        evidence.integrate(args.identity)
    elif args.action == "adjudicate":
        import qualification_evidence as primary

        primary.explorer(args.identity, args.summary)
    else:
        import qualification_controls as primary

        primary.record(args.identity, args.unit, "accept", args.summary)
