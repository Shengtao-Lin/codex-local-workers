"""IQ3_S single-resident comparison on two frozen exposed project tasks."""

import argparse
import os
from pathlib import Path

import project_caller_trial as J

S, P = J.S, J.P
BATCH = P.I.BASE / "strata-project-20261023-1"
ENTRY = Path(__file__).with_name("strata_entry.py")
ORIGINAL_SAVE = S.save
ORIGINAL_COMMAND = J.command


def command(root, mode="unit", replay=None):
    argv = ORIGINAL_COMMAND(root, mode=mode, replay=replay)
    return [*argv[:2], str(ENTRY), "unit", *argv[3:]]


def save(path, value):
    path = Path(path)
    if (
        path.name == "config.json"
        and ".agent" in path.parts
        and "prepared" not in path.parts
    ):
        value = dict(value)
        value.update(
            lmstudio_base_url="http://127.0.0.1:47831/v1",
            experimental_strata_transport=True,
            experimental_strata_instance_id="2b1266cf-c609-421d-a538-19bfd4f7ea73",
        )
        for role in ("coder", "reviewer", "explorer", "coordinator"):
            value[role + "_model"] = "iq3_s"
            value[role + "_context_length"] = 32768
        # Keep the exact existing role sampling, editing/check budgets and output caps.
        # Low thinking is explicit for both roles; the old Coder was non-thinking.
    if path == BATCH / "registration.json":
        value = dict(value)
        value.update(
            weekly_cap=40,
            candidate="Unmodified installed bounded-v1/flat-v1, Strata readiness/transport wrapper only",
            model="Strata 0.1.47 Qwen3.8-Flash-Next IQ3_S; actual loaded128K, client32K; parallel1, low reasoning; image reader remains loaded but text-only requests",
            exposure="Two already-exposed tasks, two repeats each; no holdout/new-task credit. Compare historical facts descriptively, not an engine-only causal A/B.",
            difference="Coder and Reviewer model/backend changed together for single-model feasibility. Native readiness adapter replaces LM-specific lifecycle, refuses any LM resident model; no load/unload. Existing role sampling, budget, contracts/checks unchanged.",
            residency_limit="Observed serial exclusivity; cooperative experiment lock, NOT qualified global cross-backend switch management",
            Primary="Existing detailed contracts/tests reused, full independent source review required; no runtime repair hints or takeover. Preparation/coordination time and cloud tokens unknown.",
        )
        value["pins"].update({str(p): S.sha(p) for p in (Path(__file__), ENTRY)})
    return ORIGINAL_SAVE(path, value)


def configure():
    J.BATCH = P.BATCH = BATCH
    J.command = command
    P.ORDER = J.ORDER
    P.command = command
    J.T.run = J.run_check
    S.save = save


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=J.ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    assert 0 <= args.weekly_used < 40
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    configure()
    if args.mode == "prepare":
        assert all(
            S.read(P.I.BASE / "strata-probe-20261023-1" / c / "result.json")["passed"]
            for c in ("plain", "schema", "long-schema")
        )
        J.prepare(args.weekly_used)
    else:
        row = S.read(BATCH / "cells.json")[args.cell]
        P.TARGET = row["target"]
        P.run(args.cell, args.weekly_used)
