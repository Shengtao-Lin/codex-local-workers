from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.request
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
            "description": "Return evidence-backed exploration findings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relevant_files": {"type": "array", "items": {"type": "object"}},
                    "call_flow": {"type": "array", "items": {"type": "string"}},
                    "findings": {"type": "array", "items": {"type": "string"}},
                    "relevant_tests": {"type": "array", "items": {"type": "string"}},
                    "uncertainties": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["relevant_files", "call_flow", "findings", "relevant_tests", "uncertainties"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "FINISH_FAILED",
            "description": "Finish when reliable findings cannot be produced.",
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


class ExplorerInterrupted(ExplorerError):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class ModelClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


class LMStudioClient:
    def __init__(
        self, base_url: str, model: str, timeout: int, reasoning_effort: str = "low"
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.url = self.base_url + "/chat/completions"
        self.model = model
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort
        self.empty_response_repairs = 0

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

    def _post(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 2048,
                "reasoning_effort": self.reasoning_effort,
                "tools": EXPLORER_TOOLS,
                "tool_choice": "auto",
            }
        ).encode("utf-8")
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
            raise ExplorerError(
                f"LM Studio request failed: HTTP {exc.code}: {detail[:4000]}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ExplorerError(f"LM Studio request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise ExplorerError("LM Studio returned a non-object response")
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
        for attempt in range(2):
            payload = self._post(request_messages)
            try:
                choice = payload["choices"][0]
                message = choice["message"]
                content = message.get("content")
            except (KeyError, IndexError, TypeError) as exc:
                raise ExplorerError("LM Studio returned an unexpected response shape") from exc
            if isinstance(content, str) and content.strip():
                return content.strip()
            tool_calls = message.get("tool_calls", []) if isinstance(message, dict) else []
            if isinstance(tool_calls, list) and len(tool_calls) == 1:
                function = tool_calls[0].get("function", {}) if isinstance(tool_calls[0], dict) else {}
                name = function.get("name")
                arguments = function.get("arguments", "{}")
                if isinstance(name, str) and isinstance(arguments, (str, dict)):
                    if isinstance(arguments, dict):
                        parsed_arguments = arguments
                    else:
                        try:
                            parsed_arguments = json.loads(arguments)
                        except ValueError as exc:
                            raise ExplorerError("LM Studio tool-call arguments are invalid JSON") from exc
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
            if attempt == 0:
                self.empty_response_repairs += 1
                request_messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "Your previous response had no executable action. Output exactly one "
                            "JSON action object now, with no reasoning or prose."
                        ),
                    },
                ]
                continue
            break
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
            raise ExplorerError("nested action must contain exactly 'action' and object 'arguments'")
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
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.task = require_string(task, "task")
        self.config = config
        self.client = client
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
        self.search_count = 0
        self.action_count = 0
        self.action_trace: list[dict[str, Any]] = []
        self.read_hashes: dict[str, str] = {}
        self.evidence_cache = EVIDENCE_CACHE.EvidenceCache(self.repo_root)
        self.cache_fingerprint: dict[str, Any] = {}
        self.cache_hit = False
        self.usage_run_id: str | None = None

    def _finish_run(self, report: dict[str, Any]) -> dict[str, Any]:
        EVIDENCE_CACHE.record_explorer_finish(
            self.repo_root, self.usage_run_id, report
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
        return """You are a bounded read-only repository explorer. Investigate the user's question
using actual repository evidence. Output exactly one flat JSON action per turn.
Available read-only tools/actions:
- repo_browser.list_files / LIST_FILES: path? (default .), glob?, max_results?
- repo_browser.search / SEARCH: query, path?, glob?, case_sensitive?, max_results?
- repo_browser.read_file / READ_FILE: path, start_line?, end_line?
- repo_browser.finish_success / FINISH_SUCCESS: relevant_files, call_flow, findings, relevant_tests, uncertainties
- repo_browser.finish_failed / FINISH_FAILED: summary, reason, uncertainties
Never request writes, tests, shell, Git, Codex, or another agent. Read implementation
and relevant tests before concluding. Relevant files/tests in the final report must
have been read. `relevant_tests` must contain repository-relative test file paths,
not test function names. Use repository-relative paths. Do not return a prose or
Markdown final answer. Finish with an action shaped like:
{"action":"FINISH_SUCCESS","relevant_files":[{"path":"src/a.py","reason":"..."}],"call_flow":["..."],"findings":["..."],"relevant_tests":["tests/test_a.py"],"uncertainties":[]}
Stop when evidence is sufficient."""

    def run(self) -> dict[str, Any]:
        self.deadline = time.monotonic() + self.invocation_timeout
        self.cache_fingerprint = EVIDENCE_CACHE.repository_fingerprint(self.repo_root)
        cached = self.evidence_cache.lookup(self.task, self.cache_fingerprint)
        if cached is not None:
            self.cache_hit = True
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
                if self.usage_run_id is None:
                    self.usage_run_id = EVIDENCE_CACHE.record_explorer_start(
                        self.repo_root, self.task
                    )
                raw = self.client.complete(self._trim_messages(messages))
                self._remaining_seconds("model request")
            except ExplorerInterrupted as exc:
                return self._finish_run(self.report(
                    "interrupted",
                    failure_reason=str(exc),
                    interruption={"reason_code": exc.reason_code, "reason": str(exc)},
                ))
            except ExplorerError as exc:
                return self._finish_run(self.report("failed", failure_reason=str(exc)))
            finally:
                if isinstance(original_timeout, (int, float)):
                    self.client.timeout = original_timeout
            messages.append({"role": "assistant", "content": raw})
            try:
                envelope = parse_action(raw)
                warnings = envelope["warnings"]
                self.protocol_normalizations += len(warnings)
                observation, final = self.execute(envelope["action"], envelope["arguments"])
                if warnings and final is None:
                    observation["protocol_warnings"] = warnings
            except (ExplorerError, OSError, UnicodeDecodeError, re.error) as exc:
                self.protocol_errors += 1
                last_error = str(exc)
                self.protocol_error_details.append(
                    {"error": str(exc), "response": raw[:1000]}
                )
                observation = {"status": "error", "error": str(exc)}
                final = None
                if self.protocol_errors >= self.max_protocol_errors:
                    return self._finish_run(self.report("failed", failure_reason=last_error))
            if final is not None:
                if final.get("status") == "success":
                    stored = self.evidence_cache.store(
                        self.task, self.cache_fingerprint, final
                    )
                    final["cache"] = {
                        "hit": False,
                        "stored": stored,
                        "fingerprint": self.cache_fingerprint.get("sha256"),
                        "file_count": self.cache_fingerprint.get("file_count"),
                    }
                return self._finish_run(final)
            messages.append(
                {
                    "role": "user",
                    "content": "OBSERVATION\n" + json.dumps(observation, ensure_ascii=False)[: self.max_output],
                }
            )
        return self._finish_run(
            self.report("failed", failure_reason="model turn budget exhausted")
        )

    @staticmethod
    def _trim_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        if len(messages) <= 12:
            return messages
        return messages[:2] + messages[-10:]

    def resolve(self, raw_path: str, *, allow_dot: bool = False) -> tuple[str, Path]:
        relative = normalize_relative_path(raw_path, allow_dot=allow_dot)
        if self._has_reparse_component(relative):
            raise ExplorerError(
                f"path traverses a symlink, junction, or reparse point: {relative}"
            )
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

    def execute(self, name: str, args: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        self.action_count += 1
        self.action_trace.append(
            {
                "action": name,
                "path": args.get("path"),
                "query": str(args.get("query", ""))[:200] or None,
                "glob": args.get("glob"),
            }
        )
        if name == "LIST_FILES":
            return self.list_files(args), None
        if name == "SEARCH":
            return self.search(args), None
        if name == "READ_FILE":
            return self.read_file(args), None
        if name == "FINISH_SUCCESS":
            return {}, self.finish_success(args)
        if name == "FINISH_FAILED":
            summary = string_list(args.get("summary"), "summary")
            reason = require_string(args.get("reason"), "reason")
            uncertainties = string_list(args.get("uncertainties", []), "uncertainties")
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
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern):
                results.append(rel)
        return {"status": "ok", "files": results, "truncated": len(results) >= limit}

    def search(self, args: dict[str, Any]) -> dict[str, Any]:
        self._consume_search_budget()
        query = require_string(args.get("query"), "query")
        relative, root = self.resolve(args.get("path") or ".", allow_dot=True)
        if not root.exists():
            raise ExplorerError(f"path does not exist: {relative}")
        pattern = require_string(args.get("glob", "*"), "glob")
        flags = 0 if args.get("case_sensitive", False) else re.IGNORECASE
        expression = re.compile(query, flags)
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
            if not (fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern)):
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
        return {"status": "ok", "results": results, "truncated": len(results) >= limit}

    def _consume_search_budget(self) -> None:
        if self.search_count >= self.max_searches:
            raise ExplorerError("search/list budget exhausted; finish with current evidence")
        self.search_count += 1

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
        self.read_hashes[relative] = EVIDENCE_CACHE.RUN_STATE.sha256_bytes(data)
        lines = text.splitlines()
        start = int(args.get("start_line", args.get("line_start", 1)))
        requested_end = int(
            args.get("end_line", args.get("line_end", min(len(lines), start + 199)))
        )
        if start < 1 or requested_end < start:
            raise ExplorerError("READ_FILE line range is invalid")
        end = min(requested_end, start + 249)
        self.read_files.add(relative)
        content = "\n".join(
            f"{number}: {lines[number - 1]}"
            for number in range(start, min(end, len(lines)) + 1)
        )
        return {
            "status": "ok",
            "path": relative,
            "start_line": start,
            "end_line": min(end, len(lines)),
            "total_lines": len(lines),
            "content": content,
        }

    def finish_success(self, args: dict[str, Any]) -> dict[str, Any]:
        relevant_files = args.get("relevant_files")
        if not isinstance(relevant_files, list) or not relevant_files:
            raise ExplorerError("relevant_files must be a non-empty array")
        normalized_files: list[dict[str, str]] = []
        for item in relevant_files:
            if isinstance(item, str):
                path = normalize_relative_path(item)
                reason = "Relevant to the exploration task."
            elif isinstance(item, dict):
                path = normalize_relative_path(require_string(item.get("path"), "relevant_files.path"))
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
        return self.report(
            "success",
            relevant_files=normalized_files,
            call_flow=string_list(args.get("call_flow", []), "call_flow"),
            findings=string_list(args.get("findings"), "findings"),
            relevant_tests=relevant_tests,
            uncertainties=string_list(args.get("uncertainties", []), "uncertainties"),
        )

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
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": status,
            "task": self.task,
            "relevant_files": relevant_files or [],
            "call_flow": call_flow or [],
            "findings": findings or summary or [],
            "relevant_tests": relevant_tests or [],
            "uncertainties": uncertainties or [],
            "failure_reason": failure_reason,
            "interruption": interruption,
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
                "empty_response_repairs": int(
                    getattr(self.client, "empty_response_repairs", 0)
                ),
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
        "status": report.get("status"),
        "task": report.get("task"),
        "relevant_files": report.get("relevant_files", []),
        "findings": [str(item)[:800] for item in findings[:6]] if isinstance(findings, list) else [],
        "relevant_tests": report.get("relevant_tests", []),
        "uncertainties": [str(item)[:500] for item in uncertainties[:6]]
        if isinstance(uncertainties, list)
        else [],
        "failure_reason": report.get("failure_reason"),
        "cache": report.get("cache", {"hit": False}),
        "evidence_summary": {
            "observed_files": report.get("observed_files", []),
            "actions": budget.get("actions"),
            "unique_files_read": budget.get("unique_files_read"),
            "protocol_errors": budget.get("protocol_errors"),
            "empty_response_repairs": budget.get("empty_response_repairs"),
        },
    }
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
        )
        runtime = ExplorerRuntime(Path.cwd(), args.task, config, client)
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
