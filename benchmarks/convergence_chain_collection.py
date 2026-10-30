"""Thin P1 registration adapter for already completed convergence chains; never launches."""

import argparse
from pathlib import Path

from convergence_coder import KIT, save
from system_convergence import collect, read_object, ref


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch")
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    base = KIT / "benchmarks/work/system-convergence" / args.batch
    original = read_object(base / "registration.json")
    registration = {
        "schema_version": 1,
        "experiment_id": args.batch + "-collection",
        "worker_launch_allowed": False,
        "cells": [],
        "baseline": ref(
            KIT, "benchmarks/work/system-convergence/p0p1-20261010-1/baseline-manifest.json"
        ),
        "source_batches": [ref(KIT, (base / "registration.json").relative_to(KIT).as_posix())],
    }
    for cell in original["cells"]:
        root = Path(cell["root"])
        ident = cell["identity"]
        run = f".agent/tasks/{ident['task_id']}/runs/{ident['run_id']}"
        primary = read_object(root / run / "review.json")
        compact = read_object(root / ".agent/reviewer.json")
        paths = {
            label: run + "/" + filename
            for label, filename in {
                "packet": "packet.json",
                "coder": "handoff.json",
                "completed": "completed.json",
                "validation": "validation.json",
                "post_state": "post-state.json",
                "primary": "review.json",
                "diff": "cumulative.diff",
                "baseline": "baseline.json",
                "preimages": "preimages.json",
            }.items()
        }
        paths.update(
            compact=".agent/coder.json",
            reviewer_compact=".agent/reviewer.json",
            independent_audit="independent-audit.json",
            independent_junit=".agent/primary-tests.xml",
        )
        if primary["local_review_id"]:
            paths["reviewer"] = (
                f".agent/tasks/{ident['task_id']}/reviews/{primary['local_review_id']}/handoff.json"
            )
        validation = read_object(root / paths["validation"])
        paths["junit"] = validation["focused_tests"]["junit"]["path"]
        for attempt in (root / run).glob("validation-attempt-*.json"):
            paths[attempt.stem] = run + "/" + attempt.name
        protected = {
            a["path"]: a["sha256"] for a in cell["inputs"] if a["path"] not in cell["writable"]
        }
        protected.update(
            {
                ".agent/packet.json": cell["packet"]["sha256"],
                ".agent/config.json": cell["config"]["sha256"],
            }
        )
        registration["cells"].append(
            {
                "cell_id": cell["id"],
                "root": root.relative_to(KIT).as_posix(),
                "identity": ident,
                "arm": cell["arm"],
                "expected": {
                    "coder_status": "ready_for_review",
                    "reviewer_outcome": compact["decision"],
                    "primary_decision": primary["decision"],
                },
                "protected_hashes": protected,
                "artifacts": {label: ref(root, path) for label, path in paths.items()},
            }
        )
    save(base / f"p1-registration-{args.attempt}.json", registration)
    result = collect(KIT, registration)
    save(base / f"p1-collection-{args.attempt}.json", result)
    print(result["complete_cells"], result["all_expected_match"])


if __name__ == "__main__":
    main()
