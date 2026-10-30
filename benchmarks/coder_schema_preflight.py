"""Non-executing real LM Studio schema compatibility probe."""

import argparse
import json

from capability_fit import WORK, load_worker, write
from inherited_context_recovery import read

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--negative", action="store_true")
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    snapshot = WORK / "coder-tagged-runtime-1"
    worker = load_worker(snapshot)
    config = read(WORK / "limit-baseline-1/semantic-baseline-1/.agent/config.json")
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        config["coder_model"],
        config.get("model_request_timeout_seconds", 180),
        max_tokens=4096,
        temperature=config["coder_temperature"],
        top_p=config["coder_top_p"],
        top_k=config["coder_top_k"],
        min_p=config["coder_min_p"],
        repeat_penalty=config["coder_repeat_penalty"],
        context_length=config["coder_context_length"],
        typed_action_arguments=not args.native,
        native_tools=(
            [
                {
                    "type": "function",
                    "function": {
                        "name": branch["properties"]["action"]["enum"][0],
                        "description": "Bounded canonical action; runtime validates every argument before execution",
                        "parameters": branch["properties"]["arguments"],
                    },
                }
                for branch in worker.typed_coder_action_schema(
                    worker.CODER_ACTION_SCHEMA
                )["anyOf"]
            ]
            if args.native
            else None
        ),
    )
    if args.native:
        client.native_tool_choice = "required"
    facts = {"executes_actions": False, "compatibility_only": True, "probes": []}
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        probes = (
            ("READ_FILE", {"path": "src/example.py", "start_line": 1, "end_line": 2}),
            (
                "SAFE_REPLACE_LINE",
                {
                    "path": "src/example.py",
                    "line": 12,
                    "expected_sha256": "a" * 64,
                    "replacement": "value = 2",
                },
            ),
            (
                "SAFE_REPLACE",
                {
                    "path": "src/example.py",
                    "expected_sha256": "b" * 64,
                    "find": "old",
                    "replace": "new\nnext",
                },
            ),
        )
        if args.negative:
            client.action_schema = json.loads(json.dumps(worker.CODER_ACTION_SCHEMA))
            client.action_schema["properties"]["action"]["enum"] = ["SAFE_REPLACE_LINE"]
            probes = (
                (
                    "SAFE_REPLACE_LINE",
                    {
                        "path": "src/example.py",
                        "expected_sha256": "a" * 64,
                        "replacement": "value = 2",
                    },
                ),
                (
                    "SAFE_REPLACE_LINE",
                    {
                        "path": "src/example.py",
                        "line": None,
                        "expected_sha256": "a" * 64,
                        "replacement": "value = 2",
                    },
                ),
                (
                    "SAFE_REPLACE_LINE",
                    {
                        "path": "src/example.py",
                        "line": 12,
                        "expected_sha256": "a" * 64,
                        "replacement": "value = 2\nnext = 3",
                    },
                ),
            )
        for action, arguments in probes:
            try:
                raw = client.complete(
                    [
                        {
                            "role": "user",
                            "content": "Non-executing compatibility probe. Return exactly this canonical action and arguments: "
                            + json.dumps({"action": action, "arguments": arguments}),
                        }
                    ]
                )
                result = json.loads(raw)
                returned = (
                    result.get("arguments", {}) if isinstance(result, dict) else {}
                )
                line_conformance = (
                    (
                        result.get("action") == "SAFE_REPLACE_LINE"
                        and set(returned)
                        == {"path", "line", "expected_sha256", "replacement"}
                        and type(returned.get("line")) is int
                        and returned["line"] >= 1
                        and all(
                            isinstance(returned.get(field), str)
                            for field in ("path", "expected_sha256", "replacement")
                        )
                        and "\n" not in returned["replacement"]
                        and "\r" not in returned["replacement"]
                    )
                    if args.negative
                    else None
                )
                facts["probes"].append(
                    {
                        "action": action,
                        "exact_match": result
                        == {"action": action, "arguments": arguments},
                        "error": None,
                        "line_schema_conformance": line_conformance,
                        "stats": dict(client.last_request_stats),
                    }
                )
            except Exception as exc:  # noqa: BLE001 -- immutable infra diagnostics
                facts["probes"].append(
                    {
                        "action": action,
                        "exact_match": False,
                        "error": f"{type(exc).__name__}: {exc}",
                        "stats": dict(client.last_request_stats),
                    }
                )
                break
    facts["negative_probe"] = args.negative
    facts["native_transport"] = args.native
    facts["passed"] = len(facts["probes"]) == 3 and all(
        p.get("line_schema_conformance") if args.negative else p["exact_match"]
        for p in facts["probes"]
    )
    write(
        WORK
        / (
            "coder-native-negative-1"
            if args.native and args.negative
            else "coder-native-preflight-1"
            if args.native
            else "coder-tagged-negative-1"
            if args.negative
            else "coder-tagged-preflight-1"
        )
        / "facts.json",
        facts,
    )
    print(
        json.dumps(
            {
                "passed": facts["passed"],
                "probes": [
                    {
                        "action": p["action"],
                        "exact_match": p["exact_match"],
                        "error": p["error"],
                        "line_schema_conformance": p.get("line_schema_conformance"),
                    }
                    for p in facts["probes"]
                ],
            }
        )
    )
