"""Correct the actual Popen unit entry; v1 treatment failure remains immutable."""

import argparse
import subprocess
from pathlib import Path

import feedback_recovery_trial as V1

BATCH = V1.S.KIT / "benchmarks/work/harness-convergence/feedback-recovery-20261018-3"


def unit_argv(argv):
    result = [str(x) for x in argv]
    old = str(V1.S.KIT / "benchmarks/bounded_evidence_unit.py")
    if old in result:
        result[result.index(old)] = str(
            V1.S.KIT / "benchmarks/feedback_receipt_unit.py"
        )
    return result


def prepare():
    V1.BATCH = BATCH
    original_save = V1.S.save

    def save(path, value):
        if Path(path).name in {"candidate-freeze.json", "registration.json"}:
            value["pins"][str(Path(__file__))] = V1.S.sha(__file__)
            value["pins"][str(V1.S.KIT / "tests/test_feedback_receipt_v2.py")] = (
                V1.S.sha(V1.S.KIT / "tests/test_feedback_receipt_v2.py")
            )
        if Path(path).name == "registration.json":
            value["v1_treatment_failure"] = "feedback-recovery-20261018-1/decision.json"
            value["actual_unit"] = str(V1.S.KIT / "benchmarks/feedback_receipt_unit.py")
        original_save(path, value)

    V1.S.save = save
    V1.prepare()


def run(cell, used, at):
    V1.BATCH = BATCH
    original = subprocess.Popen

    def popen(argv, *args, **kwargs):
        return original(unit_argv(argv), *args, **kwargs)

    subprocess.Popen = popen
    return V1.run(cell, used, at)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("--cell")
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--usage-observed-at", type=float)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare()
        print("v2 prepared; no live")
    else:
        result = run(args.cell, args.weekly_used, args.usage_observed_at)
        print(result["cell"], "stop_batch=", result["stop_batch"])
