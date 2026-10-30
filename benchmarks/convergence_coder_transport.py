"""C3: config-only paired transport qualification, not a new D2 denominator."""

import argparse
import copy
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import convergence_coder as paired
import convergence_execution as controls
from convergence_coder import KIT, save
from convergence_protocol_audit import preservation
from system_convergence import read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/c3-transport-20261011-1"
OLD = KIT / "benchmarks/work/system-convergence/execution-20261011-2"
TARGET = BASE / "candidate-kit"
RUNTIME = TARGET / ".local-agents"
C1 = KIT / "benchmarks/work/system-convergence/c1-20261010-1"


def prepare():
    if BASE.exists():
        raise FileExistsError("C3 identity already exists")
    save(
        BASE / "authorization.json",
        {
            "stage": "C3",
            "user_authorized": True,
            "user_message": "批准",
            "weekly_used_start": 3,
            "weekly_used_ceiling": 15,
            "approved_proposal": ref(OLD, "next-stage-proposal-1.json"),
            "old_D2_remains_HOLD": True,
            "preservation": preservation(),
        },
    )
    shutil.copytree(
        OLD / "candidate-kit",
        TARGET,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )
    for path in (
        "benchmarks/convergence_coder_transport.py",
        "tests/test_convergence_coder_transport.py",
    ):
        shutil.copyfile(KIT / path, TARGET / path)
    cells = []
    for kind, old_root, packet_path, order in (
        (
            "normal",
            OLD / "features/async-first-present/B",
            ".agent/unit-1-packet.json",
            ("baseline", "candidate"),
        ),
        (
            "repair",
            C1 / "cells/errors-baseline",
            ".agent/packet.json",
            ("candidate", "baseline"),
        ),
    ):
        packet = read_object(old_root / packet_path)
        archive = old_root / f".agent/tasks/{packet['task_id']}/runs/{packet['run_id']}"
        images = {
            p["path"]: p for p in json.loads((archive / "preimages.json").read_text())
        }
        if kind == "normal":
            paths = read_object(old_root / ".agent/brief.json")["source_hashes"]
        else:
            old_cell = next(
                c
                for c in read_object(C1 / "registration.json")["cells"]
                if c["id"] == "errors-baseline"
            )
            paths = {p["path"]: p["sha256"] for p in old_cell["inputs"]}
        for arm in order:
            identity = kind + "-" + arm
            root = BASE / "cells" / identity
            for path, digest in paths.items():
                source = old_root / (
                    images[path]["archive_path"] if path in images else path
                )
                assert sha256(source) == digest
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            current = copy.deepcopy(packet)
            task = "convergence-c3-" + identity
            current.update(task_id=task, feature_id=task, run_id=task + "-a1")
            config = read_object(
                OLD / "features/async-first-present/B/.agent/config.json"
            )
            # No Coordinator calls in a worker transport experiment; same in both arms.
            config.update(
                coordinator_enabled=False,
                coder_typed_action_arguments=arm == "candidate",
            )
            save(root / ".agent/packet.json", current)
            save(root / ".agent/config.json", config)
            for name, argv in (
                ("initial-lint", ["-m", "ruff", "check", "src", "tests"]),
                ("initial-format", ["-m", "ruff", "format", "--check", "src", "tests"]),
            ):
                assert (
                    controls.command(root, argv, root / (".agent/" + name + ".json"))
                    == 0
                )
            # Original faulty preimages, not a successful draft or substituted task.
            assert (
                controls.command(
                    root,
                    [
                        "-m",
                        "pytest",
                        "-q",
                        "-p",
                        "no:cacheprovider",
                        "--junitxml=" + str(root / ".agent/preimage.xml"),
                    ],
                    root / ".agent/preimage-test.json",
                )
                == 1
            )
            cells.append(
                {
                    "id": identity,
                    "kind": kind,
                    "arm": arm,
                    "root": str(root),
                    "identity": {
                        k: current[k] for k in ("task_id", "unit_id", "run_id")
                    },
                    "inputs": [ref(root, p) for p in paths],
                    "writable": current["scope"]["modify"],
                    "packet": ref(root, ".agent/packet.json"),
                    "config": ref(root, ".agent/config.json"),
                    "origin_packet": ref(old_root, packet_path),
                    "origin_preimages": ref(archive, "preimages.json"),
                }
            )
    save(
        BASE / "preparation.json",
        {
            "cells": cells,
            "source_runtime": read_object(OLD / "registration.json")["runtime"],
            "previous_positive_controls": [
                ref(C1, "positive-errors.xml"),
                ref(OLD, "preflight.json"),
            ],
        },
    )


def bind():
    controls.BASE, controls.TARGET, controls.RUNTIME = BASE, TARGET, RUNTIME
    paired.BASE = BASE
    paired.ARMS = {"baseline": RUNTIME, "candidate": RUNTIME}


def register():
    prep = read_object(BASE / "preparation.json")
    cases = list(ET.parse(BASE / "full-regression-2.xml").iter("testcase"))
    assert cases and all(
        c.find("failure") is None and c.find("error") is None for c in cases
    )
    skips = [c.attrib for c in cases if c.find("skipped") is not None]
    assert len(skips) == 1 and "symlink" in skips[0]["name"]
    for p in prep["source_runtime"]:
        assert sha256(RUNTIME / p["path"]) == p["sha256"]
    save(
        BASE / "registration.json",
        {
            "stage": "C3",
            "registered_calls": 4,
            "cells": prep["cells"],
            "driver": ref(KIT, "benchmarks/convergence_coder.py"),
            "wrapper": ref(KIT, "benchmarks/convergence_coder_transport.py"),
            "runtime": {
                arm: [ref(RUNTIME, p["path"]) for p in prep["source_runtime"]]
                for arm in ("baseline", "candidate")
            },
            "full_regression": ref(BASE, "full-regression-2.xml"),
            "host_skips": skips,
            "preparation": ref(BASE, "preparation.json"),
            "authorization": ref(BASE, "authorization.json"),
            "weekly_used_start": 3,
            "weekly_used_ceiling": 15,
            "single_axis": "coder_typed_action_arguments false versus true; identical runtime, prompts, contracts, budgets and role configuration",
            "target_error_measure": "Tool errors for invalid/missing SAFE_REPLACE_LINE fields and VALIDATE contract_check shape/missing acknowledgements; exact action/error text retained. Other errors separately reported",
            "order": [c["id"] for c in prep["cells"]],
            "promotion": "Both candidate full chains accepted with current tests/checks, safety controls pass, and fewer target field errors than paired baseline. If no observed benefit KEEP_BASELINE; any candidate failure HOLD. No semantic transfer/D2/I1 promotion",
            "interventions": "One initial call each; no external rework, Primary business edits, resampling or changed hints. Fresh automatic Reviewer for actual Coder successes. Stop on safety failure or two consecutive same no-progress semantic failures; unrun registered cells remain unrun",
            "prior_exposure": "Both tasks previously exposed. Same Primary context; small, nonrandomized diagnostic comparison, not general success-rate estimate",
            "classification_route": "Old classification-shapes semantic failure remains unqualified, Primary-owned; no new classification calls",
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "economics": "UNMEASURED",
        },
    )


def run(identity):
    record = read_object(BASE / "registration.json")
    assert sha256(Path(__file__)) == record["wrapper"]["sha256"]
    paired.run(identity)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "regression", "register", "run"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    bind()
    if args.action == "prepare":
        prepare()
    elif args.action == "regression":
        controls.regression()
    elif args.action == "register":
        register()
    else:
        run(args.cell)
