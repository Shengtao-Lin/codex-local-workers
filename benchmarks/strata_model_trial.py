"""Register model-specific IQ3_S settings separately from historical attempts."""

import argparse
import os
from pathlib import Path

import strata_project_trial as FIRST

S, J, P = FIRST.S, FIRST.J, FIRST.P
BATCH = P.I.BASE / "strata-project-20261023-2"
ENTRY = Path(__file__).with_name("strata_model_entry.py")
BASE_SAVE = FIRST.ORIGINAL_SAVE


def save(path, value):
    path = Path(path)
    if (
        path.name == "config.json"
        and ".agent" in path.parts
        and "prepared" not in path.parts
    ):
        value = dict(value)
        value.update(
            experimental_strata_model_profile="thinking-v1",
            experimental_strata_thinking_tokens=4096,
            model_request_timeout_seconds=600,
            reviewer_reasoning_strength="medium",
        )
        for role in ("coder", "reviewer"):
            value[role + "_context_length"] = 65536
            value[role + "_max_tokens"] = 12288
            value[role + "_temperature"] = 1.0
            value[role + "_top_p"] = 0.95
            value[role + "_top_k"] = 20
    if path == BATCH / "registration.json":
        value = dict(value)
        value.update(
            candidate="Installed bounded-v1/flat-v1 with explicit Strata thinking-v1 backend profile",
            model="Same IQ3_S instance128K/parallel1/vision-on; client64K; medium thinking; temperature1/top_p.95/top_k20",
            budget="C12requests/3edits/1initial+3postchecks900s; R16requests600s; each request max12288 total output with4096 thinking budget and600s timeout; cell2220s batch5400s",
            difference="Joint model-specific profile: client32K->64K, output4096->12288, explicit4096 thinking allowance, medium effort and model-card sampling. Actual engine128K unchanged; no reload or repair hints. Not a single-factor causal experiment.",
            prerequisite="Initial batch -1 infrastructure HOLD and separate two-cell calibration retained; no historical score replacement.",
        )
        value["pins"].update(
            {
                str(p): S.sha(p)
                for p in (
                    Path(__file__),
                    ENTRY,
                    Path(FIRST.__file__),
                    Path(__file__).with_name("strata_entry.py"),
                )
            }
        )
    return BASE_SAVE(path, value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=J.ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    assert args.weekly_used < 40
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    FIRST.BATCH = BATCH
    FIRST.ENTRY = ENTRY
    FIRST.configure()
    FIRST.ORIGINAL_SAVE = save
    if args.mode == "prepare":
        assert (
            P.I.BASE / "strata-output-20261023-1/schema-capped/result.json"
        ).exists()
        J.prepare(args.weekly_used)
    else:
        row = S.read(BATCH / "cells.json")[args.cell]
        P.TARGET = row["target"]
        P.run(args.cell, args.weekly_used)
