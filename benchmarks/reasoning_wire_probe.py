"""Bounded synthetic transport probe; never save model reasoning text."""

import hashlib
import json
import queue
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/reasoning-wire-20261020-1"
BASE = "http://127.0.0.1:12345"
MODEL = "meta/muse-glimmer"
LMS = "C:/Users/Lin/.lmstudio/bin/lms.exe"
TOOL = {
    "type": "function",
    "function": {
        "name": "REPORT_READY",
        "description": "Report protocol readiness.",
        "parameters": {
            "type": "object",
            "properties": {"ready": {"type": "boolean", "const": True}},
            "required": ["ready"],
            "additionalProperties": False,
        },
    },
}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def probe(used, observed, batch=BATCH):
    BATCH = batch.resolve()
    if not 0 <= used < 40 or not 0 <= time.time() - observed <= 120:
        raise ValueError("Fresh weekly observation required")
    with urllib.request.urlopen(BASE + "/api/v1/models", timeout=30) as response:
        models = json.load(response)["models"]
    loaded = [m for m in models if m.get("loaded_instances")]
    if len(loaded) != 1 or loaded[0]["key"] != MODEL:
        raise ValueError("Only current Muse may be resident for this probe")
    S.save(
        BATCH / "registration.json",
        {
            "weekly_used": used,
            "weekly_stop": 40,
            "model": MODEL,
            "probes": [
                "chat-default",
                "chat-low",
                "responses-low only if chat-low not verified",
            ],
            "maximum_requests": 3,
            "tokens_per_request": 512,
            "seconds_per_request": 180,
            "purpose": "Synthetic readiness only; rendered-input reasoning level observation, no semantic review/acceptance or machine setting changes",
            "loaded_model": loaded[0],
            "driver_sha256": S.sha(__file__),
        },
    )
    records = queue.Queue()
    log_counts = {"lines": 0, "events": 0}
    process = subprocess.Popen(
        [LMS, "log", "stream", "--json", "--source", "model", "--filter", "input"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    def reader():
        buffer = ""
        for line in process.stdout:
            log_counts["lines"] += 1
            if not buffer and not line.lstrip().startswith(("{", "[")):
                continue
            buffer += line
            try:
                records.put(json.loads(buffer))
                log_counts["events"] += 1
                buffer = ""
            except json.JSONDecodeError:
                if len(buffer) > 1_000_000:
                    buffer = ""

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    time.sleep(0.5)
    results = []
    try:
        for name in ("chat-default", "chat-low", "responses-low"):
            if name == "responses-low" and any(
                "low" in item for item in results[-1]["rendered_reasoning"]
            ):
                break
            marker = "WIRE_PROBE_" + name
            messages = [
                {
                    "role": "system",
                    "content": "Use the provided REPORT_READY function to report readiness.",
                },
                {"role": "user", "content": marker + ": Report ready true."},
            ]
            body = {
                "model": MODEL,
                "messages": messages,
                "tools": [TOOL],
                "tool_choice": "required",
                "parallel_tool_calls": False,
                "max_tokens": 512,
                "temperature": 0,
                "top_p": 0.9,
                "top_k": 40,
                "min_p": 0,
                "repeat_penalty": 1,
            }
            endpoint = "/v1/chat/completions"
            if name == "chat-low":
                body["reasoning_effort"] = "low"
            elif name == "responses-low":
                endpoint = "/v1/responses"
                body = {
                    "model": MODEL,
                    "input": messages,
                    "reasoning": {"effort": "low"},
                    "tools": [{"type": "function", **TOOL["function"]}],
                    "tool_choice": "required",
                    "parallel_tool_calls": False,
                    "max_output_tokens": 512,
                    "temperature": 0,
                    "top_p": 0.9,
                    "store": False,
                }
            S.save(BATCH / name / "request.json", body)
            start = time.monotonic()
            request = urllib.request.Request(
                BASE + endpoint,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    raw = response.read()
                result = json.loads(raw)
                message = (result.get("choices") or [{}])[0].get("message", {})
                summary = {
                    "finish_reason": (result.get("choices") or [{}])[0].get(
                        "finish_reason", result.get("status")
                    ),
                    "usage": result.get("usage"),
                    "reasoning_chars": sum(
                        len(message.get(key) or "")
                        for key in ("reasoning", "reasoning_content")
                    ),
                    "tool_calls": [
                        {
                            "name": t.get("function", {}).get("name"),
                            "arguments": t.get("function", {}).get("arguments"),
                        }
                        for t in message.get("tool_calls", [])
                    ],
                    "output_types": [
                        item.get("type") for item in result.get("output", [])
                    ],
                    "response_sha256": hashlib.sha256(raw).hexdigest(),
                }
            except urllib.error.HTTPError as exc:
                summary = {
                    "http_error": exc.code,
                    "error": exc.read().decode("utf-8")[:1000],
                }
            time.sleep(0.2)
            reasoning = []
            input_excerpts = []
            while not records.empty():
                event = records.get_nowait()
                texts = list(strings(event))
                if any(marker in text for text in texts):
                    for text in texts:
                        reasoning.extend(
                            re.findall(
                                r"(?i)(?:reasoning|effort)[^\n]{0,64}\b(?:xhigh|high|medium|low|none|off)\b",
                                text,
                            )
                        )
                        if marker in text:
                            input_excerpts.append(text[:1500])
            row = {
                "name": name,
                "seconds": time.monotonic() - start,
                "rendered_reasoning": reasoning,
                "synthetic_input_excerpts": input_excerpts,
                **summary,
            }
            results.append(row)
            S.save(BATCH / name / "result.json", row)
            print(
                name,
                reasoning,
                summary.get("finish_reason", summary.get("http_error")),
                flush=True,
            )
    finally:
        process.terminate()
        process.wait(timeout=10)
        thread.join(timeout=2)
    S.save(
        BATCH / "decision.json",
        {
            "results": results,
            "semantic_acceptance_credit": 0,
            "log_counts": log_counts,
            "conclusion": "Only rendered-prompt configuration evidence is authoritative; small probe output length is not proof of review quality",
        },
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--observed-at", type=float, required=True)
    args = parser.parse_args()
    probe(args.weekly_used, args.observed_at)
