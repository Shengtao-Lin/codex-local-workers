"""Retain private functions' use sites in isolated source; no check suppression."""

import argparse
from pathlib import Path

import stream_slice_transfer as V1

S, P = V1.S, V1.P
BATCH = P.I.BASE / "stream-slice-transfer-20261022-2"
ORIGINAL_TASKS = V1.tasks


def tasks():
    result = ORIGINAL_TASKS()
    result["frame"]["header"] += (
        "\n\ndef render_event(event: str, data: str) -> str:\n    return _sse(event, data)\n"
    )
    result["text"]["header"] += (
        "\n\ndef render_content(value: object) -> str:\n    return _text(value)\n"
    )
    for topic, wrapper in (("frame", "render_event"), ("text", "render_content")):
        symbol = result[topic]["symbol"]
        for kind in ("public", "private"):
            result[topic][kind] = result[topic][kind].replace(
                "from product.code import " + symbol,
                f"from product.code import {wrapper} as {symbol}",
            )
    return result


def prepare(used):
    original_save = S.save

    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value["pins"][str(Path(__file__))] = S.sha(__file__)
            value["prior_preparation_failure"] = (
                "stream-slice-transfer-20261022-1/decision.json"
            )
            value["fixture_change"] = (
                "Protected public forwarding callers retain actual use of each private function; public/private tests execute through those callers. No checks suppressed, signature or target behavior unchanged."
            )
        original_save(path, value)

    V1.BATCH, V1.tasks, S.save = BATCH, tasks, save
    try:
        V1.prepare(used)
    finally:
        S.save = original_save


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=V1.ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        P.BATCH, P.ORDER = BATCH, V1.ORDER
        P.run(args.cell, args.weekly_used)
