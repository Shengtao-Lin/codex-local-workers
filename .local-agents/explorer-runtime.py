from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
from pathlib import Path, PureWindowsPath
from typing import Any, Protocol

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
EXCLUDED_PARTS = {
    ".agent",
    ".git",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}


def has_path_line_citation(item: str, path: str) -> bool:
    normalized = unicodedata.normalize("NFKC", item)
    return any(
        re.search(rf"(?<![\w./]){re.escape(path)}(?![\w./])", clause)
        and re.search(r"\blines?\s*\d+|:\d+\b", clause, re.I)
        for clause in re.split(r"(?<=[.!?])\s+|\n", normalized)
    )


def _load_evidence_cache() -> Any:
    spec = importlib.util.spec_from_file_location(
        "local_explorer_evidence_cache", SCRIPT_DIR / "evidence-cache.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load evidence-cache.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EVIDENCE_CACHE = _load_evidence_cache()

EXPLORER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "LIST_FILES",
            "description": "List repository files under a relative path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "SEARCH",
            "description": "Search repository text using a regular expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                    "mode": {"type": "string", "enum": ["literal", "regex"]},
                    "case_sensitive": {"type": "boolean"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "TRACE",
            "description": "Trace Python definitions and one-hop callers/callees with file/line evidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "READ_FILE",
            "description": "Read a bounded line range from a repository text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "FINISH_SUCCESS",
            "description": (
                "Investigation completed with evidence, including when a defect was found. "
                "This does not mean the investigated code passes its tests."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "relevant_files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                            "required": ["path", "reason"],
                        },
                    },
                    "call_flow": {"type": "array", "items": {"type": "string"}},
                    "findings": {"type": "array", "items": {"type": "string"}},
                    "relevant_tests": {"type": "array", "items": {"type": "string"}},
                    "uncertainties": {"type": "array", "items": {"type": "string"}},
                    "citations": {
                        "type": "array",
                        "description": "Observed READ_FILE lines supporting source/test claims.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "line": {"type": "integer"},
                                "claim": {"type": "string", "minLength": 1},
                            },
                            "required": ["path", "line", "claim"],
                        },
                    },
                },
                "required": [
                    "relevant_files",
                    "call_flow",
                    "findings",
                    "relevant_tests",
                    "uncertainties",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "FINISH_FAILED",
            "description": (
                "Investigation could not produce reliable findings (missing evidence, "
                "inaccessible scope, or exhausted budget). Finding a code bug is NOT failure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
                    "uncertainties": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["summary", "reason", "uncertainties"],
            },
        },
    },
]


class ExplorerError(RuntimeError):
    pass


class ExplorerPreflightBlocked(ExplorerError):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class ExplorerModelRequestError(ExplorerError):
    def __init__(self, reason_code: str, message: str, diagnostics: dict[str, Any]) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.diagnostics = diagnostics


class ExplorerInterrupted(ExplorerError):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class ModelClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


class LMStudioClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int,
        reasoning_effort: str = "low",
        context_length: int | None = None,
        context_safety_margin: int = 1024,
        max_output_tokens: int = 2048,
        required_tool_max_tokens: int = 1536,
        temperature: float = 0.1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.url = self.base_url + "/chat/completions"
        self.model = model
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not 0 <= temperature <= 2
        ):
            raise ExplorerPreflightBlocked(
                "invalid_config", "explorer_temperature must be between 0 and 2"
            )
        self.temperature = float(temperature)
        self.empty_response_repairs = 0
        self.context_length = context_length
        self.context_safety_margin = max(0, context_safety_margin)
        if max_output_tokens < 1 or required_tool_max_tokens < 1:
            raise ExplorerError("Explorer output token limits must be positive")
        self.max_output_tokens = max_output_tokens
        self.required_tool_max_tokens = required_tool_max_tokens
        self.last_request_stats: dict[str, Any] = {}
        self.native_tools = EXPLORER_TOOLS
        self.native_tool_choice = "auto"

    @staticmethod
    def _prompt_sections(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
        sections = []
        for index, message in enumerate(messages, 1):
            content = str(message.get("content", ""))
            first_line = content.splitlines()[0][:80] if content else "empty"
            label = (
                first_line
                if re.fullmatch(r"[A-Z][A-Z0-9_ -]{2,79}", first_line)
                else str(message.get("role", "message"))
            )
            sections.append(
                {
                    "section": f"{index}:{label}",
                    "estimated_tokens": max(1, (len(content) + 3) // 4),
                    "bytes": len(content.encode("utf-8")),
                }
            )
        return sorted(sections, key=lambda item: item["estimated_tokens"], reverse=True)

    @staticmethod
    def _merge_adjacent_roles(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        merged: list[dict[str, str]] = []
        for message in messages:
            if merged and merged[-1].get("role") == message.get("role"):
                merged[-1] = {
                    "role": str(message["role"]),
                    "content": merged[-1]["content"] + "\n\n" + message["content"],
                }
            else:
                merged.append(dict(message))
        return merged

    def preflight(self) -> None:
        request = urllib.request.Request(self.base_url + "/models", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ExplorerPreflightBlocked(
                "lmstudio_unavailable", f"LM Studio preflight failed: {exc}"
            ) from exc
        items = payload.get("data", payload.get("models", [])) if isinstance(payload, dict) else []
        model_ids = {item.get("id") if isinstance(item, dict) else item for item in items}
        if self.model not in model_ids:
            raise ExplorerPreflightBlocked(
                "model_unavailable",
                f"configured Explorer model is not available: {self.model}",
            )

    def _post(
        self, messages: list[dict[str, str]], *, require_tool: bool = False
    ) -> dict[str, Any]:
        max_tokens = self.required_tool_max_tokens if require_tool else self.max_output_tokens
        request_payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "reasoning_effort": self.reasoning_effort,
            "tools": self.native_tools,
            "tool_choice": "required" if require_tool else self.native_tool_choice,
        }
        body = json.dumps(request_payload).encode("utf-8")
        message_chars = len(json.dumps(messages, ensure_ascii=False))
        estimated_input_tokens = max(1, (message_chars + 3) // 4)
        self.last_request_stats = {
            "model": self.model,
            "message_chars": message_chars,
            "request_bytes": len(body),
            "estimated_input_tokens": estimated_input_tokens,
            "max_output_tokens": max_tokens,
            "context_length": self.context_length,
            "context_safety_margin": self.context_safety_margin,
            "largest_prompt_sections": self._prompt_sections(messages)[:3],
        }
        if self.context_length:
            available_input_tokens = max(
                0, self.context_length - max_tokens - self.context_safety_margin
            )
            self.last_request_stats["available_input_tokens"] = available_input_tokens
            self.last_request_stats["estimated_remaining_tokens"] = (
                self.context_length - estimated_input_tokens - max_tokens
            )
            self.last_request_stats["estimated_context_utilization"] = round(
                (estimated_input_tokens + max_tokens) / self.context_length, 4
            )
            if estimated_input_tokens > available_input_tokens:
                self.last_request_stats["rejection_reason"] = "input_too_large"
                raise ExplorerModelRequestError(
                    "input_too_large",
                    "LM Studio request rejected locally: estimated input exceeds configured "
                    "context after output reserve and safety margin",
                    dict(self.last_request_stats),
                )
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read(4000).decode("utf-8", errors="replace")
            except OSError:
                detail = ""
            response_body = detail[:4000]
            reason_code = "http_4xx" if 400 <= exc.code < 500 else "http_5xx"
            self.last_request_stats.update(
                {
                    "provider_status_code": exc.code,
                    "provider_response_body": response_body,
                    "rejection_reason": reason_code,
                }
            )
            raise ExplorerModelRequestError(
                reason_code,
                f"LM Studio request failed: HTTP {exc.code}: {response_body}",
                dict(self.last_request_stats),
            ) from exc
        except TimeoutError as exc:
            self.last_request_stats["rejection_reason"] = "model_request_timeout"
            raise ExplorerModelRequestError(
                "model_request_timeout",
                f"LM Studio request failed: {exc}",
                dict(self.last_request_stats),
            ) from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise ExplorerError(f"LM Studio request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise ExplorerError("LM Studio returned a non-object response")
        usage = payload.get("usage")
        if isinstance(usage, dict):
            reported = usage.get("prompt_tokens", usage.get("input_tokens"))
            if isinstance(reported, int) and reported >= 0:
                self.last_request_stats["reported_input_tokens"] = reported
                if self.context_length:
                    self.last_request_stats["reported_remaining_tokens"] = (
                        self.context_length - reported - max_tokens
                    )
                    self.last_request_stats["reported_context_utilization"] = round(
                        (reported + max_tokens) / self.context_length, 4
                    )
        return payload

    @staticmethod
    def _embedded_action(text: str) -> str | None:
        decoder = json.JSONDecoder()
        for index, character in enumerate(text):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(text[index:])
            except ValueError:
                continue
            if isinstance(value, dict) and isinstance(value.get("action"), str):
                return json.dumps(value, ensure_ascii=False)
        return None

    def complete(self, messages: list[dict[str, str]]) -> str:
        request_messages = messages
        last_diagnostic = ""
        last_finish_reason: str | None = None
        for attempt in range(2):
            try:
                payload = self._post(request_messages)
            except ExplorerModelRequestError as exc:
                if (
                    attempt == 0
                    and exc.reason_code == "http_4xx"
                    and "roles must alternate user and assistant" in str(exc)
                ):
                    merged = self._merge_adjacent_roles(request_messages)
                    if merged == request_messages:
                        raise
                    request_messages = merged
                    payload = self._post(request_messages)
                    self.last_request_stats["role_alternation_retry_attempts"] = 1
                elif attempt == 0 and exc.reason_code == "http_4xx" and "peg-native" in str(exc):
                    # The server rejected generated tool-recipient syntax, not
                    # the task. Change the request shape for one bounded retry.
                    payload = self._post(request_messages, require_tool=True)
                    self.last_request_stats["peg_native_retry_attempts"] = 1
                else:
                    raise
            try:
                choice = payload["choices"][0]
                message = choice["message"]
                content = message.get("content")
            except (KeyError, IndexError, TypeError) as exc:
                raise ExplorerError("LM Studio returned an unexpected response shape") from exc
            self.last_request_stats["finish_reason"] = choice.get("finish_reason")
            usage = payload.get("usage")
            if isinstance(usage, dict):
                self.last_request_stats["response_usage"] = {
                    key: usage[key]
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                    if type(usage.get(key)) is int and usage[key] >= 0
                }
            if choice.get("finish_reason") == "length":
                self.last_request_stats["rejection_reason"] = "output_token_limit"
                raise ExplorerModelRequestError(
                    "output_token_limit",
                    "LM Studio truncated the Explorer response at its output-token limit; "
                    "no partial action was executed",
                    dict(self.last_request_stats),
                )
            if isinstance(content, str) and content.strip():
                return content.strip()
            tool_calls = message.get("tool_calls", []) if isinstance(message, dict) else []
            if isinstance(tool_calls, list) and len(tool_calls) == 1:
                function = (
                    tool_calls[0].get("function", {}) if isinstance(tool_calls[0], dict) else {}
                )
                name = function.get("name")
                arguments = function.get("arguments", "{}")
                if isinstance(name, str) and isinstance(arguments, (str, dict)):
                    if isinstance(arguments, dict):
                        parsed_arguments = arguments
                    else:
                        try:
                            parsed_arguments = json.loads(arguments)
                        except ValueError as exc:
                            raise ExplorerError(
                                "LM Studio tool-call arguments are invalid JSON"
                            ) from exc
                    if isinstance(parsed_arguments, dict):
                        return json.dumps(
                            {"action": name, "arguments": parsed_arguments}, ensure_ascii=False
                        )
            reasoning = message.get("reasoning", "") if isinstance(message, dict) else ""
            if isinstance(reasoning, str):
                embedded = self._embedded_action(reasoning)
                if embedded is not None:
                    return embedded
                if reasoning.lstrip().startswith("<|channel|>"):
                    return reasoning.strip()
            last_diagnostic = (
                f"finish_reason={choice.get('finish_reason')!r}, "
                f"reasoning_chars={len(reasoning) if isinstance(reasoning, str) else 0}, "
                f"tool_calls={len(tool_calls) if isinstance(tool_calls, list) else 0}, "
                f"reasoning_excerpt={reasoning[:200]!r}"
            )
            last_finish_reason = choice.get("finish_reason")
            if attempt == 0:
                self.empty_response_repairs += 1
                request_messages = self._merge_adjacent_roles(
                    [
                        *request_messages,
                        {
                            "role": "user",
                            "content": (
                                "Your previous response had no executable action. Output exactly one "
                                "JSON action object now, with no reasoning or prose."
                            ),
                        },
                    ]
                )
                continue
            break
        if last_finish_reason == "length":
            self.last_request_stats["rejection_reason"] = "output_token_limit"
            raise ExplorerModelRequestError(
                "output_token_limit",
                "LM Studio exhausted the configured Explorer output-token reserve "
                f"before producing one action ({last_diagnostic})",
                dict(self.last_request_stats),
            )
        raise ExplorerError(
            f"LM Studio returned an empty assistant message after one repair ({last_diagnostic})"
        )


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ExplorerError(f"could not load JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExplorerError(f"JSON root must be an object: {path}")
    return value


def require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExplorerError(f"{name} must be a non-empty string")
    return value.strip()


def string_list(value: Any, name: str) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ExplorerError(f"{name} must be a string or an array of non-empty strings")
    normalized = [item.strip() for item in value]
    if any(not item for item in normalized):
        raise ExplorerError(f"{name} contains an empty string")
    return normalized


def normalize_relative_path(raw_path: str, *, allow_dot: bool = False) -> str:
    if allow_dot and raw_path == ".":
        return "."
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ExplorerError("path is required")
    candidate = raw_path.strip().replace("\\", "/")
    while candidate.startswith("./"):
        candidate = candidate[2:]
    windows_path = PureWindowsPath(candidate)
    if windows_path.is_absolute() or windows_path.drive or candidate.startswith("/"):
        raise ExplorerError(f"absolute paths are not allowed: {raw_path}")
    parts = candidate.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ExplorerError(f"path must be normalized and repository-relative: {raw_path}")
    return "/".join(parts)


def is_reparse_point(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def parse_action(raw: str) -> dict[str, Any]:
    harmony_finish = re.fullmatch(
        r"<\|channel\|>final\s+to=([A-Za-z0-9_.-]+)"
        r"<\|channel\|>commentary\s+(?:<\|constrain\|>json|code)"
        r"<\|message\|>(\{.*\})\s*",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if harmony_finish:
        tool_name = harmony_finish.group(1)
        try:
            arguments = json.loads(harmony_finish.group(2))
        except ValueError as exc:
            raise ExplorerError(f"Harmony finish arguments are invalid JSON: {exc}") from exc
        if not isinstance(arguments, dict):
            raise ExplorerError("Harmony finish arguments must be an object")
        mapping = {
            "repo_browser.finish_success": "FINISH_SUCCESS",
            "repo_browser.finish_failed": "FINISH_FAILED",
        }
        return {
            "action": mapping.get(tool_name, tool_name),
            "arguments": arguments,
            "warnings": [],
        }
    harmony = re.fullmatch(
        r"<\|channel\|>commentary\s+to=([A-Za-z0-9_.-]+)\s+"
        r"(?:<\|constrain\|>json|code)<\|message\|>(\{.*\})\s*",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if harmony:
        tool_name = harmony.group(1)
        try:
            arguments = json.loads(harmony.group(2))
        except ValueError as exc:
            raise ExplorerError(f"Harmony tool arguments are invalid JSON: {exc}") from exc
        if not isinstance(arguments, dict):
            raise ExplorerError("Harmony tool arguments must be an object")
        mapping = {
            "repo_browser.list_files": "LIST_FILES",
            "repo_browser.search": "SEARCH",
            "repo_browser.trace": "TRACE",
            "repo_browser.read_file": "READ_FILE",
            "repo_browser.finish_success": "FINISH_SUCCESS",
            "repo_browser.finish_failed": "FINISH_FAILED",
        }
        return {
            "action": mapping.get(tool_name, tool_name),
            "arguments": arguments,
            "warnings": [],
        }
    harmony_final = re.fullmatch(
        r"<\|channel\|>final\s+(?:<\|constrain\|>json|code)"
        r"<\|message\|>(.*)",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if harmony_final:
        raw = harmony_final.group(1).strip()
    decoder = json.JSONDecoder()
    remaining = raw.lstrip()
    try:
        action, offset = decoder.raw_decode(remaining)
    except ValueError as exc:
        raise ExplorerError(f"response does not begin with a JSON object: {exc}") from exc
    if not isinstance(action, dict) or not isinstance(action.get("action"), str):
        raise ExplorerError("action response must be a JSON object with string field 'action'")
    warnings: list[str] = []
    trailing = remaining[offset:].strip()
    while trailing:
        try:
            extra, extra_offset = decoder.raw_decode(trailing)
        except ValueError as exc:
            raise ExplorerError(f"non-JSON trailing output is not allowed: {exc}") from exc
        if not isinstance(extra, dict):
            raise ExplorerError("every trailing JSON value must be an action object")
        warnings.append("ignored an additional action from the same model turn")
        trailing = trailing[extra_offset:].strip()
    if "arguments" in action:
        if set(action) != {"action", "arguments"} or not isinstance(action["arguments"], dict):
            raise ExplorerError(
                "nested action must contain exactly 'action' and object 'arguments'"
            )
        arguments = action["arguments"]
    else:
        arguments = {key: value for key, value in action.items() if key != "action"}
    return {"action": action["action"], "arguments": arguments, "warnings": warnings}


class ExplorerRuntime:
    def __init__(
        self,
        repo_root: Path,
        task: str,
        config: dict[str, Any],
        client: ModelClient,
        task_id: str | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.task = require_string(task, "task")
        if task_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", task_id):
            raise ExplorerPreflightBlocked("invalid_task_id", "task_id is not a safe identifier")
        self.config = config
        self.client = client
        self.mode = config.get("explorer_mode", "investigate")
        if not isinstance(self.mode, str) or self.mode not in {"investigate", "locate"}:
            raise ExplorerPreflightBlocked("invalid_config", "unknown explorer_mode")
        self.cache_task = self.task if self.mode == "investigate" else "LOCATE_V1\n" + self.task
        if self.mode == "locate" and hasattr(client, "native_tools"):
            client.native_tools = [
                self.localization_tool() if tool["function"]["name"] == "FINISH_SUCCESS" else tool
                for tool in EXPLORER_TOOLS
            ]
        self.task_id = task_id
        self.max_turns = int(config.get("max_explorer_turns", 16))
        self.max_file_reads = int(config.get("max_explorer_file_reads", 8))
        self.max_searches = int(config.get("max_explorer_searches", 10))
        self.max_output = int(config.get("max_tool_output_chars", 16000))
        self.invocation_timeout = int(config.get("explorer_invocation_timeout_seconds", 600))
        if self.invocation_timeout < 1:
            raise ExplorerPreflightBlocked(
                "invalid_config", "explorer_invocation_timeout_seconds must be positive"
            )
        self.deadline: float | None = None
        self.protocol_errors = 0
        self.protocol_error_details: list[dict[str, str]] = []
        self.max_protocol_errors = int(
            config.get("max_explorer_protocol_errors", config.get("max_protocol_errors", 4))
        )
        self.protocol_normalizations = 0
        self.read_files: set[str] = set()
        self.search_hits: set[str] = set()
        self.search_hit_queries: dict[str, set[str]] = {}
        self.search_count = 0
        self.action_count = 0
        self.action_trace: list[dict[str, Any]] = []
        self.trace_evidence_symbols: set[str] = set()
        self.seen_actions: set[str] = set()
        self.context_trimmed = False
        self.replayed_actions: set[str] = set()
        self.no_progress_streak = 0
        self.finish_repair_pending = False
        self.finish_repair_used = False
        self.required_citation_read: str | None = None
        self.required_citation_read_rejections = 0
        self.max_no_progress_streak = int(config.get("max_explorer_no_progress_streak", 3))
        self.read_hashes: dict[str, str] = {}
        self.read_observations: dict[str, str] = {}
        self.observed_line_numbers: dict[str, set[int]] = {}
        self.displayed_line_numbers: dict[str, set[int]] = {}
        self.evidence_cache = EVIDENCE_CACHE.EvidenceCache(self.repo_root)
        self.cache_fingerprint: dict[str, Any] = {}
        self.cache_hit = False
        self.usage_run_id: str | None = None
        self.model_started = False
        self.diagnostic_logging = config.get("diagnostic_logging", True) is not False
        self.diagnostic_path: Path | None = None
        self.diagnostic_write_error: str | None = None

    def diagnostic_event(self, event: str, facts: dict[str, Any]) -> None:
        if not self.diagnostic_logging or self.diagnostic_path is None:
            return
        record = {"at": EVIDENCE_CACHE.RUN_STATE.utc_now(), "event": event, "facts": facts}
        try:
            self.diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
            with self.diagnostic_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            self.diagnostic_write_error = f"{type(exc).__name__}: {str(exc)[:200]}"

    def _finish_run(self, report: dict[str, Any]) -> dict[str, Any]:
        if self.diagnostic_path is not None:
            self.diagnostic_event(
                "finish",
                {
                    "status": report.get("status"),
                    "failure_reason": str(report.get("failure_reason") or "")[:200],
                    "actions": self.action_count,
                    "protocol_errors": self.protocol_errors,
                },
            )
            report["diagnostic_log"] = self.diagnostic_path.relative_to(self.repo_root).as_posix()
        if self.diagnostic_write_error is not None:
            report["diagnostic_write_error"] = self.diagnostic_write_error
        if self.diagnostic_path is not None:
            report_path = self.diagnostic_path.with_name("report.json")
            report["diagnostic_report"] = report_path.relative_to(self.repo_root).as_posix()
            try:
                EVIDENCE_CACHE.RUN_STATE.write_json_once(report_path, report)
            except (OSError, ValueError) as exc:
                self.diagnostic_write_error = f"{type(exc).__name__}: {str(exc)[:200]}"
                report["diagnostic_write_error"] = self.diagnostic_write_error
        EVIDENCE_CACHE.record_explorer_finish(
            self.repo_root, self.usage_run_id, report, self.task_id
        )
        return report

    def _remaining_seconds(self, phase: str) -> float:
        if self.deadline is None:
            return float(self.invocation_timeout)
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ExplorerInterrupted(
                "invocation_deadline_exceeded",
                f"the Explorer invocation deadline expired during {phase}",
            )
        return remaining

    def _has_reparse_component(self, relative: str) -> bool:
        if relative == ".":
            return False
        current = self.repo_root
        for part in Path(relative).parts:
            current = current / part
            if is_reparse_point(current):
                return True
        return False

    def system_prompt(self) -> str:
        if self.mode == "locate":
            return """You are a bounded read-only repository locator, not an implementation verifier.
Use LIST_FILES, SEARCH (literal by default), TRACE or READ_FILE to locate the
implementation and tests relevant to the single question. Never edit, run tests,
shell or another agent. Read source before citing it. Stop when locations are
sufficient. Do not predict execution results or treat assertions as source facts.
Return exactly one JSON action per turn. FINISH_SUCCESS means locations found,
NOT that code or tests pass. Its only fields are source_refs and uncertainties.
source_refs is an array of objects with path, start_line, end_line and kind
(implementation, test, caller, or definition). Select the actual controlling
branch and relevant assertions, not imports or an entire file. All lines must
have been displayed by READ_FILE. Maximum 6 references, 80 total lines.
Example shape (replace with actual observed locations):
{"action":"FINISH_SUCCESS","source_refs":[{"path":"src/a.py","start_line":7,"end_line":12,"kind":"implementation"},{"path":"tests/test_a.py","start_line":5,"end_line":10,"kind":"test"}],"uncertainties":[]}
The runtime will quote the current source verbatim; do not supply findings,
claims, quotes or a semantic verdict. For genuinely missing evidence use
FINISH_FAILED with summary, reason and uncertainties. Never repeat identical
reads/searches to avoid finishing. Repository hints are navigation, not proof."""
        return """You are a bounded read-only repository explorer. Investigate the user's question
using actual repository evidence. Output exactly one flat JSON action per turn.
Available read-only tools/actions:
- repo_browser.list_files / LIST_FILES: path? (default .), glob?, max_results?
- repo_browser.search / SEARCH: query, path?, glob?, mode? (literal by default; regex only when explicit), case_sensitive?, max_results?
- repo_browser.trace / TRACE: symbol, path?, glob? (default *.py), max_results?; returns read-only Python definition/caller/callee path+line evidence
- repo_browser.read_file / READ_FILE: path, start_line?, end_line?
- repo_browser.finish_success / FINISH_SUCCESS: relevant_files, call_flow, findings, relevant_tests, uncertainties, citations? [{path, line, claim}]
- repo_browser.finish_failed / FINISH_FAILED: summary, reason, uncertainties
Never request writes, tests, shell, Git, Codex, or another agent. Read implementation
and relevant tests before concluding. FINISH_SUCCESS means the investigation is
complete, NOT that the code is correct. A proven implementation/test mismatch is
a successful finding: report the observed source behavior and test expectation
with their separate citations. FINISH_FAILED means you cannot reliably answer
the investigation; never use it merely because you found a bug. Do not infer
that reading files alone proves you answered the question. Read implementation
and relevant tests before concluding. Relevant files/tests in the final report must
have been read. `relevant_tests` must contain repository-relative test file paths,
not test function names. When the task asks for test evidence and you read a test
file, include that path in `relevant_tests` and cite its observed line number in
`findings` or `call_flow`. A test assertion states expected behavior; it is not
evidence that the current implementation satisfies it. Distinguish observed
source behavior from test expectations. If a source operation's semantics depend
on an unread definition or model field, read that definition or state uncertainty
instead of inferring that the test passes. Use repository-relative paths. Do not return a prose or
Markdown final answer. Finish with an action shaped like:
{"action":"FINISH_SUCCESS","relevant_files":[{"path":"src/a.py","reason":"..."}],"call_flow":["..."],"findings":["..."],"relevant_tests":["tests/test_a.py"],"uncertainties":[]}
Optional structured citations must include a nonempty claim, for example
{"path":"src/a.py","line":7,"claim":"the function returns the input unchanged"}.
Use actual observed paths/lines and your supported claim, not this example's values.
Stop when evidence is sufficient. Never repeat an identical search, listing, or
file-line read unless earlier context was trimmed and you need its lines restored.
That unchanged read can be replayed once; it is not new evidence. Cite only files
you actually read; if a test path is absent, report uncertainty instead of
guessing. SEARCH defaults to literal text; use mode regex only for a deliberate
regular expression. A regex error is not evidence of absent code: retry with
literal mode. Reconcile positive search matches and read files before claiming
the repository lacks code. If searches stop yielding new evidence, conclude from
existing evidence if it answers the question; otherwise finish failed with the
specific unresolved question. Do not keep searching merely to avoid a report.
REPOSITORY_HINTS are prior navigation notes, not evidence. Their listed files
were unchanged when loaded, but you must read current source before citing a
finding or concluding the current question is answered."""

    def run(self) -> dict[str, Any]:
        self.deadline = time.monotonic() + self.invocation_timeout
        self.cache_fingerprint = EVIDENCE_CACHE.repository_fingerprint(self.repo_root)
        cached = self.evidence_cache.lookup(self.cache_task, self.cache_fingerprint)
        if cached is not None:
            self.cache_hit = True
            cached["task_id"] = self.task_id
            cached["cache"] = {
                "hit": True,
                "fingerprint": self.cache_fingerprint.get("sha256"),
                "file_count": self.cache_fingerprint.get("file_count"),
            }
            return cached
        client_preflight = getattr(self.client, "preflight", None)
        if callable(client_preflight):
            client_preflight()
        messages = [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": "EXPLORATION_TASK\n" + self.task},
        ]
        hints = self.evidence_cache.navigation_hints(task_id=self.task_id)
        if hints:
            messages.append(
                {
                    "role": "user",
                    "content": "REPOSITORY_HINTS\n" + json.dumps(hints, ensure_ascii=False),
                }
            )
        last_error: str | None = None
        for _turn in range(self.max_turns):
            original_timeout: int | float | None = None
            try:
                self._remaining_seconds("model request")
                original_timeout = getattr(self.client, "timeout", None)
                if isinstance(original_timeout, (int, float)):
                    self.client.timeout = max(
                        1, min(original_timeout, int(self._remaining_seconds("model request")))
                    )
                if not self.model_started:
                    self.model_started = True
                    self.usage_run_id = EVIDENCE_CACHE.record_explorer_start(
                        self.repo_root, self.task, self.task_id
                    )
                    if self.diagnostic_logging:
                        log_id = self.usage_run_id or f"explorer-{uuid.uuid4().hex[:12]}"
                        self.diagnostic_path = (
                            self.repo_root / ".agent" / "explorer-runs" / log_id / "events.jsonl"
                        )
                        self.diagnostic_event(
                            "start",
                            {
                                "run_id": log_id,
                                "task_sha256": EVIDENCE_CACHE.RUN_STATE.sha256_bytes(
                                    self.task.encode("utf-8")
                                ),
                            },
                        )
                finish_only = self.finish_repair_pending
                self.finish_repair_pending = False
                original_tools = getattr(self.client, "native_tools", None)
                original_choice = getattr(self.client, "native_tool_choice", None)
                if finish_only and original_tools is not None:
                    self.client.native_tools = [
                        {
                            **tool,
                            "function": {
                                **tool["function"],
                                "description": (
                                    "Correct the final report. Include citations with one "
                                    "observed path, line, and claim per required source/test."
                                ),
                                "parameters": {
                                    **tool["function"]["parameters"],
                                    "properties": {
                                        **tool["function"]["parameters"]["properties"],
                                        "citations": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "path": {"type": "string"},
                                                    "line": {"type": "integer"},
                                                    "claim": {"type": "string"},
                                                },
                                                "required": ["path", "line", "claim"],
                                            },
                                        },
                                    },
                                    "required": [
                                        *tool["function"]["parameters"]["required"],
                                        "citations",
                                    ],
                                },
                            },
                        }
                        for tool in original_tools
                        if tool["function"]["name"] == "FINISH_SUCCESS"
                    ]
                    if self.mode == "locate":
                        self.client.native_tools = [self.localization_tool()]
                    self.client.native_tool_choice = "required"
                    self.diagnostic_event("finish_repair_gate", {"turn": _turn + 1})
                try:
                    raw = self.client.complete(self._trim_messages(messages))
                finally:
                    if finish_only and original_tools is not None:
                        self.client.native_tools = original_tools
                        self.client.native_tool_choice = original_choice
                request_stats = getattr(self.client, "last_request_stats", None)
                if isinstance(request_stats, dict) and request_stats:
                    self.diagnostic_event("model_request", dict(request_stats))
                self._remaining_seconds("model request")
            except ExplorerInterrupted as exc:
                return self._finish_run(
                    self.report(
                        "interrupted",
                        failure_reason=str(exc),
                        interruption={"reason_code": exc.reason_code, "reason": str(exc)},
                    )
                )
            except ExplorerModelRequestError as exc:
                request_stats = getattr(self.client, "last_request_stats", None)
                if isinstance(request_stats, dict) and request_stats:
                    self.diagnostic_event("model_request", dict(request_stats))
                return self._finish_run(
                    self.report(
                        "failed",
                        failure_reason=str(exc),
                        infra_failure={
                            "reason_code": exc.reason_code,
                            "reason": str(exc),
                            "diagnostics": exc.diagnostics,
                        },
                    )
                )
            except ExplorerError as exc:
                request_stats = getattr(self.client, "last_request_stats", None)
                if isinstance(request_stats, dict) and request_stats:
                    self.diagnostic_event("model_request", dict(request_stats))
                return self._finish_run(self.report("failed", failure_reason=str(exc)))
            finally:
                if isinstance(original_timeout, (int, float)):
                    self.client.timeout = original_timeout
            messages.append({"role": "assistant", "content": raw})
            envelope: dict[str, Any] | None = None
            try:
                envelope = parse_action(raw)
                warnings = []
                if finish_only and envelope["action"] != "FINISH_SUCCESS":
                    raise ExplorerError("report-only recovery permits only FINISH_SUCCESS")
                if self.required_citation_read is not None:
                    expected_path = self.required_citation_read
                    if (
                        envelope["action"] != "READ_FILE"
                        or envelope["arguments"].get("path") != expected_path
                    ):
                        self.required_citation_read_rejections += 1
                        if self.required_citation_read_rejections >= 2:
                            raise ExplorerError(
                                "required citation READ_FILE was ignored twice: " + expected_path
                            )
                        observation = {
                            "status": "rejected",
                            "error": "required_citation_read_not_taken",
                            "next_step": (
                                "Next action exactly READ_FILE with path " + expected_path
                            ),
                        }
                        final = None
                    else:
                        self.required_citation_read = None
                        self.required_citation_read_rejections = 0
                        warnings = envelope["warnings"]
                        self.protocol_normalizations += len(warnings)
                        observation, final = self.execute(envelope["action"], envelope["arguments"])
                else:
                    warnings = envelope["warnings"]
                    self.protocol_normalizations += len(warnings)
                    observation, final = self.execute(envelope["action"], envelope["arguments"])
                if warnings and final is None:
                    observation["protocol_warnings"] = warnings
            except (ExplorerError, OSError, UnicodeDecodeError, re.error) as exc:
                self.protocol_errors += 1
                last_error = str(exc)
                self.protocol_error_details.append(
                    {
                        "error": str(exc),
                        "response_chars": len(raw),
                        "response_sha256": EVIDENCE_CACHE.RUN_STATE.sha256_bytes(
                            raw.encode("utf-8", errors="replace")
                        ),
                    }
                )
                observation = {"status": "error", "error": str(exc)}
                final = None
                repeated_output = (
                    envelope is None
                    and len(self.protocol_error_details) >= 2
                    and self.protocol_error_details[-1]["response_sha256"]
                    == self.protocol_error_details[-2]["response_sha256"]
                )
                has_source_and_test = any(path.startswith("tests/") for path in self.read_files)
                has_source_and_test = has_source_and_test and any(
                    not path.startswith("tests/") for path in self.read_files
                )
                if (
                    repeated_output
                    and has_source_and_test
                    and not self.finish_repair_used
                    and self.protocol_errors < self.max_protocol_errors
                ):
                    self.finish_repair_pending = True
                    self.finish_repair_used = True
                    observation["next_step"] = (
                        "The same malformed action repeated after source and test reads. "
                        "Next turn is report-only: use FINISH_SUCCESS with observed "
                        "source/test line citations and explicit uncertainty."
                    )
                    replay = "\n".join(
                        f"{path}\n{content}"
                        for path, content in sorted(self.read_observations.items())
                    )[:12000]
                    messages = messages[:2] + [
                        {
                            "role": "user",
                            "content": "REPORT_ONLY_RECOVERY\n" + replay,
                        }
                    ]
                    self.diagnostic_event(
                        "report_only_recovery",
                        {"turn": _turn + 1, "observed_files": len(self.read_files)},
                    )
                if (
                    envelope is not None
                    and envelope["action"] == "FINISH_SUCCESS"
                    and not self.finish_repair_used
                    and (
                        self.mode == "locate"
                        or "line citations" in str(exc)
                        or "relevant_tests must include observed test paths" in str(exc)
                        or str(exc).startswith("citations.")
                    )
                ):
                    needs_read = self.mode == "locate" and (
                        str(exc).startswith("source_refs contain unread lines:")
                        or (
                            str(exc).startswith("source_refs missing required paths:")
                            and any(
                                path.strip() not in self.read_files
                                for path in str(exc).split(":", 1)[1].split(",")
                            )
                        )
                    )
                    if needs_read:
                        observation["next_step"] = (
                            "READ_FILE the missing source/test lines named in the error, "
                            "then retry FINISH_SUCCESS with observed line ranges. "
                            "A SEARCH hit alone is not a cited read."
                        )
                    else:
                        self.finish_repair_pending = True
                        self.finish_repair_used = True
                        observation["next_step"] = (
                            "Correct FINISH_SUCCESS now. Supply citations as objects with "
                            "path, integer line, and claim, one for every path named in the "
                            "error. claim must be a nonempty string explaining that observed "
                            "line, not a field named text or quote. Use only lines from "
                            "READ_FILE. Do not read or search again."
                        )
                        if self.mode == "locate":
                            observation["next_step"] = (
                                "Correct FINISH_SUCCESS once using only source_refs and uncertainties. "
                                "Each reference needs path, integer start_line/end_line, and kind "
                                "implementation/test/caller/definition. Use already read lines. "
                                "Both limits apply together: at most 6 references AND at most 80 "
                                "total lines, summing end_line - start_line + 1 for every reference. "
                                "Keep controlling values and relevant assertions; omit optional "
                                "context ranges rather than citing whole files."
                            )
                if self.protocol_errors >= self.max_protocol_errors:
                    self.diagnostic_event(
                        "turn",
                        {
                            "turn": _turn + 1,
                            **EVIDENCE_CACHE.RUN_STATE.diagnostic_facts(
                                envelope["action"] if envelope else None,
                                envelope["arguments"] if envelope else {},
                                raw,
                                observation,
                            ),
                        },
                    )
                    return self._finish_run(self.report("failed", failure_reason=last_error))
            if final is not None:
                self.diagnostic_event(
                    "turn",
                    {
                        "turn": _turn + 1,
                        **EVIDENCE_CACHE.RUN_STATE.diagnostic_facts(
                            envelope["action"] if envelope else None,
                            envelope["arguments"] if envelope else {},
                            raw,
                            final,
                        ),
                    },
                )
                if final.get("status") == "success":
                    stored = self.evidence_cache.store(
                        self.cache_task, self.cache_fingerprint, final
                    )
                    final["cache"] = {
                        "hit": False,
                        "stored": stored,
                        "fingerprint": self.cache_fingerprint.get("sha256"),
                        "file_count": self.cache_fingerprint.get("file_count"),
                    }
                return self._finish_run(final)
            if finish_only:
                return self._finish_run(
                    self.report(
                        "failed",
                        failure_reason="report-only recovery exhausted: " + str(last_error),
                    )
                )
            if observation.get("status") == "ok":
                evidence = observation.get(
                    "files", observation.get("results", observation.get("content", ""))
                )
                self.no_progress_streak = 0 if evidence else self.no_progress_streak + 1
            else:
                self.no_progress_streak += 1
            if (
                self.mode == "locate"
                and envelope is not None
                and envelope["action"] == "SEARCH"
                and observation.get("status") == "ok"
                and not observation.get("results")
                and self.required_citation_read is None
            ):
                for candidate in self.config.get("explorer_required_citation_paths", []):
                    if not isinstance(candidate, str):
                        continue
                    try:
                        relative, required_file = self.resolve(candidate)
                    except ExplorerError:
                        continue
                    if relative not in self.read_files and required_file.is_file():
                        self.required_citation_read = relative
                        self.required_citation_read_rejections = 0
                        observation["next_step"] = (
                            "Content search found no matches. The required citation file exists; "
                            "next action exactly READ_FILE with path " + relative + "."
                        )
                        self.no_progress_streak = 0
                        break
            if self.finish_repair_pending:
                # One invalid terminal report is a formatting error, not another
                # repository investigation. Allow its single report-only retry
                # even when earlier malformed output used the evidence budget.
                self.no_progress_streak = 0
            self.diagnostic_event(
                "turn",
                {
                    "turn": _turn + 1,
                    **EVIDENCE_CACHE.RUN_STATE.diagnostic_facts(
                        envelope["action"] if envelope else None,
                        envelope["arguments"] if envelope else {},
                        raw,
                        observation,
                    ),
                    "no_progress_streak": self.no_progress_streak,
                },
            )
            if self.no_progress_streak >= self.max_no_progress_streak:
                return self._finish_run(
                    self.report(
                        "failed", failure_reason="no new evidence across consecutive actions"
                    )
                )
            observation["remaining_model_turns"] = self.max_turns - _turn - 1
            if (
                observation["remaining_model_turns"] <= 2
                and not self.finish_repair_pending
                and "next_step" not in observation
            ):
                observation["next_step"] = (
                    "Finish now with evidence or explicit uncertainty. "
                    "Do not start another broad search."
                )
            messages.append(
                {
                    "role": "user",
                    "content": "OBSERVATION\n"
                    + json.dumps(observation, ensure_ascii=False)[: self.max_output],
                }
            )
        return self._finish_run(self.report("failed", failure_reason="model turn budget exhausted"))

    def _trim_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        if len(messages) <= 12:
            return messages
        self.context_trimmed = True
        remaining = 12000
        replay: list[str] = []
        paths = sorted(
            self.read_observations,
            key=lambda path: (not path.startswith("tests/"), path),
        )
        for path in paths:
            block = f"{path}\n{self.read_observations[path]}\n"
            if remaining <= 0:
                break
            replay.append(block[:remaining])
            remaining -= len(replay[-1])
        recap = {
            "role": "user",
            "content": (
                "PREVIOUSLY_OBSERVED_READ_LINES\n"
                + "".join(replay)
                + "These lines were already read; do not reread them solely because earlier "
                "turns left the active context."
            ),
        }
        return messages[:2] + [recap] + messages[-10:]

    def resolve(self, raw_path: str, *, allow_dot: bool = False) -> tuple[str, Path]:
        relative = normalize_relative_path(raw_path, allow_dot=allow_dot)
        if self._has_reparse_component(relative):
            raise ExplorerError(f"path traverses a symlink, junction, or reparse point: {relative}")
        resolved = self.repo_root if relative == "." else (self.repo_root / relative).resolve()
        root_key = os.path.normcase(str(self.repo_root))
        path_key = os.path.normcase(str(resolved))
        try:
            common = os.path.commonpath((root_key, path_key))
        except ValueError as exc:
            raise ExplorerError(f"path is outside repository: {raw_path}") from exc
        if common != root_key:
            raise ExplorerError(f"path is outside repository: {raw_path}")
        return relative, resolved

    def execute(
        self, name: str, args: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        replay_read = False
        if name in {"LIST_FILES", "SEARCH", "TRACE", "READ_FILE"}:
            action_key = json.dumps(
                {"action": name, "arguments": args}, sort_keys=True, ensure_ascii=False
            )
            if action_key in self.seen_actions:
                if (
                    name == "READ_FILE"
                    and self.context_trimmed
                    and action_key not in self.replayed_actions
                    and len(self.replayed_actions) < 2
                ):
                    replay_read = True
                    self.replayed_actions.add(action_key)
                else:
                    raise ExplorerError(
                        "identical read/search already performed; use existing evidence or finish"
                    )
            else:
                self.seen_actions.add(action_key)
        self.action_count += 1
        self.action_trace.append(
            {
                "action": name,
                "path": args.get("path"),
                "query": str(args.get("query", ""))[:200] or None,
                "symbol": str(args.get("symbol", ""))[:200] or None,
                "glob": args.get("glob"),
                "mode": args.get("mode", "literal") if name == "SEARCH" else None,
            }
        )
        if name == "LIST_FILES":
            return self.list_files(args), None
        if name == "SEARCH":
            return self.search(args), None
        if name == "TRACE":
            observation = self.trace(args)
            if any(observation.get(key) for key in ("definitions", "incoming", "outgoing")):
                self.trace_evidence_symbols.add(observation["symbol"])
            return observation, None
        if name == "READ_FILE":
            if replay_read:
                relative, path = self.resolve(require_string(args.get("path"), "path"))
                expected_digest = self.read_hashes.get(relative)
                if (
                    expected_digest is None
                    or EVIDENCE_CACHE.RUN_STATE.sha256_bytes(path.read_bytes()) != expected_digest
                ):
                    raise ExplorerError("previously read file changed; cannot replay old evidence")
                observation = self.read_file(args)
                observation["status"] = "replayed"
                observation["new_evidence_count"] = 0
                observation["next_step"] = (
                    "Previously observed lines restored after context trim; "
                    "finish with evidence or uncertainty."
                )
                return observation, None
            return self.read_file(args), None
        if name == "FINISH_SUCCESS":
            if self.config.get("explorer_require_regex_search", False) and not any(
                item.get("action") == "SEARCH" and item.get("mode") == "regex"
                for item in self.action_trace
            ):
                raise ExplorerError(
                    "compatibility qualification requires regex SEARCH; next action exactly: "
                    '{"action":"SEARCH","query":"normalize_.*","mode":"regex",'
                    '"glob":"**/*.py"}'
                )
            required_trace = self.config.get("explorer_require_trace_symbol")
            if required_trace and required_trace not in self.trace_evidence_symbols:
                raise ExplorerError(
                    "compatibility qualification requires TRACE with file/line evidence; "
                    "next action exactly: "
                    + json.dumps({"action": "TRACE", "symbol": required_trace})
                )
            return {}, self.finish_success(args)
        if name == "FINISH_FAILED":
            summary = string_list(args.get("summary"), "summary")
            reason = require_string(args.get("reason"), "reason")
            uncertainties = string_list(args.get("uncertainties", []), "uncertainties")
            absence_claim = " ".join([*summary, reason]).lower()
            claims_absence = bool(
                re.search(r"\b(?:repository|repo)\b|仓库", absence_claim)
                and re.search(
                    r"\b(?:lack|lacks|missing|absent|unable to locate|does not contain)\b|不存在|没有|找不到",
                    absence_claim,
                )
            )
            matched_positive_query = any(
                query in absence_claim for query in self.search_hit_queries if len(query) >= 3
            )
            blanket_absence = bool(
                re.search(
                    r"\b(?:this|any|all)\s+(?:code|implementation|functionality)\b|这些代码|任何代码",
                    absence_claim,
                )
            )
            if claims_absence and (
                matched_positive_query or (blanket_absence and self.search_hits)
            ):
                raise ExplorerError(
                    "Repository-absence claim conflicts with positive SEARCH for the "
                    "claimed term or a blanket absence claim. Reconcile matches or name "
                    "the specific unverified symbol as an uncertainty."
                )
            return {}, self.report(
                "failed", summary=summary, uncertainties=uncertainties, failure_reason=reason
            )
        raise ExplorerError(f"unknown or forbidden action: {name}")

    def list_files(self, args: dict[str, Any]) -> dict[str, Any]:
        self._consume_search_budget()
        relative, root = self.resolve(args.get("path") or ".", allow_dot=True)
        if not root.exists():
            raise ExplorerError(f"path does not exist: {relative}")
        pattern = require_string(args.get("glob", "*"), "glob")
        limit = min(max(int(args.get("max_results", 100)), 1), 200)
        candidates = [root] if root.is_file() else root.rglob("*")
        results: list[str] = []
        for path in candidates:
            if len(results) >= limit:
                break
            if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            rel = path.relative_to(self.repo_root).as_posix()
            if self._has_reparse_component(rel):
                continue
            if EVIDENCE_CACHE.RUN_STATE.matches_repo_glob(rel, pattern):
                results.append(rel)
        return {"status": "ok", "files": results, "truncated": len(results) >= limit}

    def search(self, args: dict[str, Any]) -> dict[str, Any]:
        self._consume_search_budget()
        query = require_string(args.get("query"), "query")
        relative, root = self.resolve(args.get("path") or ".", allow_dot=True)
        if not root.exists():
            raise ExplorerError(f"path does not exist: {relative}")
        pattern = require_string(args.get("glob", "*"), "glob")
        mode = args.get("mode", "literal")
        if mode not in {"literal", "regex"}:
            raise ExplorerError("SEARCH mode must be literal or regex")
        flags = 0 if args.get("case_sensitive", False) else re.IGNORECASE
        try:
            expression = re.compile(query if mode == "regex" else re.escape(query), flags)
        except re.error as exc:
            raise ExplorerError(f"invalid SEARCH regex; retry with mode literal: {exc}") from exc
        limit = min(max(int(args.get("max_results", 40)), 1), 100)
        results: list[dict[str, Any]] = []
        scanned = 0
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if len(results) >= limit or scanned >= 1000:
                break
            if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            rel = path.relative_to(self.repo_root).as_posix()
            if self._has_reparse_component(rel):
                continue
            if not EVIDENCE_CACHE.RUN_STATE.matches_repo_glob(rel, pattern):
                continue
            if path.stat().st_size > 1_000_000:
                continue
            scanned += 1
            try:
                lines = path.read_text(encoding="utf-8-sig").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(lines, 1):
                if expression.search(line):
                    results.append({"path": rel, "line": number, "text": line[:500]})
                    if len(results) >= limit:
                        break
        self.search_hits.update(item["path"] for item in results)
        if results:
            self.search_hit_queries.setdefault(query.casefold(), set()).update(
                item["path"] for item in results
            )
        return {
            "status": "ok",
            "mode": mode,
            "results": results,
            "truncated": len(results) >= limit,
        }

    def _consume_search_budget(self) -> None:
        if self.search_count >= self.max_searches:
            raise ExplorerError("search/list budget exhausted; finish with current evidence")
        self.search_count += 1

    def trace(self, args: dict[str, Any]) -> dict[str, Any]:
        self._consume_search_budget()
        symbol = require_string(args.get("symbol"), "symbol")
        relative, root = self.resolve(args.get("path") or ".", allow_dot=True)
        if not root.exists():
            raise ExplorerError(f"path does not exist: {relative}")
        pattern = require_string(args.get("glob", "*.py"), "glob")
        limit = min(max(int(args.get("max_results", 40)), 1), 100)
        definitions: list[dict[str, Any]] = []
        incoming: list[dict[str, Any]] = []
        outgoing: list[dict[str, Any]] = []
        candidates = [root] if root.is_file() else root.rglob("*.py")
        for path in candidates:
            if len(definitions) + len(incoming) + len(outgoing) >= limit:
                break
            if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            rel = path.relative_to(self.repo_root).as_posix()
            if self._has_reparse_component(rel):
                continue
            if not EVIDENCE_CACHE.RUN_STATE.matches_repo_glob(rel, pattern):
                continue
            try:
                data = path.read_bytes()
                text = data.decode("utf-8-sig")
                tree = ast.parse(text)
            except (OSError, UnicodeError, SyntaxError):
                continue
            lines = text.splitlines()
            file_matches: list[dict[str, Any]] = []
            functions = [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            for function in functions:
                if function.name == symbol:
                    item = {
                        "path": rel,
                        "line": function.lineno,
                        "quote": lines[function.lineno - 1][:500],
                        "symbol": symbol,
                    }
                    definitions.append(item)
                    file_matches.append(item)
                    for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
                        callee = (
                            call.func.id
                            if isinstance(call.func, ast.Name)
                            else call.func.attr
                            if isinstance(call.func, ast.Attribute)
                            else None
                        )
                        if callee:
                            edge = {
                                "path": rel,
                                "line": call.lineno,
                                "quote": lines[call.lineno - 1][:500],
                                "caller": symbol,
                                "callee": callee,
                            }
                            outgoing.append(edge)
                            file_matches.append(edge)
                for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
                    callee = (
                        call.func.id
                        if isinstance(call.func, ast.Name)
                        else call.func.attr
                        if isinstance(call.func, ast.Attribute)
                        else None
                    )
                    if callee == symbol and function.name != symbol:
                        edge = {
                            "path": rel,
                            "line": call.lineno,
                            "quote": lines[call.lineno - 1][:500],
                            "caller": function.name,
                            "callee": symbol,
                        }
                        incoming.append(edge)
                        file_matches.append(edge)
            if file_matches:
                if rel not in self.read_files and len(self.read_files) >= self.max_file_reads:
                    break
                self.read_files.add(rel)
                digest = EVIDENCE_CACHE.RUN_STATE.sha256_bytes(data)
                if self.read_hashes.get(rel) not in {None, digest}:
                    self.observed_line_numbers.pop(rel, None)
                    self.displayed_line_numbers.pop(rel, None)
                    self.read_observations.pop(rel, None)
                self.read_hashes[rel] = digest
        return {
            "status": "ok",
            "symbol": symbol,
            "definitions": definitions[:limit],
            "incoming": incoming[:limit],
            "outgoing": outgoing[:limit],
            "observed_files": sorted(
                {item["path"] for item in [*definitions, *incoming, *outgoing]}
            ),
            "truncated": len(definitions) + len(incoming) + len(outgoing) >= limit,
        }

    def read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        relative, path = self.resolve(require_string(args.get("path"), "path"))
        if any(part in EXCLUDED_PARTS for part in path.parts):
            raise ExplorerError(f"excluded path cannot be read: {relative}")
        if not path.is_file():
            raise ExplorerError(f"file does not exist: {relative}")
        if relative not in self.read_files and len(self.read_files) >= self.max_file_reads:
            raise ExplorerError("file-read budget exhausted; finish with current evidence")
        data = path.read_bytes()
        if len(data) > 2_000_000:
            raise ExplorerError(f"file is too large to read: {relative}")
        text = data.decode("utf-8-sig")
        digest = EVIDENCE_CACHE.RUN_STATE.sha256_bytes(data)
        if self.read_hashes.get(relative) not in {None, digest}:
            self.observed_line_numbers.pop(relative, None)
            self.displayed_line_numbers.pop(relative, None)
            self.read_observations.pop(relative, None)
        self.read_hashes[relative] = digest
        lines = text.splitlines()
        start = int(args.get("start_line", args.get("line_start", 1)))
        requested_end = int(
            args.get("end_line", args.get("line_end", min(len(lines), start + 199)))
        )
        if start < 1 or requested_end < start:
            raise ExplorerError("READ_FILE line range is invalid")
        end = min(requested_end, start + 249)
        self.read_files.add(relative)
        shown: list[int] = []
        rendered: list[str] = []
        remaining_chars = max(0, self.max_output - 1024)
        for number in range(start, min(end, len(lines)) + 1):
            line = f"{number}: {lines[number - 1]}"
            cost = len(json.dumps(line, ensure_ascii=False)) + 2
            if cost > remaining_chars:
                break
            remaining_chars -= cost
            shown.append(number)
            rendered.append(line)
        content = "\n".join(rendered)
        self.displayed_line_numbers.setdefault(relative, set()).update(shown)
        self.observed_line_numbers.setdefault(relative, set()).update(
            number for number in shown if lines[number - 1].strip()
        )
        if content:
            prior = self.read_observations.get(relative, "")
            self.read_observations[relative] = (prior + "\n" + content)[-6000:]
        return {
            "status": "ok",
            "path": relative,
            "start_line": start,
            "end_line": shown[-1] if shown else start - 1,
            "truncated": bool(shown and shown[-1] < min(end, len(lines))) or not shown,
            "total_lines": len(lines),
            "content": content,
        }

    def citation_example(self, path: str) -> str | None:
        observed = self.read_observations.get(path, "")
        lines = [
            (int(match.group(1)), match.group(2))
            for match in re.finditer(r"(?m)^(\d+):\s*(.*)$", observed)
            if match.group(2).strip()
        ]
        if not lines:
            return None
        priorities = (
            ("assert", "def test_")
            if path.startswith("tests/")
            else ("model_dump", "return bool", "pass", "return", "if ", "def ")
        )
        for keyword in priorities:
            for number, content in lines:
                if keyword in content:
                    return f"{path} line {number}"
        return f"{path} line {lines[0][0]}"

    def finish_success(self, args: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "locate":
            return self.finish_localization(args)
        relevant_files = args.get("relevant_files")
        if not isinstance(relevant_files, list) or not relevant_files:
            raise ExplorerError("relevant_files must be a non-empty array")
        normalized_files: list[dict[str, str]] = []
        for item in relevant_files:
            if isinstance(item, str):
                path = normalize_relative_path(item)
                reason = "Relevant to the exploration task."
            elif isinstance(item, dict):
                path = normalize_relative_path(
                    require_string(item.get("path"), "relevant_files.path")
                )
                reason = require_string(item.get("reason"), "relevant_files.reason")
            else:
                raise ExplorerError("each relevant_files item must be a path or object")
            if path not in self.read_files:
                raise ExplorerError(f"final report references unread file: {path}")
            normalized_files.append({"path": path, "reason": reason})
        relevant_tests = string_list(args.get("relevant_tests", []), "relevant_tests")
        for path in relevant_tests:
            normalized = normalize_relative_path(path.split("::", 1)[0])
            if normalized not in self.read_files:
                raise ExplorerError(f"final report references unread test file: {normalized}")
        observed_tests = {
            path
            for path in self.read_files
            if Path(path).name.startswith("test_")
            or "/tests/" in f"/{path}"
            or path.startswith("tests/")
        }
        if re.search(r"\btests?\b", self.task, flags=re.IGNORECASE) and observed_tests:
            normalized_tests = {
                normalize_relative_path(path.split("::", 1)[0]) for path in relevant_tests
            }
            missing_tests = sorted(observed_tests - normalized_tests)
            if missing_tests:
                raise ExplorerError(
                    "task requests test evidence; relevant_tests must include observed test "
                    f"paths: {missing_tests}"
                )
        findings = string_list(args.get("findings"), "findings")
        call_flow = string_list(args.get("call_flow", []), "call_flow")
        citations = args.get("citations", [])
        if not isinstance(citations, list):
            raise ExplorerError("citations must be an array")
        for citation in citations:
            if not isinstance(citation, dict):
                raise ExplorerError("each citation must be an object")
            path = normalize_relative_path(require_string(citation.get("path"), "citations.path"))
            line = citation.get("line")
            claim = require_string(citation.get("claim"), "citations.claim")
            if type(line) is not int or line not in self.observed_line_numbers.get(path, set()):
                raise ExplorerError(
                    f"citation is not an observed READ_FILE line: {path} line {line}"
                )
            findings.append(f"{path} line {line}: {claim}")
        required_citations = self.config.get("explorer_required_citation_paths", [])
        if required_citations:
            if not isinstance(required_citations, list) or any(
                not isinstance(path, str) for path in required_citations
            ):
                raise ExplorerError("explorer_required_citation_paths must be paths")
            missing_citations = []
            for path in required_citations:
                normalized = normalize_relative_path(path)
                if normalized not in self.read_files:
                    missing_citations.append(normalized)
                    continue
                if not any(
                    has_path_line_citation(item, normalized) for item in [*findings, *call_flow]
                ):
                    missing_citations.append(normalized)
            if missing_citations:
                examples = [self.citation_example(path) for path in missing_citations]
                raise ExplorerError(
                    "FINISH_SUCCESS needs observed source/test line citations in "
                    "findings or call_flow for: "
                    + ", ".join(missing_citations)
                    + ". Use path and line N from an existing READ_FILE observation. "
                    + "Observed citation examples: "
                    + "; ".join(example for example in examples if example)
                )
        return self.report(
            "success",
            relevant_files=normalized_files,
            call_flow=call_flow,
            findings=findings,
            relevant_tests=relevant_tests,
            uncertainties=string_list(args.get("uncertainties", []), "uncertainties"),
        )

    @staticmethod
    def localization_tool() -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "FINISH_SUCCESS",
                "description": "Return read source/test locations, not a diagnosis or test verdict.",
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "source_refs": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 6,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "path": {"type": "string"},
                                    "start_line": {"type": "integer", "minimum": 1},
                                    "end_line": {"type": "integer", "minimum": 1},
                                    "kind": {
                                        "enum": ["implementation", "test", "caller", "definition"]
                                    },
                                },
                                "required": ["path", "start_line", "end_line", "kind"],
                            },
                        },
                        "uncertainties": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["source_refs", "uncertainties"],
                },
            },
        }

    def finish_localization(self, args: dict[str, Any]) -> dict[str, Any]:
        if set(args) != {"source_refs", "uncertainties"}:
            raise ExplorerError("localization requires only source_refs and uncertainties")
        refs = args["source_refs"]
        if not isinstance(refs, list) or not 1 <= len(refs) <= 6:
            raise ExplorerError("source_refs must contain 1 to 6 locations")
        materialized = []
        total_lines = 0
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {"path", "start_line", "end_line", "kind"}:
                raise ExplorerError("source_refs need path, start_line, end_line and kind only")
            relative, path = self.resolve(require_string(ref["path"], "source_refs.path"))
            start, end = ref["start_line"], ref["end_line"]
            if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                raise ExplorerError("source_refs require positive ordered integer lines")
            total_lines += end - start + 1
            if total_lines > 80:
                raise ExplorerError("source_refs exceed 80 total lines")
            if not isinstance(ref["kind"], str) or ref["kind"] not in {
                "implementation",
                "test",
                "caller",
                "definition",
            }:
                raise ExplorerError("source_refs have an invalid kind")
            if not set(range(start, end + 1)) <= self.displayed_line_numbers.get(relative, set()):
                raise ExplorerError(f"source_refs contain unread lines: {relative}:{start}-{end}")
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if digest != self.read_hashes.get(relative):
                raise ExplorerError(f"source_refs changed since READ_FILE: {relative}")
            lines = content.decode("utf-8-sig").splitlines()
            quote = "\n".join(lines[start - 1 : end])
            if len(quote) > 8000:
                raise ExplorerError("source_refs quote exceeds 8000 characters")
            materialized.append({**ref, "path": relative, "source_hash": digest, "quote": quote})
        required = self.config.get("explorer_required_citation_paths", [])
        if not isinstance(required, list) or any(not isinstance(path, str) for path in required):
            raise ExplorerError("explorer_required_citation_paths must be paths")
        present = {ref["path"] for ref in materialized}
        missing = {normalize_relative_path(path) for path in required} - present
        if missing:
            raise ExplorerError("source_refs missing required paths: " + ", ".join(sorted(missing)))
        if self.config.get("explorer_require_test_assertion_citation", False):
            if not any(
                ref["kind"] == "test"
                and ("assert " in ref["quote"] or "pytest.raises(" in ref["quote"])
                for ref in materialized
            ):
                raise ExplorerError(
                    "source_refs need a read test assertion line (assert or pytest.raises)"
                )
        report = self.report(
            "success",
            relevant_files=[
                {"path": ref["path"], "reason": "Located " + ref["kind"]} for ref in materialized
            ],
            findings=[
                f"{ref['path']} line {ref['start_line']}-{ref['end_line']}:\n{ref['quote']}"
                for ref in materialized
            ],
            relevant_tests=list(
                dict.fromkeys(ref["path"] for ref in materialized if ref["kind"] == "test")
            ),
            uncertainties=string_list(args["uncertainties"], "uncertainties"),
        )
        report["source_refs"] = materialized
        report["semantic_verdict"] = "not_evaluated"
        return report

    def report(
        self,
        status: str,
        *,
        relevant_files: list[dict[str, str]] | None = None,
        call_flow: list[str] | None = None,
        findings: list[str] | None = None,
        relevant_tests: list[str] | None = None,
        summary: list[str] | None = None,
        uncertainties: list[str] | None = None,
        failure_reason: str | None = None,
        interruption: dict[str, str] | None = None,
        infra_failure: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": status,
            "explorer_mode": self.mode,
            "task": self.task,
            "task_id": self.task_id,
            "relevant_files": relevant_files or [],
            "call_flow": call_flow or [],
            "findings": findings or summary or [],
            "relevant_tests": relevant_tests or [],
            "uncertainties": uncertainties or [],
            "failure_reason": failure_reason,
            "interruption": interruption,
            "infra_failure": infra_failure,
            "observed_files": sorted(self.read_files),
            "observed_hashes": dict(sorted(self.read_hashes.items())),
            "budget_usage": {
                "model_turns_max": self.max_turns,
                "actions": self.action_count,
                "unique_files_read": len(self.read_files),
                "file_reads_max": self.max_file_reads,
                "searches": self.search_count,
                "searches_max": self.max_searches,
                "protocol_errors": self.protocol_errors,
                "protocol_normalizations": self.protocol_normalizations,
                "empty_response_repairs": int(getattr(self.client, "empty_response_repairs", 0)),
                "invocation_timeout_seconds": self.invocation_timeout,
            },
            "protocol_error_details": self.protocol_error_details[-4:],
            "action_trace": self.action_trace[-12:],
        }


def compact_explorer_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = report.get("findings", [])
    uncertainties = report.get("uncertainties", [])
    budget = report.get("budget_usage", {})
    compact = {
        "schema_version": report.get("schema_version", 1),
        "explorer_mode": report.get("explorer_mode", "investigate"),
        "status": report.get("status"),
        "task": report.get("task"),
        "task_id": report.get("task_id"),
        "relevant_files": report.get("relevant_files", []),
        "findings": [str(item)[:800] for item in findings[:6]]
        if isinstance(findings, list)
        else [],
        "findings_truncated": bool(
            isinstance(findings, list)
            and (len(findings) > 6 or any(len(str(item)) > 800 for item in findings))
        ),
        "relevant_tests": report.get("relevant_tests", []),
        "uncertainties": [str(item)[:500] for item in uncertainties[:6]]
        if isinstance(uncertainties, list)
        else [],
        "failure_reason": report.get("failure_reason"),
        "infra_failure": report.get("infra_failure"),
        "diagnostic_log": report.get("diagnostic_log"),
        "diagnostic_report": report.get("diagnostic_report"),
        "diagnostic_write_error": report.get("diagnostic_write_error"),
        "cache": report.get("cache", {"hit": False}),
        "evidence_summary": {
            "observed_files": report.get("observed_files", []),
            "actions": budget.get("actions"),
            "unique_files_read": budget.get("unique_files_read"),
            "protocol_errors": budget.get("protocol_errors"),
            "empty_response_repairs": budget.get("empty_response_repairs"),
        },
    }
    if report.get("explorer_mode") == "locate":
        compact["semantic_verdict"] = "not_evaluated"
        compact["source_refs"] = [
            {key: value for key, value in ref.items() if key != "quote"}
            for ref in report.get("source_refs", [])
        ]
    if report.get("status") != "success":
        compact["protocol_error_details"] = [
            {"error": str(item.get("error", ""))[:500]}
            for item in report.get("protocol_error_details", [])[-2:]
            if isinstance(item, dict)
        ]
        compact["action_trace"] = report.get("action_trace", [])[-8:]
    return compact


def write_report(report: dict[str, Any], path: Path | None, *, compact: bool = True) -> bool:
    output = compact_explorer_report(report) if compact else report
    encoded = json.dumps(output, ensure_ascii=False, indent=2)
    print(encoded, flush=True)
    if path is not None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(encoded + "\n", encoding="utf-8", newline="\n")
        except OSError as exc:
            print(f"REPORT_WRITE_ERROR: {exc}", file=sys.stderr)
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--config", default=str(SCRIPT_DIR / "config.json"))
    parser.add_argument("--report")
    parser.add_argument("--full-report", action="store_true")
    args = parser.parse_args()
    try:
        config = load_json(Path(args.config).resolve())
        client = LMStudioClient(
            require_string(config.get("lmstudio_base_url"), "lmstudio_base_url"),
            require_string(config.get("explorer_model"), "explorer_model"),
            int(config.get("model_request_timeout_seconds", 180)),
            str(config.get("explorer_reasoning_effort", "low")),
            context_length=(
                int(config["explorer_context_length"])
                if config.get("explorer_context_length") is not None
                else None
            ),
            context_safety_margin=int(config.get("model_context_safety_margin", 1024)),
            max_output_tokens=int(config.get("explorer_max_tokens", 2048)),
            required_tool_max_tokens=int(config.get("explorer_required_tool_max_tokens", 1536)),
            temperature=config.get("explorer_temperature", 0.1),
        )
        runtime = ExplorerRuntime(Path.cwd(), args.task, config, client, args.task_id)
        report = runtime.run()
    except KeyboardInterrupt:
        report = {
            "schema_version": 1,
            "status": "interrupted",
            "task": args.task,
            "failure_reason": "keyboard interrupt",
            "interruption": {
                "reason_code": "user_interrupt",
                "reason": "The Explorer invocation was cancelled by the user.",
            },
        }
    except ExplorerPreflightBlocked as exc:
        report = {
            "schema_version": 1,
            "status": "blocked",
            "task": args.task,
            "failure_reason": str(exc),
            "blocked": {"reason_code": exc.reason_code, "reason": str(exc)},
        }
    except ExplorerModelRequestError as exc:
        report = {
            "schema_version": 1,
            "status": "failed",
            "task": args.task,
            "failure_reason": str(exc),
            "infra_failure": {
                "reason_code": exc.reason_code,
                "reason": str(exc),
                "diagnostics": exc.diagnostics,
            },
        }
    except (ExplorerError, OSError, ValueError) as exc:
        report = {
            "schema_version": 1,
            "status": "failed",
            "task": args.task,
            "failure_reason": str(exc),
        }
    report_path = Path(args.report).resolve() if args.report else None
    report_written = write_report(report, report_path, compact=not args.full_report)
    if not report_written:
        return 1
    return {
        "success": 0,
        "blocked": 3,
        "interrupted": 130,
    }.get(report.get("status"), 1)


if __name__ == "__main__":
    raise SystemExit(main())
