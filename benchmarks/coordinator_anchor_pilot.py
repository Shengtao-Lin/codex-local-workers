"""Assisted known-location arm; not unaided Explorer qualification."""

import argparse
from pathlib import Path

import coordinator_completion_pilot as previous
from capability_fit import load_worker, write
from inherited_context_recovery import digest, read

BASE = previous.WORK / "coordinator-anchor-pilot-1"
ANCHORS = [
    {"path": "tests/test_target.py", "text": name}
    for name in ("def test_collect_order", "def test_receipt_roundtrip")
]


def configure():
    previous.BASE = BASE
    return previous.configure()


def prepare():
    contract = configure()
    previous.verify_hashes(
        previous.KIT, read(previous.SNAPSHOT / "freeze.json")["files"]
    )
    BASE.mkdir(exist_ok=False)
    source = read(previous.WORK / "coordinator-completion-pilot-1/manifest.json")[
        "cells"
    ][0]
    config = read(Path(source["root"]) / ".agent/config.json")
    config["explorer_required_source_anchors"] = ANCHORS
    write(BASE / "config.json", config)
    root = Path(
        previous.prior.matrix.MIXED.prepare(
            "async-receipt", 1, BASE / "config.json", "anchor-pilot1"
        )["root"]
    )
    plan = read(root / ".agent/feature-plan.json")
    for unit in source["units"]:
        packet = read(root / f".agent/{unit}-reference.json")
        packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
        packet = contract.validate_unit_packet(plan, packet)
        load_worker(previous.SNAPSHOT).validate_packet(packet)
        write(root / f".agent/{unit}-bound.json", packet)
    for path, sha in source["hashes"].items():
        if path.startswith(("src/", "tests/")) or path == "pyproject.toml":
            if digest(root / path) != sha:
                raise ValueError("fixture drift: " + path)
    cell = {
        **source,
        "root": str(root),
        "hashes": {p: digest(root / p) for p in source["hashes"]},
    }
    write(
        BASE / "manifest.json",
        {
            "runtime": str(previous.SNAPSHOT),
            "cells": [cell],
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (__file__, previous.__file__, previous.prior.__file__)
            },
        },
    )
    write(
        BASE / "preflight-1.json",
        read(previous.WORK / "coordinator-completion-pilot-1/preflight-1.json"),
    )
    write(
        BASE / "registration.json",
        {
            "driver_sha256": digest(Path(previous.prior.__file__)),
            "weekly_used_start": 38,
            "weekly_used_ceiling": 40,
            "feature_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Dispatch authority audit; existing functional units medium.",
            "axis": "Two existing trusted source-anchor obligations only; same model, question, runtime and tests.",
            "criterion": "Assisted complete Explorer followed by Primary-adjudicated bounded two-unit Coordinator chain and integration.",
            "unaided_discovery_credit": False,
            "global_coordinator_enabled": False,
        },
    )
    print(root)


def dispatch_gate(root):
    verdict = read(root / ".agent/explorer-primary-adjudication.json")
    report = read(root / ".agent/explorer.json")
    if verdict.get("success") is not True or report.get("status") != "success":
        raise ValueError("Primary semantic Explorer approval required")
    if verdict.get("report_sha256") != digest(root / ".agent/explorer.json"):
        raise ValueError("Primary approval not bound to this report")
    for anchor in ANCHORS:
        if not any(
            r["path"] == anchor["path"]
            and anchor["text"] in r["quote"]
            and digest(root / r["path"]) == r["source_hash"]
            for r in report["source_refs"]
        ):
            raise ValueError("missing unchanged anchor evidence")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action", choices=("prepare", "explore", "run", "record", "integrate")
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
        cell = previous.prior.matrix.verify()["cells"][0]
        root = Path(cell["root"])
        if args.action == "explore":
            if (root / ".agent/explorer.json").exists():
                raise FileExistsError("historical call cannot be replayed")
            previous.prior.matrix.explore("coordinator-r1")
        elif args.action == "run":
            dispatch_gate(root)
            previous.prior.run("coordinator-r1", args.unit)
        elif args.action == "record":
            previous.controls.record(
                "coordinator-r1", args.unit, args.decision, args.summary
            )
        else:
            previous.evidence.integrate("coordinator-r1")
