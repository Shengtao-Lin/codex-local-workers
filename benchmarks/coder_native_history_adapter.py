"""Diagnostic native history fidelity; no change to dispatch or safety gates."""

import copy
import json

import coder_native_block_adapter as block


def adapt_history(messages, observed_calls, *, repair_history=False):
    result = []
    index = 0
    while index < len(messages):
        message = messages[index]
        following = messages[index + 1] if index + 1 < len(messages) else {}
        raw = message.get("content")
        native = observed_calls.get(raw) if isinstance(raw, str) else None
        observation = following.get("content", "")
        prefix = "OBSERVATION\n"
        if (
            repair_history
            and native is not None
            and native.get("function", {}).get("name") == "VALIDATE"
            and isinstance(observation, str)
            and observation.startswith("REPAIR_REQUIRED\n")
        ):
            prefix = "REPAIR_REQUIRED\n"
        if (
            message.get("role") == "assistant"
            and native is not None
            and following.get("role") == "user"
            and isinstance(observation, str)
            and observation.startswith(prefix)
        ):
            # Only an actual returned native call with its actual adjacent observation.
            # Correlation IDs are transport-local, not evidence or execution identity.
            try:
                value = json.loads(observation.removeprefix(prefix))
            except ValueError:
                value = None
            if isinstance(value, dict):
                call = copy.deepcopy(native)
                call["id"] = "history_call_" + str(index)
                result.extend(
                    [
                        {"role": "assistant", "content": "", "tool_calls": [call]},
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": observation,
                        },
                    ]
                )
                index += 2
                continue
        result.append(copy.deepcopy(message))
        index += 1
    return result


def install(worker, packet, *, repair_history=False):
    block.install(worker, packet)
    original = worker.LMStudioClient.complete

    def complete(client, messages):
        calls = getattr(client, "diagnostic_history_calls", {})
        result = original(
            client, adapt_history(messages, calls, repair_history=repair_history)
        )
        native = getattr(client, "last_native_call", None)
        if isinstance(native, dict):
            action = json.loads(result)
            function = native.get("function", {})
            arguments = function.get("arguments")
            arguments = (
                json.loads(arguments) if isinstance(arguments, str) else arguments
            )
            if function.get("name") == action.get("action") and arguments == action.get(
                "arguments"
            ):
                calls[result] = copy.deepcopy(native)
                client.diagnostic_history_calls = calls
        client.last_request_stats["coder_transport_candidate"] = (
            "native-block-correlated-repair-history-v2"
            if repair_history
            else "native-block-correlated-history-v1"
        )
        return result

    worker.LMStudioClient.complete = complete


if __name__ == "__main__":
    block.native.install = install
    raise SystemExit(block.native.main())
