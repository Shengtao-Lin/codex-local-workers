"""Isolated native Coder candidate with paired tool-call/result history."""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import native_coder_adapter as V1
from capability_fit import load_worker


def paired_history(messages, issued):
    """Translate only runtime results paired with a call this client issued.

    Compacted standalone evidence stays a user message. Reconstructed call IDs
    identify history pairs only; they never authorize execution or infer success.
    """
    result = []
    index = 0
    while index < len(messages):
        message = messages[index]
        raw = message.get("content")
        next_message = messages[index + 1] if index + 1 < len(messages) else {}
        observation = next_message.get("content", "")
        if (
            message.get("role") == "assistant"
            and isinstance(raw, str)
            and raw in issued
            and next_message.get("role") == "user"
            and isinstance(observation, str)
            and observation.startswith(("OBSERVATION\n", "REPAIR_REQUIRED\n"))
        ):
            action = json.loads(raw)
            call_id = (
                "call_"
                + hashlib.sha256((str(index) + "\n" + raw).encode("utf-8")).hexdigest()[
                    :24
                ]
            )
            result.extend(
                [
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": action["action"],
                                    "arguments": json.dumps(
                                        action["arguments"], ensure_ascii=False
                                    ),
                                },
                            }
                        ],
                    },
                    {"role": "tool", "tool_call_id": call_id, "content": observation},
                ]
            )
            index += 2
        else:
            result.append(copy.deepcopy(message))
            index += 1
    return result


def install(worker, packet):
    V1.install(worker, packet)
    original = worker.LMStudioClient.complete

    def complete(client, messages):
        issued = getattr(client, "_native_issued_actions", set())
        adapted = paired_history(messages, issued)
        allowed = client.action_schema["properties"]["action"]["enum"]
        # The underlying estimator counts serialized messages, including calls,
        # but not tool schemas. Reserve their estimated cost without dropping the
        # original safety margin; restore the configured value after this request.
        tools = V1.tools_for(packet, allowed)
        tool_tokens = (len(json.dumps(tools, ensure_ascii=False)) + 3) // 4
        margin = client.context_safety_margin
        client.context_safety_margin = margin + tool_tokens
        try:
            raw = original(client, adapted)
        finally:
            client.context_safety_margin = margin
            client.last_request_stats["native_schema_estimated_tokens"] = tool_tokens
            client.last_request_stats["native_history_tool_results"] = sum(
                message.get("role") == "tool" for message in adapted
            )
        issued.add(raw)
        client._native_issued_actions = issued
        client.last_request_stats["coder_transport_candidate"] = (
            "typed-native-paired-v2"
        )
        return raw

    worker.LMStudioClient.complete = complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    worker = load_worker(args.snapshot)
    packet = worker.resolve_inherited_packet(
        Path.cwd(), worker.load_json(Path(remaining[remaining.index("--packet") + 1]))
    )
    worker.validate_packet(packet)
    install(worker, packet)
    sys.argv = ["worker-runtime.py", *remaining]
    return worker.main()


if __name__ == "__main__":
    raise SystemExit(main())
