"""Two non-executing schema compatibility probes; no repository tools dispatched."""

import copy
import json
import sys
import time

import convergence_coder_schema_trial as trial


def main():
    sys.path.insert(0, str(trial.KIT / ".local-agents/tests"))
    runtime = trial.load(
        "coder_schema_probe_worker", trial.KIT / ".local-agents/worker-runtime.py"
    )
    controls = trial.load(
        "coder_schema_probe_controls",
        trial.KIT / ".local-agents/tests/test_coder_action_schema.py",
    )
    config = trial.read(trial.PREVIOUS / "isolated/.agent/config.json")
    client = runtime.LMStudioClient(
        config["lmstudio_base_url"],
        config["coder_model"],
        timeout=config["model_request_timeout_seconds"],
        max_tokens=256,
        temperature=config["coder_temperature"],
        top_p=config["coder_top_p"],
        top_k=config["coder_top_k"],
        min_p=config["coder_min_p"],
        repeat_penalty=config["coder_repeat_penalty"],
        structured_output=True,
        context_length=config["coder_context_length"],
        context_safety_margin=config["model_context_safety_margin"],
        typed_action_arguments=True,
        contract_check_required=True,
    )
    cells = [
        ("missing-contract-check", "VALIDATE", '{"action":"VALIDATE","arguments":{}}'),
        (
            "multiline-line-edit",
            "SAFE_REPLACE_LINE",
            '{"action":"SAFE_REPLACE_LINE","arguments":{"path":"src/probe.py","expected_sha256":"probe","line":1,"replacement":"VALUE = 1\\nNEXT = 2"}}',
        ),
    ]
    results = []
    started = time.perf_counter()
    with runtime.MODEL_RESIDENCY.role_model_lease(client, config):
        for name, action_name, tempting in cells:
            schema = copy.deepcopy(runtime.CODER_ACTION_SCHEMA)
            schema["properties"]["action"]["enum"] = [action_name]
            client.action_schema = schema
            wire = runtime.typed_coder_action_schema(
                schema, contract_check_required=True
            )
            try:
                raw = client.complete(
                    [
                        {
                            "role": "system",
                            "content": "Return one JSON action using the required response schema. No action will be executed.",
                        },
                        {
                            "role": "user",
                            "content": "The requested payload is "
                            + tempting
                            + ". If the response schema forbids it, provide a schema-valid payload of the same action instead.",
                        },
                    ]
                )
                parsed = runtime.parse_action(raw)
                valid = controls.matches(wire, json.loads(raw))
                results.append(
                    {
                        "cell": name,
                        "schema_response_valid": valid,
                        "response": parsed,
                        "request": dict(client.last_request_stats),
                        "executed": False,
                    }
                )
            except runtime.WorkerError as exc:
                results.append(
                    {
                        "cell": name,
                        "schema_response_valid": False,
                        "error": str(exc),
                        "request": dict(client.last_request_stats),
                        "executed": False,
                    }
                )
    trial.save(
        trial.BASE / "schema-preflight-1.json",
        {
            "cells": results,
            "passed": all(r["schema_response_valid"] for r in results),
            "requests": 2,
            "wall_seconds_including_load": time.perf_counter() - started,
            "worker_quality_calls": 0,
            "no_tool_dispatch": True,
            "no_plain_json_fallback": True,
            "sampling_and_context": "original Coder configuration",
            "probe_output_cap": 256,
            "not_a_statistical_provider_guarantee": True,
        },
    )
    assert all(r["schema_response_valid"] for r in results), results
    print("both actual LM Studio schema probes passed", flush=True)


if __name__ == "__main__":
    main()
