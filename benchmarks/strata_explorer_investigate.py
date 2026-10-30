"""Correct task/mode fit and retain all four existing read-only tools."""

import argparse
import json
import os
from pathlib import Path

import strata_explorer_serial as SERIAL

E, MODEL = SERIAL.E, SERIAL.MODEL
BASE_SAVE = E.S.save


def read_batch(calls):
    if not isinstance(calls, list) or not 2 <= len(calls) <= 4:
        raise ValueError("Expected two to four read-only tool calls")
    actions = []
    for call in calls:
        if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
            raise TypeError("Invalid tool call")
        function = call["function"]
        name = function.get("name")
        if name not in {"READ_FILE", "SEARCH", "LIST_FILES", "TRACE"}:
            raise ValueError("Only existing read-only tools can be serialized")
        raw = function.get("arguments")
        arguments = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be an object")
        actions.append({"action": name, "arguments": arguments})
    return actions


def save(path, value):
    path = Path(path)
    if path.name == "config.json":
        value = {
            **value,
            "explorer_mode": "investigate",
            "explorer_answer_protocol": False,
            "explorer_required_source_anchors": [],
        }
    if path == E.BATCH / "registration.json":
        value = dict(value)
        value.update(
            candidate="Original investigate mode, typed location answer disabled, complete4-tool read-only batch normalization",
            differences="Correct two experimental preparation defects only: retain already-advertised TRACE and select existing investigate mode for explain/trace questions. Same model/profile/questions/snapshot/budgets/scopes, no new permission, no production change.",
            prior="strata-explorer-20261023-1 native batch mismatch; -2 corrected batching but omitted TRACE and used locate mode for trace task. Preserve both failures and partial notes, do not label them model navigation failures.",
            controls="Offline whole-batch rejection, original4 read-only tool set and original scope/execution guards; no batch reports/writes",
        )
        value["pins"].update(
            {
                str(p): E.S.sha(p)
                for p in (
                    Path(SERIAL.__file__),
                    Path(E.__file__),
                    Path(__file__).parents[1] / "tests/test_strata_read_batch_v2.py",
                )
            }
        )
    return BASE_SAVE(path, value)


if __name__ == "__main__":
    E.BATCH = E.S.KIT / "benchmarks/work/harness-convergence/strata-explorer-20261023-3"
    E.ENTRY = Path(__file__).resolve()
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run", "worker"])
    parser.add_argument("--cell", choices=E.TASKS)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    SERIAL.read_batch = read_batch
    if args.mode == "prepare":
        E.S.save = save
        E.prepare(args.weekly_used)
    elif args.mode == "worker":
        MODEL.patch = SERIAL.patch
        raise SystemExit(E.worker(args))
    else:
        E.run(args.cell, args.weekly_used)
