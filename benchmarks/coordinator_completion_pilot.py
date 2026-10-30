"""One fresh, Primary-plan-bound Coordinator chain after Explorer completion gate."""

import argparse
from pathlib import Path

import coordinator_receipt_pilot as prior
import qualification_controls as controls
import qualification_evidence as evidence
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "coordinator-completion-pilot-1"
SOURCE = WORK / "explorer-completion-1"
SNAPSHOT = WORK / "explorer-completion-runtime-1"


def configure():
    prior.BASE, prior.SOURCE, prior.SNAPSHOT = BASE, SOURCE, SNAPSHOT
    return prior.configure()


def prepare():
    contract = configure()
    verify_hashes(KIT, read(SNAPSHOT / "freeze.json")["files"])
    assert read(SOURCE / "primary-stage-decision-1.json")["decision"] == (
        "GO_ISOLATED_COORDINATOR_PILOT_KNOWN_SCOPE"
    )
    BASE.mkdir(exist_ok=False)
    source = next(
        c
        for c in read(SOURCE / "manifest.json")["cells"]
        if c["id"] == "async-receipt-r1"
    )
    config = read(Path(source["root"]) / ".agent/config.json")
    config["coordinator_enabled"] = True
    config_path = BASE / "pilot-config.json"
    write(config_path, config)
    root = Path(
        prior.matrix.MIXED.prepare(
            "async-receipt", 1, config_path, "completion-pilot1"
        )["root"]
    )
    plan = read(root / ".agent/feature-plan.json")
    for unit in ("collect-unit", "qual-unit"):
        packet = read(root / f".agent/{unit}-reference.json")
        packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
        packet = contract.validate_unit_packet(plan, packet)
        load_worker(SNAPSHOT).validate_packet(packet)
        write(root / f".agent/{unit}-bound.json", packet)
    for path, sha in source["hashes"].items():
        if path.startswith(("src/", "tests/")) or path == "pyproject.toml":
            assert digest(root / path) == sha, path
    drivers = {
        str(Path(p).resolve()): digest(Path(p))
        for p in (
            __file__,
            prior.__file__,
            prior.matrix.__file__,
            controls.__file__,
            evidence.__file__,
        )
    }
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "drivers": drivers,
            "feature_id": "controlled-completion-pilot",
            "feature_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Dispatch authority audit; functional units medium.",
            "cells": [
                {
                    "id": "coordinator-r1",
                    "case": "async-receipt",
                    "round": 1,
                    "arm": "coordinator",
                    "root": str(root),
                    "units": ["collect-unit", "qual-unit"],
                    "explorer_required": True,
                    "hashes": {p: digest(root / p) for p in source["hashes"]},
                }
            ],
        },
    )
    write(
        BASE / "preflight-1.json",
        {
            "all_pass": True,
            "new_model_credit": False,
            "basis": "Unchanged qualified corpus source/test hashes; inherited discriminating preflight, plus new failing baseline from MIXED.prepare.",
        },
    )
    write(
        BASE / "registration.json",
        {
            "driver_sha256": digest(Path(prior.__file__)),
            "wrapper_sha256": digest(Path(__file__)),
            "weekly_used_start": 37,
            "weekly_used_ceiling": 40,
            "criterion": "Fresh complete Explorer; two bounded Coordinator dispatches; two actual Coder/Reviewer/Primary accepts; full integration; no scope or dependency bypass.",
            "primary_authority": "Preapproved plan, identity, contract, scopes and tests; validate model proposal mechanically before dispatch; Primary accepts each result separately.",
            "not_evaluated": [
                "autonomous decomposition",
                "unfamiliar repositories",
                "cost savings",
                "unattended operation",
            ],
            "global_coordinator_enabled": False,
        },
    )
    print(root, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "run",
            "record",
            "adjudicate-explorer",
            "integrate",
        ),
    )
    parser.add_argument("--unit", default="collect-unit")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        prepare()
    else:
        prior.matrix.verify()
        if args.action == "explore":
            root = Path(read(BASE / "manifest.json")["cells"][0]["root"])
            assert not (root / ".agent/explorer.json").exists(), "fresh calls only"
            prior.matrix.explore("coordinator-r1")
        elif args.action == "run":
            prior.run("coordinator-r1", args.unit)
        elif args.action == "record":
            controls.record("coordinator-r1", args.unit, args.decision, args.summary)
        elif args.action == "adjudicate-explorer":
            evidence.explorer("coordinator-r1", args.summary)
        else:
            evidence.integrate("coordinator-r1")
