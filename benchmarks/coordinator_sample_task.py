"""One new supervised simulated task; no automatic Primary acceptance."""

import argparse
import json
import time
from pathlib import Path

import coordinator_label_evidence as evidence
import coordinator_numeric_split as split
import coordinator_sample_task_case as fixture
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-sample-task-1"
SNAPSHOT = WORK / "coordinator-sample-task-baseline-1"
IDENTITY = "coordinator-r1"


def configure():
    split.BASE, split.SNAPSHOT = BASE, SNAPSHOT
    split.candidate.numeric.fixture = fixture
    return split.configure()


def prepare():
    freeze(SNAPSHOT.name)
    contract = configure()
    BASE.mkdir(exist_ok=False)
    task = fixture.case()
    write(BASE / "corpus.json", {"cases": [task]})
    write(
        BASE / "primary-oracles.json",
        {
            "labelled-receipt": {
                "reference": fixture.REFERENCE,
                "mutants": [
                    {**fixture.REFERENCE, path: fixture.INITIAL[path]}
                    for path in fixture.REFERENCE
                ],
            }
        },
    )
    config = read(WORK / "coordinator-ownership-retention-1/coordinator-config.json")
    config["coordinator_enabled"] = True
    settings = BASE / "task-config.json"
    write(settings, config)
    matrix = split.candidate.numeric.pilot.matrix
    root = Path(
        matrix.MIXED.prepare("labelled-receipt", 1, settings, "sampletask1")["root"]
    )
    plan = read(root / ".agent/feature-plan.json")
    paths = [
        *task["files"],
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
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "cells": [
                {
                    "id": IDENTITY,
                    "arm": "coordinator",
                    "case": "labelled-receipt",
                    "root": str(root),
                    "units": [u["unit_id"] for u in plan["units"]],
                    "explorer_required": True,
                    "hashes": {p: digest(root / p) for p in paths},
                }
            ],
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (__file__, fixture.__file__)
            },
        },
    )
    write(
        BASE / "registration.json",
        {
            "weekly_used_start": 9,
            "weekly_used_ceiling": 18,
            "started_epoch": time.time(),
            "classification": "Simulated task transfer, not real deployment or cost-savings proof",
            "hard_plan_owner": "Primary",
            "functional_risk": "medium",
            "criterion": "Two accepted focused Explorers, three actual Coder/fresh Reviewer/Primary accepts, seven independent integration tests and static checks. Stop on substantive failure for adjudication; no unchanged replay.",
            "new_coverage": "plus/leading zeros/underscores/negative zero; strict await start-end ordering; result identity; first/middle backend error; five invalid forms rejected before I/O",
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "cost_limit": "One arm only, no causal cost comparison. Active Primary time cannot be inferred from chat gaps; retain actual invocation and validation timing.",
            "global_activation": False,
            "source_project_writes": False,
        },
    )
    matrix.preflight()
    print(json.dumps({"root": str(root), "registered": str(BASE)}))


def run(unit):
    matrix = split.candidate.numeric.pilot.matrix
    root = split.root_for(IDENTITY)
    for mode in split.QUESTIONS:
        primary = read(root / f".agent/{mode}-explorer-primary.json")
        if (
            not primary["success"]
            or digest(root / f".agent/{mode}-explorer.json") != primary["report_sha256"]
        ):
            raise ValueError("fresh accepted Explorer evidence required")
    mode = "parse" if unit == "normalize-unit" else "flow"
    pilot = split.candidate.numeric.pilot
    original = pilot.read

    def selected(path):
        return original(
            root / f".agent/{mode}-explorer.json"
            if Path(path) == root / ".agent/explorer.json"
            else path
        )

    pilot.read = selected
    matrix.verify()
    pilot.run(IDENTITY, unit)


def audit():
    contract = configure()
    matrix = split.candidate.numeric.pilot.matrix
    cell = matrix.verify()["cells"][0]
    root = Path(cell["root"])
    plan = read(root / ".agent/feature-plan.json")
    _, refs, accepted = evidence.provenance(contract, cell, root, plan, True)
    contract.verify_integration_archive(plan, root, refs)
    rows = []
    for uid in cell["units"]:
        packet = read(root / f".agent/{uid}-bound.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        actual, coder, primary = (
            read(archive / name)
            for name in ("packet.json", "handoff.json", "review.json")
        )
        reviewer = read(
            root
            / ".agent/tasks"
            / packet["task_id"]
            / "reviews"
            / primary["local_review_id"]
            / "handoff.json"
        )
        for key in (
            "scope",
            "focused_tests",
            "required_behavior",
            "dependencies",
            "acceptance_scenarios",
            "owned_contract_ids",
            "validation_profile",
        ):
            if actual[key] != packet[key]:
                raise ValueError("contract drift: " + key)
        if any(
            actual["risk"][k] != packet["risk"][k]
            for k in ("feature", "unit", "integration")
        ):
            raise ValueError("risk drift")
        if (
            coder["status"] != "ready_for_review"
            or reviewer["decision"] != "pass_to_primary"
            or primary["decision"] != "accept"
        ):
            raise ValueError("unaccepted unit")
        independent = read(root / f".agent/{uid}-independent-1.json")
        if not independent["passed"]:
            raise ValueError("independent checks failed")
        invocation = read(root / f".agent/{uid}-invocation.json")
        rows.append(
            {
                "unit": uid,
                "seconds": invocation["seconds"],
                "run_id": packet["run_id"],
                "review_id": primary["local_review_id"],
            }
        )
    frozen = read(SNAPSHOT / "freeze.json")["files"]
    if not all(digest(KIT / p) == sha for p, sha in frozen.items()):
        raise ValueError("runtime drift")
    write(
        BASE / "facts-1.json",
        {
            "units": rows,
            "accepted_units": sorted(accepted),
            "integration": read(root / ".agent/feature-integration.json"),
            "local_invocation_seconds": sum(row["seconds"] for row in rows),
            "production_files_verified": len(frozen),
            "primary_feature_accepted": False,
            "cost_savings_established": False,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    print(json.dumps({"facts": str(BASE / "facts-1.json")}))


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
            "audit",
        ),
    )
    parser.add_argument("--mode", choices=("flow", "parse"))
    parser.add_argument("--unit", default="normalize-unit")
    parser.add_argument("--summary")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        configure()
        split.candidate.numeric.pilot.matrix.verify()
        if args.action == "explore":
            scope = split.candidate.numeric.pilot.matrix.SCOPE
            original = scope.invoke
            scope.invoke = lambda root, name, argv: original(
                root, name + "-" + args.mode, argv
            )
            split.explore(IDENTITY, args.mode)
        elif args.action == "adjudicate":
            split.adjudicate(IDENTITY, args.mode, args.summary)
        elif args.action == "run":
            run(args.unit)
        elif args.action == "check":
            evidence.unit_check(IDENTITY, args.unit)
        elif args.action == "record":
            import qualification_controls as controls

            controls.record(IDENTITY, args.unit, "accept", args.summary)
        elif args.action == "integrate":
            evidence.integrate(IDENTITY)
        else:
            audit()
