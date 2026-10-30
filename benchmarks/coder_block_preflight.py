"""Non-executing native BLOCK compatibility; LINE deliberately not advertised."""

import argparse
import json

from capability_fit import WORK, load_worker, write
from inherited_context_recovery import read
from layer_isolation import verify_hashes
from native_coder_adapter import tools_for

BASE = WORK / "coder-block-preflight-2"
SNAPSHOT = WORK / "tool-reviewer-runtime-5"
ALLOWED = ["READ_FILE", "SAFE_REPLACE", "VALIDATE", "FINISH_SUCCESS", "FINISH_BLOCKED"]
PROBES = (
    ("READ_FILE", {"path": "src/example.py", "start_line": 1, "end_line": 2}),
    (
        "SAFE_REPLACE",
        {
            "path": "src/example.py",
            "expected_sha256": "b" * 64,
            "find": "def value():\n    return 1",
            "replace": "def value():\n    return 2",
        },
    ),
    (
        "VALIDATE",
        {
            "phase": "final",
            "contract_check": {
                "required_behavior_ids": ["value"],
                "required_order_confirmed": True,
                "forbidden_orderings_absent": True,
                "observable_scenario_ids": ["normal"],
                "unrelated_changes": [],
            },
        },
    ),
    (
        "FINISH_SUCCESS",
        {"summary": ["Compatibility probe only"], "remaining_uncertainty": []},
    ),
)


def exact_native_action(returned, action, arguments, stats):
    return (
        returned.get("action") == action
        and returned.get("arguments") == arguments
        and returned.get("_warnings") == []
        and stats.get("native_tool_call") == action
        and stats.get("response_parts", {}).get("tool_calls", {}).get("count") == 1
    )


def register():
    write(
        BASE / "registration.json",
        {
            "weekly_ceiling": 23,
            "runtime": str(SNAPSHOT),
            "actions": ALLOWED,
            "axis": "Native tool call with BLOCK only, excludes previously truncating LINE schema",
            "model": "Unchanged Qwen/config/context and single model residency",
            "actions_execute": False,
            "credit": "Compatibility only, no implementation or validation success",
            "failure_policy": "Stop at first failed positive probe, no identical retry",
            "negative": "A requested LINE is unavailable; return bounded FINISH_BLOCKED without fabricated edit",
        },
    )


def run():
    if not (BASE / "registration.json").exists():
        raise ValueError("register first")
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    worker = load_worker(SNAPSHOT)
    config = read(WORK / "tool-awaitable-5/fresh-1/.agent/config.json")
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
        structured_output=False,
        native_tools=tools_for({"contract_check_required": True}, ALLOWED),
    )
    client.native_tool_choice = "required"
    facts = {"actions_execute": False, "probes": [], "passed": False}
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        for action, arguments in PROBES:
            try:
                raw = client.complete(
                    [
                        {
                            "role": "system",
                            "content": "Non-executing compatibility test. Use exactly one provided native function. Do not type a JSON envelope or prose.",
                        },
                        {
                            "role": "user",
                            "content": "Return exactly the following function and arguments; no action will execute: "
                            + json.dumps({"action": action, "arguments": arguments}),
                        },
                    ]
                )
                returned = worker.parse_action(raw)
                passed = exact_native_action(
                    returned, action, arguments, client.last_request_stats
                )
                item = {
                    "action": action,
                    "passed": passed,
                    "returned": returned,
                    "stats": dict(client.last_request_stats),
                }
            except Exception as exc:  # noqa: BLE001 -- immutable backend failure record
                item = {
                    "action": action,
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "stats": dict(client.last_request_stats),
                }
            facts["probes"].append(item)
            write(BASE / f"probe-{len(facts['probes'])}.json", item)
            if not item["passed"]:
                break
        if len(facts["probes"]) == len(PROBES) and all(
            item["passed"] for item in facts["probes"]
        ):
            try:
                raw = client.complete(
                    [
                        {
                            "role": "system",
                            "content": "Use exactly one available native function. Never invent a missing tool or hash.",
                        },
                        {
                            "role": "user",
                            "content": "SAFE_REPLACE_LINE is unavailable. Do not read or edit. Return FINISH_BLOCKED with reason_code=unsupported_action and reason=LINE unavailable.",
                        },
                    ]
                )
                returned = worker.parse_action(raw)
                arguments = returned["arguments"]
                negative = {
                    "passed": returned["action"] == "FINISH_BLOCKED"
                    and client.last_request_stats.get("native_tool_call")
                    == "FINISH_BLOCKED"
                    and arguments.get("reason_code") == "unsupported_action"
                    and arguments.get("reason") == "LINE unavailable",
                    "returned": returned,
                    "stats": dict(client.last_request_stats),
                }
                negative["passed"] = (
                    negative["passed"]
                    and returned.get("_warnings") == []
                    and client.last_request_stats.get("response_parts", {})
                    .get("tool_calls", {})
                    .get("count")
                    == 1
                )
            except Exception as exc:  # noqa: BLE001 -- compatibility evidence
                negative = {
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "stats": dict(client.last_request_stats),
                }
            facts["negative"] = negative
            facts["passed"] = negative["passed"]
    write(BASE / "facts.json", facts)
    print(json.dumps(facts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "run"))
    args = parser.parse_args()
    register() if args.action == "register" else run()
