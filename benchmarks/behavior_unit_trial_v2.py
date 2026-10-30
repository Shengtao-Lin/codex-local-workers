"""Fresh registration after a zero-model nullable-list startup failure."""

import argparse
from pathlib import Path

import behavior_unit_trial as V1

BATCH = V1.S.KIT / "benchmarks/work/harness-convergence/behavior-unit-20261018-2"
EXTRA = [
    "benchmarks/behavior_unit_candidate_v2.py",
    "benchmarks/behavior_unit_entry_v2.py",
    "benchmarks/behavior_unit_unit_v2.py",
    "benchmarks/behavior_unit_trial_v2.py",
    "tests/test_behavior_unit_v2.py",
]


def unit_argv(argv):
    if not isinstance(argv, (list, tuple)):
        return argv
    result = [str(a) for a in argv]
    old = str(V1.S.KIT / "benchmarks/bounded_evidence_unit.py")
    if old in result:
        result[result.index(old)] = str(
            V1.S.KIT / "benchmarks/behavior_unit_unit_v2.py"
        )
    return result


def prepare(used):
    V1.BATCH = BATCH
    original_save = V1.S.save
    original_check = V1.T.run

    def save(path, value):
        if Path(path).name in {"candidate-freeze.json", "registration.json"}:
            value["pins"].update(
                {str(V1.S.KIT / p): V1.S.sha(V1.S.KIT / p) for p in EXTRA}
            )
        if Path(path).name == "registration.json":
            value["amendment"] = (
                "v1 B startup zero model requests: configured_checks None. Presentation-only empty-list view, immutable original validation retained. Old batch closed, not overwritten."
            )
        original_save(path, value)

    def check(argv, root, timeout=120):
        argv = [str(x) for x in argv]
        old = str(V1.S.KIT / "benchmarks/behavior_unit_entry.py")
        if old in argv:
            argv[argv.index(old)] = str(
                V1.S.KIT / "benchmarks/behavior_unit_entry_v2.py"
            )
        return original_check(argv, root, timeout)

    V1.S.save = save
    V1.T.run = check
    V1.prepare(used)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("--cell")
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--usage-observed-at", type=float)
    args = p.parse_args()
    V1.BATCH = BATCH
    V1.unit_argv = unit_argv
    if args.mode == "prepare":
        prepare(args.weekly_used)
        print("v2 ready; no live")
    else:
        result = V1.run(args.cell, args.weekly_used, args.usage_observed_at)
        print(result["cell"], "stop_batch=", result["stop_batch"])
