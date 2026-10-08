"""Experimental named tools over the existing Coder runtime; no extra authority."""

import argparse
import copy
import json
import sys
from pathlib import Path

from capability_fit import load_worker


def obj(properties, required=()):
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def tools_for(packet, allowed):
    string = {"type": "string"}
    strings = {"type": "array", "items": string}
    positive = {"type": "integer", "minimum": 1}
    nullable_bool = {"type": ["boolean", "null"]}
    scope = obj({key: strings for key in ("read", "modify", "create")})
    check = obj(
        {
            "required_behavior_ids": strings,
            "required_order_confirmed": nullable_bool,
            "forbidden_orderings_absent": nullable_bool,
            "observable_scenario_ids": strings,
            "unrelated_changes": strings,
        },
        (
            "required_behavior_ids",
            "required_order_confirmed",
            "forbidden_orderings_absent",
            "observable_scenario_ids",
            "unrelated_changes",
        ),
    )
    schemas = {
        "READ_FILE": obj(
            {"path": string, "start_line": positive, "end_line": positive}, ("path",)
        ),
        "SEARCH": obj(
            {
                "query": string,
                "path": string,
                "glob": string,
                "mode": {"type": "string", "enum": ["literal", "regex"]},
                "case_sensitive": {"type": "boolean"},
                "max_results": positive,
            },
            ("query",),
        ),
        "SAFE_CREATE": obj({"path": string, "content": string}, ("path", "content")),
        "SAFE_REPLACE": obj(
            {key: string for key in ("path", "expected_sha256", "find", "replace")},
            ("path", "expected_sha256", "find", "replace"),
        ),
        "SAFE_REPLACE_LINE": obj(
            {
                "path": string,
                "expected_sha256": string,
                "line": positive,
                "replacement": {"type": "string", "pattern": "^[^\\r\\n]*$"},
            },
            ("path", "expected_sha256", "line", "replacement"),
        ),
        "VALIDATE": obj(
            {
                "phase": {"type": "string", "enum": ["check", "final"]},
                "contract_check": check,
            },
            ("contract_check",) if packet.get("contract_check_required") else (),
        ),
        "FINISH_SUCCESS": obj(
            {"summary": strings, "remaining_uncertainty": strings},
            ("summary", "remaining_uncertainty"),
        ),
        "FINISH_FAILED": obj(
            {"summary": strings, "reason": string, "remaining_uncertainty": strings},
            ("summary", "reason", "remaining_uncertainty"),
        ),
        "FINISH_BLOCKED": obj(
            {
                "reason_code": string,
                "reason": string,
                "requested_scope": scope,
                "evidence_refs": strings,
                "proposed_next_step": string,
            },
            ("reason_code", "reason"),
        ),
        "REQUEST_CONTRACT_REVISION": obj(
            {
                "issue_type": {
                    "type": "string",
                    "enum": [
                        "contract_conflict",
                        "stale_test_suspected",
                        "scope_gap",
                        "missing_context",
                    ],
                },
                "reason": string,
                "contract_ids": strings,
                "source_evidence": {
                    "type": "array",
                    "items": obj(
                        {"path": string, "line": positive, "quote": string},
                        ("path", "line", "quote"),
                    ),
                },
                "validation_evidence_refs": strings,
                "requested_scope": scope,
                "proposed_next_step": string,
            },
            ("issue_type", "reason"),
        ),
    }
    if (
        not allowed
        or len(allowed) != len(set(allowed))
        or set(allowed) - schemas.keys()
    ):
        raise ValueError("unknown or empty runtime action allowlist")
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"Execute the bounded {name} action described by the system contract. Runtime scope, hashes, evidence and validation remain authoritative.",
                "parameters": copy.deepcopy(schemas[name]),
            },
        }
        for name in allowed
    ]


def install(worker, packet):
    original = worker.LMStudioClient.complete

    def complete(client, messages):
        allowed = client.action_schema["properties"]["action"]["enum"]
        client.native_tools = tools_for(packet, allowed)
        client.native_tool_choice = "required"
        adapted = copy.deepcopy(messages)
        for message in adapted:
            if message.get(
                "role"
            ) == "system" and "Available actions and their arguments:" in message.get(
                "content", ""
            ):
                _, body = message["content"].split(
                    "Available actions and their arguments:", 1
                )
                message["content"] = (
                    "You are a bounded local implementation worker. The current packet is authoritative. "
                    "Call exactly one of the provided native functions per turn with its defined arguments. "
                    "Do not emit a textual JSON action envelope, Markdown or prose. "
                    "JSON action examples below illustrate argument meaning; use the corresponding native function.\n"
                    "Available actions and their arguments:" + body
                )
        result = original(client, adapted)
        action = json.loads(result)
        if (
            client.last_request_stats.get("native_tool_call") not in allowed
            or action.get("action") not in allowed
        ):
            raise worker.WorkerError(
                "native Coder candidate requires one currently allowed explicit tool call"
            )
        client.last_request_stats["coder_transport_candidate"] = "typed-native-v1"
        return result

    worker.LMStudioClient.complete = complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    packet_arg = remaining[remaining.index("--packet") + 1]
    worker = load_worker(args.snapshot)
    packet = worker.resolve_inherited_packet(
        Path.cwd(), worker.load_json(Path(packet_arg))
    )
    worker.validate_packet(packet)
    install(worker, packet)
    sys.argv = ["worker-runtime.py", *remaining]
    return worker.main()


if __name__ == "__main__":
    raise SystemExit(main())
