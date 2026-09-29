"""Read-only LM Studio probe for Reviewer native tool-call parsing."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:12345/v1")
    parser.add_argument("--model", default="meta/muse-glimmer")
    parser.add_argument("--with-tools", action="store_true")
    args = parser.parse_args()
    payload: dict = {
        "model": args.model,
        "messages": [
            {
                "role": "system",
                "content": "Read the named file using READ_FILE. Request exactly one action.",
            },
            {"role": "user", "content": "Read src/slug.py now."},
        ],
        "temperature": 0.1,
        "max_tokens": 256,
    }
    if args.with_tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": "READ_FILE",
                    "description": "Request a bounded read of a repository file.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            }
        ]
        payload["tool_choice"] = "auto"
    request = urllib.request.Request(
        args.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        print(
            json.dumps(
                {
                    "http_status": exc.code,
                    "body": exc.read().decode("utf-8", "replace")[-600:],
                }
            )
        )
        return 1
    choice = result["choices"][0]
    message = choice.get("message", {})
    print(
        json.dumps(
            {
                "finish_reason": choice.get("finish_reason"),
                "content": message.get("content"),
                "tool_calls": message.get("tool_calls"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
