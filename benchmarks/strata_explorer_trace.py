"""Opt-in TRACE evidence accounting on the frozen Strata read adapter."""

import argparse
import os
from pathlib import Path

import strata_explorer_arguments as ARGS
import strata_trace_progress as TRACE

E, MODEL = ARGS.E, ARGS.MODEL


def patch(module, config):
    ARGS.patch(module, config)
    TRACE.install(module)


def save(path, value):
    path = Path(path)
    if path == E.BATCH / "registration.json":
        value = dict(value)
        value.update(
            candidate="Serial read tools, exact argument normalization, investigate mode, plus unique TRACE graph progress",
            differences="Only newly observed trusted TRACE edges reset no-progress. Duplicate/empty traces, citation rights, source scope and all budgets unchanged.",
            exposure="Already exposed hash question twice; no new holdout credit; all earlier failures retained.",
            risk={
                "feature_id": "strata-explorer-trace-progress",
                "feature": "medium",
                "unit": "medium",
                "integration": "medium",
                "contracts": [
                    "read-only",
                    "unique-evidence-progress",
                    "source-backed-answer",
                ],
                "rationale": "Experimental observation accounting only; must not grant source citation or additional execution authority.",
            },
            offline_evidence="strata-trace-progress-20261023-1: red control, combined40 green controls, actual request_hash observation replay; composition controls run before live",
        )
        value["pins"].update(
            {
                str(p): E.S.sha(p)
                for p in (
                    Path(ARGS.__file__),
                    Path(ARGS.INVEST.__file__),
                    Path(ARGS.SERIAL.__file__),
                    Path(E.__file__),
                    Path(TRACE.__file__),
                    Path(__file__).parents[1] / "tests/test_strata_trace_progress.py",
                    Path(__file__).parents[1]
                    / "tests/test_strata_trace_composition.py",
                )
            }
        )
    return ARGS.save(path, value)


if __name__ == "__main__":
    E.BATCH = E.S.KIT / "benchmarks/work/harness-convergence/strata-explorer-20261023-5"
    E.ENTRY = Path(__file__).resolve()
    question = E.TASKS["hash"]
    E.TASKS = {"hash-1": question, "hash-2": question}
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run", "worker"])
    parser.add_argument("--cell", choices=E.TASKS)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    if args.mode == "prepare":
        E.S.save = save
        E.prepare(args.weekly_used)
    elif args.mode == "worker":
        MODEL.patch = patch
        raise SystemExit(E.worker(args))
    else:
        E.run(args.cell, args.weekly_used)
