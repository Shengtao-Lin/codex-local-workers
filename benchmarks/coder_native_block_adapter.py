"""Benchmark-only native BLOCK transport over unchanged trusted Coder gates."""

import json

import native_coder_adapter as native

original_tools = native.tools_for
original_install = native.install


def block_tools(packet, allowed):
    return original_tools(
        packet, [action for action in allowed if action != "SAFE_REPLACE_LINE"]
    )


def install(worker, packet):
    native.tools_for = block_tools
    original_install(worker, packet)
    previous = worker.LMStudioClient.complete

    def complete(client, messages):
        adapted = [dict(message) for message in messages]
        for message in adapted:
            if message.get("role") == "system":
                message["content"] += (
                    "\nOnly currently advertised native functions are available. SAFE_REPLACE_LINE is unavailable; ignore examples for it. Use current exact smaller SAFE_REPLACE blocks after locating a mismatch."
                )
        result = previous(client, adapted)
        advertised = {tool["function"]["name"] for tool in client.native_tools}
        if (
            client.last_request_stats.get("native_tool_call") not in advertised
            or json.loads(result).get("action") not in advertised
        ):
            raise worker.WorkerError(
                "native BLOCK candidate requires one currently advertised function"
            )
        client.last_request_stats["coder_transport_candidate"] = "native-block-only-v2"
        return result

    worker.LMStudioClient.complete = complete


if __name__ == "__main__":
    native.install = install
    raise SystemExit(native.main())
