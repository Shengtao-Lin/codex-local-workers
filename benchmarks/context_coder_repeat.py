"""Second fresh workspace pair; exact frozen code/tests, reversed execution order."""

import argparse
import copy
import json
import shutil
from pathlib import Path

import context_chain_experiment as experiment
from capability_fit import WORK, write

ORIGINAL = experiment.BASE
BASE = WORK / "roleq-context-coder-repeat-1"


def prepare():
    BASE.mkdir(exist_ok=False)
    original = experiment.read(ORIGINAL / "manifest.json")
    manifest = {"drivers": original["drivers"], "cells": {}}
    write(
        BASE / "plan.json",
        {
            "classification": "Fresh paired replication, same known chain; no unseen-task qualification",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "contracts": ["immutable-history", "independent-role-evidence"],
            "axis": "coder_context_retention",
            "order": ["coder-budgeted", "coder-recent"],
            "runtime": str(experiment.SNAPSHOT),
            "weekly_ceiling": 40,
            "criterion": "Same full protected tests and unchanged helper/test hashes, verified handoff plus independent Reviewer and Primary acceptance",
            "coordinator_started": False,
        },
    )
    for label in ("coder-budgeted", "coder-recent"):
        # The first recent arm made no edits. Verify all copied facts before reuse.
        source = ORIGINAL / "coder-recent"
        root = BASE / label
        root.mkdir()
        for relative, sha in original["cells"]["coder-recent"]["files"].items():
            if experiment.digest(source / relative) != sha:
                raise ValueError("source fixture drift: " + relative)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
        config = experiment.read(root / ".agent/config.json")
        config["coder_context_retention"] = label.split("-", 1)[1]
        packet = experiment.read(root / ".agent/packet.json")
        identity = "context-chain-" + label + "-r2"
        packet.update(task_id=identity, feature_id=identity, run_id=identity + "-a1")
        # Preparation only: these copied files have never been used by a worker.
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )
        (root / ".agent/packet.json").write_text(
            json.dumps(packet, indent=2) + "\n", encoding="utf-8"
        )
        manifest["cells"][label] = {
            "files": {
                p: experiment.digest(root / p)
                for p in original["cells"]["coder-recent"]["files"]
            }
        }
    manifest["replication_driver_sha256"] = experiment.digest(Path(__file__))
    write(BASE / "manifest.json", copy.deepcopy(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", choices=("coder-budgeted", "coder-recent"))
    parser.add_argument("--review", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.run:
        experiment.BASE = BASE
        experiment.run(args.run)
    elif args.review:
        import context_budget_comparison as reviews

        reviews.BASE = BASE
        reviews.coder_review()
    else:
        parser.error("choose prepare, run, or review")
