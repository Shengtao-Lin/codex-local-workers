"""Experimental native transport; never a production default or MCP executor."""

import hashlib
import json
import urllib.error
import urllib.request


def build_client(worker, base_url, model, *, reasoning, **kwargs):
    if reasoning not in {"off", "low", "medium", "high", "on"}:
        raise ValueError("unsupported native reasoning setting")
    if kwargs.get("native_tools") is not None or kwargs.get("structured_output", False):
        raise ValueError("native candidate requires plain JSON without provider tools")

    class NativeClient(worker.LMStudioClient):
        def complete(self, messages):
            systems, transcript = [], []
            for message in messages:
                if message.get("role") == "system":
                    systems.append(message["content"])
                elif message.get("role") in {"user", "assistant"}:
                    transcript.append(
                        {"role": message["role"], "content": message["content"]}
                    )
                else:
                    raise worker.WorkerError("unsupported transcript role")
            serialized = json.dumps(transcript, ensure_ascii=False)
            estimated = (len(serialized) + sum(map(len, systems)) + 3) // 4
            self.last_request_stats = {
                "model": self.model,
                "inference_backend": "lmstudio-native-candidate",
                "reasoning_requested": reasoning,
                "estimated_input_tokens": estimated,
                "context_length": self.context_length,
                "max_output_tokens": self.max_tokens,
            }
            if (
                self.context_length
                and estimated + self.max_tokens + self.context_safety_margin
                > self.context_length
            ):
                raise worker.ModelRequestError(
                    "input_too_large",
                    "native input exceeds context reserve",
                    dict(self.last_request_stats),
                )
            body = {
                "model": self.model,
                "input": serialized,
                "system_prompt": "\n\n".join(systems),
                "reasoning": reasoning,
                "store": False,
                "max_output_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "min_p": self.min_p,
                "repeat_penalty": self.repeat_penalty,
            }
            if self.context_length:
                body["context_length"] = self.context_length
            request = urllib.request.Request(
                self.base_url.removesuffix("/v1") + "/api/v1/chat",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    result = json.load(response)
            except urllib.error.HTTPError as error:
                self.last_request_stats["provider_status_code"] = error.code
                detail = error.read(2048)
                self.last_request_stats["provider_error_sha256"] = hashlib.sha256(
                    detail
                ).hexdigest()
                text = detail.decode("utf-8", errors="replace").lower()
                self.last_request_stats["provider_error_class"] = (
                    "channel_error"
                    if "channel error" in text
                    else "tool_parse_error"
                    if "unparsed" in text
                    else "unclassified"
                )
                raise worker.ModelRequestError(
                    "http_4xx" if 400 <= error.code < 500 else "http_5xx",
                    f"native request HTTP {error.code}",
                    dict(self.last_request_stats),
                ) from error
            except (urllib.error.URLError, OSError, ValueError) as error:
                raise worker.WorkerError(f"native request failed: {error}") from error
            if not isinstance(result, dict) or not isinstance(
                result.get("output"), list
            ):
                raise worker.WorkerError("native response has invalid shape")
            stats = result.get("stats")
            if not isinstance(stats, dict):
                raise worker.WorkerError("native response lacks token accounting")
            total = stats.get("total_output_tokens")
            if type(total) is not int or total < 0:
                raise worker.WorkerError(
                    "native response lacks valid output token count"
                )
            self.last_request_stats["native_stats"] = stats
            if total >= self.max_tokens:
                raise worker.ModelRequestError(
                    "output_token_limit",
                    "native output reserve reached; no partial action executed",
                    dict(self.last_request_stats),
                )
            outputs = result["output"]
            if any(
                not isinstance(item, dict)
                or item.get("type") not in {"message", "reasoning"}
                for item in outputs
            ):
                raise worker.WorkerError(
                    "native unexpected output or provider tool refused"
                )
            texts = [
                item.get("content") for item in outputs if item["type"] == "message"
            ]
            if len(texts) != 1 or not isinstance(texts[0], str) or not texts[0].strip():
                raise worker.WorkerError("native requires exactly one nonempty message")
            return texts[0].strip()

        def probe_structured_output(self):
            raw = self.complete(
                [
                    {
                        "role": "system",
                        "content": "Return exactly one JSON object, no Markdown.",
                    },
                    {
                        "role": "user",
                        "content": 'Return exactly {"action":"READ_FILE","arguments":{"path":"probe.py"}}. Do not execute it.',
                    },
                ]
            )
            try:
                response = json.loads(raw)
            except ValueError as error:
                raise worker.PreflightBlocked(
                    "native_plain_json_incompatible",
                    "native model did not return plain JSON",
                ) from error
            if response != {"action": "READ_FILE", "arguments": {"path": "probe.py"}}:
                raise worker.PreflightBlocked(
                    "native_plain_json_incompatible",
                    "native model did not return expected probe action",
                )
            return "native_plain_json_supported"

    return NativeClient(
        base_url,
        model,
        structured_output=False,
        **{key: value for key, value in kwargs.items() if key != "structured_output"},
    )
