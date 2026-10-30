"""Use explicit raw regex literals in new fixture tests; keep failed preparations."""

import argparse
from pathlib import Path

import stream_slice_transfer_v2 as V2

S, P = V2.S, V2.P
BATCH = P.I.BASE / "stream-slice-transfer-20261022-3"
ORIGINAL_TASKS = V2.tasks


def tasks():
    result = ORIGINAL_TASKS()
    for spec in result.values():
        for kind in ("public", "private"):
            spec[kind] = spec[kind].replace('match="^', 'match=r"^')
    return result


def prepare(used):
    original_save = S.save

    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value["pins"][str(Path(__file__))] = S.sha(__file__)
            value["preparation_failures"] = [
                "stream-slice-transfer-20261022-1/decision.json",
                "stream-slice-transfer-20261022-2/decision.json",
            ]
            value["test_literal_correction"] = (
                "Raw regex prefix only, identical matching behavior, no lint suppression"
            )
        original_save(path, value)

    V2.BATCH, V2.tasks, S.save = BATCH, tasks, save
    try:
        V2.prepare(used)
    finally:
        S.save = original_save


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=V2.V1.ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        P.BATCH, P.ORDER = BATCH, V2.V1.ORDER
        P.run(args.cell, args.weekly_used)
