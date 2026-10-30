"""Six registered chains; reuse existing execution and evidence machinery."""

import argparse
from pathlib import Path

import coordinator_receipt_pilot as pilot
import fixed_release_trial as trial
import qualification_controls as controls
import qualification_evidence as evidence
from capability_fit import load_worker, write
from inherited_context_recovery import digest, read

BASE = trial.BASE / "matrix"
SOURCE = trial.WORK / "explorer-completion-1"
CONTROLS = trial.BASE / "controls"


def configure():
    pilot.BASE, pilot.SOURCE, pilot.SNAPSHOT = BASE, SOURCE, trial.SNAPSHOT
    contract = pilot.configure()
    controls.BASE = CONTROLS
    return contract


def prepare():
    trial.verify()
    loads = list(trial.BASE.glob("load-*.json"))
    if len(loads) != 9 or not all(read(p)["success"] for p in loads):
        raise ValueError("nine successful loads required")
    contract = configure()
    BASE.mkdir(exist_ok=False)
    cells = []
    source_cells = read(SOURCE / "manifest.json")["cells"]
    for repetition in (1, 2):
        for case in ("display-default", "label-rollup", "async-receipt"):
            source = next(c for c in source_cells if c["id"] == f"{case}-r1")
            config = read(Path(source["root"]) / ".agent/config.json")
            config.update(
                model_load_backend="cli",
                model_load_cli_path="C:/Users/Lin/.lmstudio/bin/lms.exe",
                coordinator_enabled=case != "display-default",
            )
            config_path = BASE / f"{case}-r{repetition}-config.json"
            write(config_path, config)
            root = Path(
                pilot.matrix.MIXED.prepare(case, repetition, config_path, "fixed1")[
                    "root"
                ]
            )
            plan = read(root / ".agent/feature-plan.json")
            for unit in source["units"]:
                packet = read(root / f".agent/{unit}-reference.json")
                packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
                packet = contract.validate_unit_packet(plan, packet)
                load_worker(trial.SNAPSHOT).validate_packet(packet)
                write(root / f".agent/{unit}-bound.json", packet)
            for path, sha in source["hashes"].items():
                if (
                    path.startswith(("src/", "tests/")) or path == "pyproject.toml"
                ) and digest(root / path) != sha:
                    raise ValueError("fixture drift: " + path)
            cells.append(
                {
                    **source,
                    "id": f"{case}-r{repetition}",
                    "round": repetition,
                    "arm": "control" if case == "display-default" else "coordinator",
                    "root": str(root),
                    "hashes": {p: digest(root / p) for p in source["hashes"]},
                }
            )
    write(
        BASE / "manifest.json",
        {
            "runtime": str(trial.SNAPSHOT),
            "cells": cells,
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (
                    __file__,
                    pilot.__file__,
                    pilot.matrix.__file__,
                    controls.__file__,
                    evidence.__file__,
                )
            },
        },
    )
    write(
        BASE / "registration.json",
        {
            "driver_sha256": digest(Path(pilot.__file__)),
            "parent_plan": str(trial.BASE / "registration.json"),
            "weekly_used_ceiling": 50,
            "display_default": "single-unit direct C/R baseline; no invented Explorer or Coordinator credit",
            "other_cases": "mandatory fresh Explorer, supervised Coordinator dispatch",
        },
    )
    write(
        BASE / "preflight-1.json",
        {
            "all_pass": True,
            "basis": "Unchanged corpus, protected test hashes and independently discriminated 18-variant qualification preflight",
            "new_credit": False,
        },
    )
    write(BASE / "corpus.json", read(SOURCE / "corpus.json"))
    write(BASE / "primary-oracles.json", read(SOURCE / "primary-oracles.json"))
    print("Six fresh chains prepared: eight units, four required Explorer calls")


def run(identity, unit):
    configure()
    cell = next(c for c in pilot.matrix.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    if cell["explorer_required"]:
        verdict = read(root / ".agent/explorer-primary-adjudication.json")
        if verdict.get("success") is not True or verdict.get("report_sha256") != digest(
            root / ".agent/explorer.json"
        ):
            raise ValueError("report-bound Primary semantic approval required")
    pilot.run(identity, unit)


def prepare_controls():
    configure()
    original = pilot.matrix.MIXED.prepare

    def cli_prepare(case, repetition, config_path, batch, suite="v1"):
        config = read(config_path)
        config.update(
            model_load_backend="cli",
            model_load_cli_path="C:/Users/Lin/.lmstudio/bin/lms.exe",
        )
        path = trial.BASE / "control-configs" / f"{case}-{batch}-{repetition}.json"
        write(path, config)
        return original(case, repetition, path, batch, suite)

    pilot.matrix.MIXED.prepare = cli_prepare
    controls.prepare()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "run",
            "record",
            "integrate",
            "controls-prepare",
            "control",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="qual-unit")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--summary")
    args = parser.parse_args()
    trial.verify()
    configure()
    if args.action == "prepare":
        prepare()
    elif args.action == "explore":
        cell = next(
            c for c in pilot.matrix.verify()["cells"] if c["id"] == args.identity
        )
        if (Path(cell["root"]) / ".agent/explorer.json").exists():
            raise FileExistsError("no replay")
        pilot.matrix.explore(args.identity)
    elif args.action == "run":
        run(args.identity, args.unit)
    elif args.action == "record":
        controls.record(args.identity, args.unit, args.decision, args.summary)
    elif args.action == "integrate":
        evidence.integrate(args.identity)
    elif args.action == "controls-prepare":
        prepare_controls()
    else:
        controls.run(args.identity)
