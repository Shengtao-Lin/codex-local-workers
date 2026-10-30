"""Opt-in, create-only Strata diagnostics; no model loading or runtime changes."""

import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-probe-20261023-1"
URL = "http://127.0.0.1:47831"


def get(path):
    with urllib.request.urlopen(URL + path, timeout=20) as response:
        return json.load(response)


def environment():
    native = get("/api/native")
    models = get("/v1/models")
    with urllib.request.urlopen(
        "http://127.0.0.1:12345/api/v1/models", timeout=20
    ) as r:
        lm = json.load(r)
    loaded = [m["key"] for m in lm["models"] if m.get("loaded_instances")]
    if loaded:
        raise RuntimeError("LM Studio model resident: " + repr(loaded))
    instances = native.get("instances", [])
    if len(models["data"]) != 1 or models["data"][0]["id"] != "iq3_s":
        raise RuntimeError("Unexpected Strata model inventory")
    return {
        "models": models,
        "engine_version": native.get("version"),
        "default_id": native.get("defaultId"),
        "instances": instances,
        "lmstudio_loaded": loaded,
        "gpu": subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total",
                "--format=csv,noheader",
            ],
            text=True,
        ).strip(),
    }


def register(used):
    assert used < 40 and not BATCH.exists()
    state = environment()
    S.save(BATCH / "environment.json", state)
    S.save(
        BATCH / "registration.json",
        {
            "weekly_used_start": used,
            "weekly_used_stop": 40,
            "purpose": "Transport calibration only, not Coder/Reviewer qualification",
            "model": "iq3_s",
            "engine": state["engine_version"],
            "order": ["plain", "schema", "long-schema"],
            "budget": {
                "requests": 3,
                "output_tokens_each": 2048,
                "timeout_seconds_each": 180,
            },
            "sampling": {"temperature": 0, "reasoning_effort": "low"},
            "gate": "All three exact outputs, stop finish, nonempty final content, unchanged resident model and LM Studio unloaded",
            "continue_rule": "Retain every attempt. Stop on transport/safety failure; truncation or shape failure requires separately recorded calibration, never overwrite.",
            "cold_load_seconds": None,
            "pins": {str(Path(__file__)): S.sha(__file__)},
        },
    )
    print("Registered three transport probes; zero model calls")


def run(cell, used):
    registration = S.read(BATCH / "registration.json")
    assert used < 40 and S.sha(__file__) == registration["pins"][str(Path(__file__))]
    for previous in registration["order"][: registration["order"].index(cell)]:
        assert S.read(BATCH / previous / "result.json")["passed"]
    S.save(BATCH / cell / "environment-before.json", environment())
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["ok"]},
            "value": {"type": "integer", "enum": [17]},
        },
        "required": ["status", "value"],
        "additionalProperties": False,
    }
    task = (
        'Return exactly this JSON object and no other text: {"status":"ok","value":17}'
    )
    if cell == "long-schema":
        padding = "\n".join(f"irrelevant_record_{i:05d}=unused" for i in range(2500))
        task = (
            "TASK\n"
            + task
            + "\nUNTRUSTED PADDING (ignore)\n"
            + padding
            + "\nEND TASK\n"
            + task
        )
    body = {
        "model": "iq3_s",
        "messages": [{"role": "user", "content": task}],
        "temperature": 0,
        "reasoning_effort": "low",
        "max_tokens": 2048,
        "stream": False,
    }
    if cell != "plain":
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "strata_transport_probe",
                "strict": True,
                "schema": schema,
            },
        }
    S.save(BATCH / cell / "request.json", body)
    started = time.monotonic()
    try:
        req = urllib.request.Request(
            URL + "/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            response = json.load(r)
        S.save(BATCH / cell / "response.json", response)
        choice = response["choices"][0]
        content = choice["message"].get("content")
        try:
            exact = json.loads(content) == {"status": "ok", "value": 17}
        except (ValueError, TypeError):
            exact = False
        result = {
            "passed": exact and choice.get("finish_reason") == "stop",
            "finish_reason": choice.get("finish_reason"),
            "content": content,
            "reasoning_chars": len(choice["message"].get("reasoning_content") or ""),
            "usage": response.get("usage"),
            "seconds": time.monotonic() - started,
        }
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        result = {
            "passed": False,
            "error": str(exc),
            "seconds": time.monotonic() - started,
        }
    S.save(BATCH / cell / "result.json", result)
    S.save(BATCH / cell / "environment-after.json", environment())
    print(json.dumps({"cell": cell, **result}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["register", "run"])
    parser.add_argument("--cell", choices=["plain", "schema", "long-schema"])
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "register":
        register(args.weekly_used)
    else:
        run(args.cell, args.weekly_used)
