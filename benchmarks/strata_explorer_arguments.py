"""One exact native read-argument envelope normalization, no new tool rights."""

import argparse
import io
import json
import os
from pathlib import Path

import strata_explorer_investigate as INVEST

E, MODEL, SERIAL = INVEST.E, INVEST.MODEL, INVEST.SERIAL
BASE_SAVE = E.S.save


def arguments(value):
    if not isinstance(value, dict):
        raise TypeError("Read arguments must be an object")
    if set(value) == {"arguments"}:
        inner = value["arguments"]
        if not isinstance(inner, dict) or "arguments" in inner:
            raise ValueError("Only one exact object wrapper is supported")
        return dict(inner)
    return value


def normalized_calls(calls):
    result = []
    for call in calls:
        function = dict(call["function"])
        if function.get("name") in {"READ_FILE", "SEARCH", "TRACE", "LIST_FILES"}:
            raw = function["arguments"]
            value = json.loads(raw) if isinstance(raw, str) else raw
            function["arguments"] = json.dumps(arguments(value))
        result.append({**call, "function": function})
    return result


def batch(calls):
    return INVEST.read_batch(normalized_calls(calls))


def patch(module, config):
    SERIAL.read_batch = batch
    SERIAL.patch(module, config)
    original_open = module.urllib.request.urlopen

    def urlopen(req, *args, **kwargs):
        response = original_open(req, *args, **kwargs)
        if not isinstance(
            req, module.urllib.request.Request
        ) or not req.full_url.endswith("/chat/completions"):
            return response
        with response as r:
            value = json.load(r)
        message = value["choices"][0]["message"]
        if message.get("tool_calls"):
            message["tool_calls"] = normalized_calls(message["tool_calls"])
        # The preceding model-profile wrapper retained the exact original wire.
        return io.BytesIO(json.dumps(value).encode())

    module.urllib.request.urlopen = urlopen


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
            candidate="Same serial4-read-tool investigate candidate plus one exact native read-argument wrapper normalization",
            differences="Only native read calls with exactly {'arguments':object} unwrap once. No semantic hint, query change, report normalization, write tool, scope or budget increase.",
            exposure="Same already-exposed hash investigation twice, not new task or holdout; old failures preserved.",
            gate="Both complete answers backed by actual read source; correctly identify request_hash/canonical_json and scoped absence of stable_message_id in that path; no broad repo absence or invented executions.",
        )
        value["pins"].update(
            {
                str(p): E.S.sha(p)
                for p in (
                    Path(E.__file__),
                    Path(INVEST.__file__),
                    Path(SERIAL.__file__),
                    Path(__file__).parents[1] / "tests/test_strata_arguments.py",
                )
            }
        )
    return BASE_SAVE(path, value)


if __name__ == "__main__":
    E.BATCH = E.S.KIT / "benchmarks/work/harness-convergence/strata-explorer-20261023-4"
    E.ENTRY = Path(__file__).resolve()
    question = E.TASKS["hash"]
    E.TASKS = {"hash-1": question, "hash-2": question}
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run", "worker"])
    p.add_argument("--cell", choices=E.TASKS)
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    if a.mode == "prepare":
        E.S.save = save
        E.prepare(a.weekly_used)
    elif a.mode == "worker":
        MODEL.patch = patch
        raise SystemExit(E.worker(a))
    else:
        E.run(a.cell, a.weekly_used)
