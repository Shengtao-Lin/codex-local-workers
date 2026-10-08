"""Opt-in benchmark pytest plugin: bounded observed calls, never inferred fixes.

This is diagnostic code for trusted fixtures, not an execution sandbox. It must
not be combined with another tracer. Normal test outcomes are not changed.
"""

import json
import math
import sys
from itertools import islice
from pathlib import Path

import pytest


def value_fact(value, depth=0):
    kind = type(value)
    if value is None or kind is bool:
        return value
    if kind is int and value.bit_length() < 128:
        return value
    if kind is float and math.isfinite(value):
        return value
    if kind is str:
        return value[:48]
    if depth < 1 and kind is dict:
        return {
            key: value_fact(item, depth + 1)
            for key, item in islice(value.items(), 3)
            if type(key) is str
        }
    if depth < 1 and kind in (list, tuple):
        return [value_fact(item, depth + 1) for item in value[:3]]
    # Never call user __repr__, __str__, __int__, iteration or properties.
    return {"type": type.__getattribute__(kind, "__name__")[:60]}


def pytest_addoption(parser):
    parser.addoption("--witness-source", action="append", default=[])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    paths = {
        str(Path(p).resolve()): Path(p).as_posix()
        for p in item.config.getoption("--witness-source")
    }
    rows = []
    active = {}
    previous = sys.gettrace()
    if previous is not None or not paths:
        yield
        return

    def trace(frame, event, arg):
        filename = str(Path(frame.f_code.co_filename).resolve())
        if filename not in paths:
            return None
        key = id(frame)
        if event == "call":
            if len(rows) >= 8:
                return None
            names = frame.f_code.co_varnames[
                : frame.f_code.co_argcount + frame.f_code.co_kwonlyargcount
            ]
            row = {
                "source": paths[filename],
                "function": frame.f_code.co_name,
                "args": {
                    name: value_fact(frame.f_locals[name])
                    for name in names[:3]
                    if name in frame.f_locals
                },
                "lines": [],
            }
            rows.append(row)
            active[key] = row
        row = active.get(key)
        if row is not None:
            if event == "line" and len(row["lines"]) < 12:
                row["lines"].append(frame.f_lineno)
            elif event == "return":
                row["return_event"] = value_fact(arg)
                active.pop(key, None)
            elif event == "exception":
                row["exception_event"] = type.__getattribute__(arg[0], "__name__")[:60]
        return trace

    sys.settrace(trace)
    try:
        yield
    finally:
        sys.settrace(previous)
        item._execution_witness_rows = rows


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    rows = getattr(item, "_execution_witness_rows", [])
    if report.when != "call" or not report.failed or not rows:
        return
    chosen = []
    for row in rows:
        candidate = json.dumps(chosen + [row], ensure_ascii=True, separators=(",", ":"))
        if len(candidate) > 550:
            break
        chosen.append(row)
    if chosen:
        evidence = json.dumps(chosen, ensure_ascii=True, separators=(",", ":"))
        item.user_properties.append(("execution_witness_v1", evidence))
