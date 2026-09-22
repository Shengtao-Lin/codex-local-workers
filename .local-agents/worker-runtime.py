from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
EXCLUDED_PARTS = {
    ".agent",
    ".local-agents",
    ".git",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
RESERVED_WRITE_PATHS = (".agent", ".local-agents", "AGENTS.md")
CODER_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "READ_FILE",
                "SEARCH",
                "SAFE_CREATE",
                "SAFE_REPLACE",
                "VALIDATE",
                "FINISH_SUCCESS",
                "FINISH_FAILED",
                "FINISH_BLOCKED",
            ],
        },
        "arguments": {
            "type": "object",
            "additionalProperties": True,
        },
    },
    "required": ["action", "arguments"],
    "additionalProperties": False,
}


def _load_safe_edit() -> Any:
    spec = importlib.util.spec_from_file_location("local_worker_safe_edit", SCRIPT_DIR / "safe-edit.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load safe-edit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_run_state() -> Any:
    spec = importlib.util.spec_from_file_location("local_worker_run_state", SCRIPT_DIR / "run-state.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load run-state.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAFE_EDIT = _load_safe_edit()
SafeEditor = SAFE_EDIT.SafeEditor
SafeEditError = SAFE_EDIT.SafeEditError
normalize_relative_path = SAFE_EDIT.normalize_relative_path
RUN_STATE = _load_run_state()
RunArchive = RUN_STATE.RunArchive
RunStateError = RUN_STATE.RunStateError


class WorkerError(RuntimeError):
    pass


class PreflightBlocked(WorkerError):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class InvocationInterrupted(WorkerError):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class PolicyViolation(WorkerError):
    pass


class RepoWriteLock:
    """Exclusive lock for writers managed by this kit; not an OS-wide sandbox."""

    def __init__(self, repo_root: Path, run_id: str) -> None:
        self.path = repo_root / ".agent" / "local-worker-write.lock"
        self.run_id = run_id
        self.token = uuid.uuid4().hex
        self.owned = False

    def acquire(self) -> None:
        if self.owned:
            self.assert_owned()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "pid": os.getpid(),
                "run_id": self.run_id,
                "token": self.token,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        try:
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            try:
                owner = self.path.read_text(encoding="utf-8-sig")[:1000]
            except OSError:
                owner = "<unreadable lock metadata>"
            raise PreflightBlocked(
                "write_lock_held",
                f"another managed writer lock exists at {self.path}: {owner}",
            ) from exc
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        self.owned = True

    def assert_owned(self) -> None:
        if not self.owned:
            raise PolicyViolation("managed write lock is not held")
        try:
            metadata = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise PolicyViolation("managed write lock disappeared or became unreadable") from exc
        if metadata.get("token") != self.token:
            raise PolicyViolation("managed write lock ownership changed")

    def release(self) -> None:
        if not self.owned:
            return
        try:
            self.assert_owned()
            self.path.unlink()
        except (OSError, PolicyViolation):
            # Never remove a lock that no longer demonstrably belongs to this run.
            pass
        finally:
            self.owned = False


class ModelClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


class LMStudioClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 180,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        top_p: float = 0.9,
        top_k: int = 40,
        min_p: float = 0.0,
        repeat_penalty: float = 1.0,
        structured_output: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.url = self.base_url + "/chat/completions"
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.min_p = min_p
        self.repeat_penalty = repeat_penalty
        self.structured_output = structured_output

    def preflight(self) -> None:
        request = urllib.request.Request(self.base_url + "/models", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise PreflightBlocked("lmstudio_unavailable", f"LM Studio preflight failed: {exc}") from exc
        items = payload.get("data", payload.get("models", [])) if isinstance(payload, dict) else []
        model_ids = {
            item.get("id") if isinstance(item, dict) else item
            for item in items
        }
        if self.model not in model_ids:
            raise PreflightBlocked(
                "model_unavailable",
                f"configured model is not available from LM Studio: {self.model}",
            )

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "min_p": self.min_p,
            "repeat_penalty": self.repeat_penalty,
            "max_tokens": self.max_tokens,
        }
        if self.structured_output:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "local_coder_action",
                    "strict": True,
                    "schema": CODER_ACTION_SCHEMA,
                },
            }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise WorkerError(f"LM Studio request failed: {exc}") from exc
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise WorkerError("LM Studio returned an unexpected response shape") from exc
        if not isinstance(content, str) or not content.strip():
            raise WorkerError("LM Studio returned an empty assistant message")
        return content.strip()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise WorkerError(f"could not load JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkerError(f"JSON root must be an object: {path}")
    return value


def require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkerError(f"{name} must be a non-empty string")
    return value.strip()


def require_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise WorkerError(f"{name} must be an array of non-empty strings")
    normalized = [item.strip() for item in value]
    if any(not item for item in normalized):
        raise WorkerError(f"{name} contains an empty string")
    return normalized


def normalize_scope_path(raw_path: str) -> str:
    candidate = require_string(raw_path, "scope path").replace("\\", "/")
    while candidate.startswith("./"):
        candidate = candidate[2:]
    if candidate == ".":
        return "."
    return normalize_relative_path(candidate)


def path_is_within(path: str, root: str) -> bool:
    return root == "." or path == root or path.startswith(root.rstrip("/") + "/")


def path_matches_any(path: str, roots: list[str] | tuple[str, ...]) -> bool:
    return any(path_is_within(path, root) for root in roots)


def normalize_requirements(value: Any, name: str, prefix: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise WorkerError(f"{name} must be a non-empty array")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(value, 1):
        if isinstance(item, str) and item.strip():
            normalized.append({"id": f"{prefix}-{index}", "text": item.strip()})
        elif isinstance(item, dict):
            normalized.append(
                {
                    "id": require_string(item.get("id"), f"{name}[{index}].id"),
                    "text": require_string(item.get("text"), f"{name}[{index}].text"),
                }
            )
        else:
            raise WorkerError(f"{name}[{index}] must be a string or id/text object")
    ids = [item["id"] for item in normalized]
    if len(ids) != len(set(ids)):
        raise WorkerError(f"{name} ids must be unique")
    return normalized


def require_identifier(value: Any, name: str) -> str:
    identifier = require_string(value, name)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", identifier):
        raise WorkerError(
            f"{name} must contain only letters, digits, dot, underscore, or hyphen"
        )
    return identifier


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    source_version = packet.get("schema_version")
    if source_version not in (1, 2):
        raise WorkerError("packet schema_version must be 1 or 2")
    packet["task_id"] = require_identifier(packet.get("task_id"), "task_id")
    packet["goal"] = require_string(packet.get("goal"), "goal")
    packet["run_id"] = require_identifier(packet.get("run_id"), "run_id")
    packet["unit_id"] = require_identifier(
        packet.get("unit_id", packet["task_id"]), "unit_id"
    )
    for field, default in (("attempt", 1), ("plan_revision", 1), ("packet_revision", 1)):
        value = packet.get(field, default)
        if not isinstance(value, int) or value < 1:
            raise WorkerError(f"{field} must be a positive integer")
        packet[field] = value
    scope = packet.get("scope")
    if not isinstance(scope, dict):
        raise WorkerError("scope must be an object")
    if source_version == 1 and "read" not in scope:
        scope["read"] = ["."]
    for field in ("read", "modify", "create", "forbidden"):
        values = require_string_list(scope.get(field, []), f"scope.{field}")
        scope[field] = [normalize_scope_path(path) for path in values]
    if not scope["read"]:
        raise WorkerError("scope.read must contain at least one readable root")
    if set(scope["modify"]) & set(scope["create"]):
        raise WorkerError("a path cannot appear in both scope.modify and scope.create")
    for path in scope["modify"] + scope["create"]:
        if path_matches_any(path, RESERVED_WRITE_PATHS):
            raise WorkerError(f"control path is never writable by Coder: {path}")
        if path_matches_any(path, scope["forbidden"]):
            raise WorkerError(f"writable path is forbidden: {path}")
        if not path_matches_any(path, scope["read"]):
            raise WorkerError(f"writable path is outside scope.read: {path}")
    packet["focused_tests"] = [
        normalize_relative_path(path.split("::", 1)[0])
        + ("::" + path.split("::", 1)[1] if "::" in path else "")
        for path in require_string_list(packet.get("focused_tests"), "focused_tests")
    ]
    for test_target in packet["focused_tests"]:
        path = test_target.split("::", 1)[0]
        if not path_matches_any(path, scope["read"]):
            raise WorkerError(f"focused test is outside scope.read: {path}")
        if path_matches_any(path, scope["forbidden"]):
            raise WorkerError(f"focused test is forbidden: {path}")
    packet["required_behavior"] = normalize_requirements(
        packet.get("required_behavior"), "required_behavior", "behavior"
    )
    packet["acceptance_criteria"] = normalize_requirements(
        packet.get("acceptance_criteria"), "acceptance_criteria", "acceptance"
    )
    scenario_source = packet.get("acceptance_scenarios")
    if scenario_source is None:
        scenario_source = [
            {"id": f"scenario-{item['id']}", "text": item["text"]}
            for item in packet["acceptance_criteria"]
        ]
    packet["acceptance_scenarios"] = normalize_requirements(
        scenario_source, "acceptance_scenarios", "scenario"
    )
    packet["validation_profile"] = require_string(
        packet.get("validation_profile", "python-focused"), "validation_profile"
    )
    packet["review_feedback"] = packet.get("review_feedback", [])
    if not isinstance(packet["review_feedback"], list):
        raise WorkerError("review_feedback must be an array")
    limits = packet.setdefault("limits", {})
    if not isinstance(limits, dict):
        raise WorkerError("limits must be an object")
    packet["_source_schema_version"] = source_version
    packet["schema_version"] = 2
    return packet


def parse_action(raw: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    remaining = raw.lstrip()
    try:
        action, offset = decoder.raw_decode(remaining)
    except ValueError as exc:
        raise WorkerError(f"response does not begin with a JSON object: {exc}") from exc
    if not isinstance(action, dict):
        raise WorkerError("response JSON root must be an object")
    warnings: list[str] = []
    trailing = remaining[offset:].strip()
    while trailing:
        try:
            extra, extra_offset = decoder.raw_decode(trailing)
        except ValueError as exc:
            raise WorkerError(f"non-JSON trailing output is not allowed: {exc}") from exc
        if not isinstance(extra, dict):
            raise WorkerError("every trailing JSON value must be an action object")
        warnings.append("ignored an additional action from the same model turn")
        trailing = trailing[extra_offset:].strip()

    name = action.get("action")
    if not isinstance(name, str):
        raise WorkerError("action must be a string")
    if "arguments" in action:
        if set(action) != {"action", "arguments"} or not isinstance(action["arguments"], dict):
            raise WorkerError("nested action must contain exactly 'action' and object 'arguments'")
        arguments = action["arguments"]
    else:
        arguments = {key: value for key, value in action.items() if key != "action"}
    return {"action": name, "arguments": arguments, "_warnings": warnings}


@dataclass
class ValidationResult:
    status: str
    py_compile: dict[str, Any]
    focused_tests: dict[str, Any]


class WorkerRuntime:
    def __init__(
        self,
        repo_root: Path,
        packet: dict[str, Any],
        config: dict[str, Any],
        client: ModelClient,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.source_packet = json.loads(json.dumps(packet))
        self.packet = validate_packet(json.loads(json.dumps(packet)))
        self.config = config
        self.client = client
        scope = self.packet["scope"]
        self.read_roots = scope["read"]
        self.forbidden_roots = scope["forbidden"]
        self.write_lock = RepoWriteLock(self.repo_root, self.packet["run_id"])
        self.archive = RunArchive(
            self.repo_root,
            self.packet["task_id"],
            self.packet["unit_id"],
            self.packet["run_id"],
        )
        self.archive_finalized = False
        self.process_state_uncertain = False
        self.process_events: list[dict[str, Any]] = []
        self.deadline: float | None = None
        self.editor = SafeEditor(
            self.repo_root,
            allowed_modify=scope["modify"],
            allowed_create=scope["create"],
            mutation_guard=self._assert_mutation_allowed,
        )
        self.max_turns = int(self._limit("max_model_turns", 24))
        self.max_protocol_errors = int(self._limit("max_protocol_errors", 4))
        self.max_repairs = int(self._limit("max_local_repairs", 2))
        self.command_timeout = int(self._limit("command_timeout_seconds", 180))
        self.invocation_timeout = int(self._limit("invocation_timeout_seconds", 900))
        self.max_output = int(config.get("max_tool_output_chars", 16000))
        if self.command_timeout < 1 or self.invocation_timeout < 1 or self.max_output < 1:
            raise PreflightBlocked(
                "invalid_config",
                "command_timeout_seconds, invocation_timeout_seconds, and max_tool_output_chars must be positive",
            )
        self.protocol_errors = 0
        self.protocol_normalizations = 0
        self.protocol_error_details: list[dict[str, str]] = []
        self.repairs = 0
        self.edit_revision = 0
        self.validated_revision = -1
        self.validation: ValidationResult | None = None
        self.validation_count = 0
        self.validated_input_facts: dict[str, dict[str, Any]] | None = None
        self.pending_failed_validation = False
        self.changed: dict[str, dict[str, str]] = {}
        self.observed_hashes: dict[str, str] = {}
        self.initial_hashes: dict[str, str | None] = {}
        self.baseline: dict[str, Any] | None = None
        for path in scope["modify"]:
            try:
                _, digest = self.editor.read_bytes(path)
            except SafeEditError as exc:
                raise PreflightBlocked("modify_target_missing", str(exc)) from exc
            self.initial_hashes[path] = digest
        for path in scope["create"]:
            relative, resolved = self.editor.resolve(path)
            if resolved.exists():
                raise PreflightBlocked(
                    "create_target_exists", f"scope.create target already exists: {relative}"
                )
            self.initial_hashes[path] = None
        for test_target in self.packet["focused_tests"]:
            test_path = test_target.split("::", 1)[0]
            relative, resolved = self.editor.resolve(test_path)
            if not resolved.is_file():
                raise PreflightBlocked(
                    "focused_test_missing", f"focused test does not exist: {relative}"
                )

    def close(self) -> None:
        self.write_lock.release()

    def _prepare_run_archive(self) -> None:
        scope = self.packet["scope"]
        authorized_paths = scope["modify"] + scope["create"]
        authorized_facts = RUN_STATE.facts_for_paths(self.repo_root, authorized_paths)
        for path, fact in authorized_facts.items():
            self.initial_hashes[path] = fact.get("sha256")
        focused_paths = [target.split("::", 1)[0] for target in self.packet["focused_tests"]]
        self.baseline = {
            "schema_version": 1,
            "captured_at": RUN_STATE.utc_now(),
            "repository": {
                "resolved_root": str(self.repo_root),
                "git": RUN_STATE.git_snapshot(self.repo_root),
            },
            "packet_sha256": RUN_STATE.sha256_bytes(
                json.dumps(
                    self.source_packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ),
            "config_sha256": RUN_STATE.sha256_bytes(
                json.dumps(
                    self.config, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ),
            "authorized_paths": authorized_facts,
            "focused_tests": RUN_STATE.facts_for_paths(self.repo_root, focused_paths),
            "coverage_note": (
                "Baseline covers authorized write paths, focused tests, trusted config, "
                "packet identity, and Git state when available. Dynamic imports are not exhaustive."
            ),
        }
        try:
            self.archive.prepare(self.source_packet, self.baseline)
        except RunStateError as exc:
            raise PreflightBlocked("run_id_conflict", str(exc)) from exc

    def _validation_paths(self) -> list[str]:
        scope = self.packet["scope"]
        focused = [target.split("::", 1)[0] for target in self.packet["focused_tests"]]
        return sorted(
            set(scope["modify"] + scope["create"] + focused + list(self.observed_hashes))
        )

    def _validation_facts(self) -> dict[str, dict[str, Any]]:
        return RUN_STATE.facts_for_paths(self.repo_root, self._validation_paths())

    def _assert_validation_current(self) -> None:
        if self.validated_input_facts is None:
            raise WorkerError("validation input state was not recorded")
        current = self._validation_facts()
        if current != self.validated_input_facts:
            raise WorkerError("validation inputs changed after validation; run VALIDATE again")

    def _post_state_and_changes(self) -> tuple[dict[str, Any], dict[str, Any]]:
        scope = self.packet["scope"]
        authorized_paths = scope["modify"] + scope["create"]
        relevant_paths = self._validation_paths()
        final_facts = RUN_STATE.facts_for_paths(self.repo_root, relevant_paths)
        initial_facts = {
            **(self.baseline or {}).get("authorized_paths", {}),
            **(self.baseline or {}).get("focused_tests", {}),
        }
        for path, digest in self.observed_hashes.items():
            initial_facts.setdefault(
                path,
                {"path": path, "exists": True, "kind": "file", "sha256": digest},
            )

        def content_identity(fact: dict[str, Any] | None) -> tuple[Any, Any, Any]:
            if fact is None:
                return (None, None, None)
            return (fact.get("exists"), fact.get("kind"), fact.get("sha256"))

        actual_changes = []
        for path in sorted(set(initial_facts) | set(final_facts)):
            before = initial_facts.get(path)
            after = final_facts.get(path)
            if content_identity(before) != content_identity(after):
                actual_changes.append(
                    {
                        "path": path,
                        "before": before,
                        "after": after,
                        "runtime_edit_recorded": path in self.changed,
                    }
                )
        post_state = {
            "captured_at": RUN_STATE.utc_now(),
            "repository": {
                "resolved_root": str(self.repo_root),
                "git": RUN_STATE.git_snapshot(self.repo_root),
            },
            "authorized_paths": {
                path: final_facts[path] for path in authorized_paths if path in final_facts
            },
            "validation_inputs": self._validation_facts(),
        }
        changes = {
            "runtime_edits": [self.changed[path] for path in sorted(self.changed)],
            "actual_relevant_changes": actual_changes,
            "unattributed_relevant_changes": [
                item for item in actual_changes if not item["runtime_edit_recorded"]
            ],
        }
        return post_state, changes

    @staticmethod
    def _failure_signature(report: dict[str, Any]) -> str | None:
        status = report.get("status")
        if status in {"ready_for_review"}:
            return None
        reason_code = (report.get("blocked") or report.get("interruption") or {}).get(
            "reason_code"
        )
        validation = report.get("validation") or {}
        validation_status = validation.get("status")
        raw = f"coder|{status}|{reason_code or validation_status or report.get('failure_reason') or 'unknown'}"
        return re.sub(r"\s+", " ", raw)[:240]

    def _complete_run(self, report: dict[str, Any]) -> dict[str, Any]:
        if self.archive_finalized or not self.archive.prepared:
            return report
        post_state, changes = self._post_state_and_changes()
        report["failure_signature"] = self._failure_signature(report)
        report["evidence_refs"] = {
            "run_archive": self.archive.run_root.relative_to(self.repo_root).as_posix(),
            "packet": (self.archive.run_root / "packet.json").relative_to(self.repo_root).as_posix(),
            "baseline": (self.archive.run_root / "baseline.json").relative_to(self.repo_root).as_posix(),
            "events": (self.archive.run_root / "events.jsonl").relative_to(self.repo_root).as_posix(),
        }
        try:
            self.archive.finalize(
                report,
                changes,
                self.validation.__dict__ if self.validation else None,
                post_state,
            )
            self.archive_finalized = True
        except (OSError, ValueError, RunStateError) as exc:
            report["status"] = "blocked"
            report["failure_reason"] = f"run archive finalization failed: {exc}"
            report["blocked"] = {
                "reason_code": "state_recording_failed",
                "reason": report["failure_reason"],
                "requested_scope": {"read": [], "modify": [], "create": []},
            }
            report["next_action_required"] = "primary_inspect_partial_state"
        return report

    def _assert_mutation_allowed(self) -> None:
        self.write_lock.assert_owned()
        if self.process_state_uncertain:
            raise PolicyViolation(
                "a timed-out validation process may still be running; further writes are blocked"
            )

    def _remaining_seconds(self, phase: str) -> float:
        if self.deadline is None:
            return float(self.invocation_timeout)
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise InvocationInterrupted(
                "invocation_deadline_exceeded",
                f"the invocation deadline expired during {phase}",
            )
        return remaining

    def _interrupted_report(self, exc: InvocationInterrupted) -> dict[str, Any]:
        return self.report(
            "interrupted",
            [str(exc)],
            str(exc),
            ["Inspect partial changes and process events before continuing."],
            interruption={"reason_code": exc.reason_code, "reason": str(exc)},
        )

    def _limit(self, key: str, default: int) -> Any:
        return self.packet.get("limits", {}).get(key, self.config.get(key, default))

    def validation_profile(self) -> dict[str, Any]:
        profiles = self.config.get("validation_profiles", {})
        if not isinstance(profiles, dict):
            raise PreflightBlocked("invalid_config", "validation_profiles must be an object")
        profile = profiles.get(self.packet["validation_profile"])
        if profile is None and self.packet["validation_profile"] == "python-focused":
            profile = {
                "python": self.config.get("python", ".\\.venv\\Scripts\\python.exe"),
                "pytest_argv": ["-B", "-m", "pytest"],
                "compile": True,
            }
        if not isinstance(profile, dict):
            raise PreflightBlocked(
                "validation_profile_missing",
                f"validation profile is not configured: {self.packet['validation_profile']}",
            )
        return profile

    def python_path(self) -> Path:
        configured = require_string(self.validation_profile().get("python"), "validation profile python")
        path = Path(configured)
        return path.resolve() if path.is_absolute() else (self.repo_root / path).resolve()

    def preflight(self) -> dict[str, Any]:
        client_preflight = getattr(self.client, "preflight", None)
        if callable(client_preflight):
            client_preflight()
        python_path = self.python_path()
        if not python_path.is_file():
            raise PreflightBlocked("python_missing", f"project Python was not found: {python_path}")
        pytest_check = self._run_command([str(python_path), "-c", "import pytest"])
        if pytest_check["status"] != "passed":
            raise PreflightBlocked(
                "pytest_missing",
                f"pytest is unavailable in configured Python: {python_path}",
            )
        return {
            "status": "ok",
            "python": str(python_path),
            "validation_profile": self.packet["validation_profile"],
            "focused_tests": self.packet["focused_tests"],
        }

    def system_prompt(self) -> str:
        return """You are a bounded local implementation worker. The current packet is authoritative.
You may request exactly one action per turn and output only one flat JSON object:
{"action":"READ_FILE","path":"src/example.py","start_line":1}
Available actions:
- READ_FILE: path, start_line?, end_line?
- SEARCH: query, path?, glob?, case_sensitive?, max_results?
- SAFE_CREATE: path, content
- SAFE_REPLACE: path, expected_sha256, find, replace
- VALIDATE: no additional fields
- FINISH_SUCCESS: summary, remaining_uncertainty
- FINISH_FAILED: summary, reason, remaining_uncertainty
- FINISH_BLOCKED: reason_code, reason, requested_scope?, evidence_refs?, proposed_next_step?
Do not emit Markdown or prose outside JSON. Never invoke shell, Git, Codex, or another agent.
Read a file before replacing it and use the sha256 returned by READ_FILE. Make narrow edits.
VALIDATE runs syntax checks and the packet's focused tests. FINISH_SUCCESS is rejected unless
validation passed after the last edit. Previous attempts are context, not authority."""

    def run(self) -> dict[str, Any]:
        self.deadline = time.monotonic() + self.invocation_timeout
        messages = [
            {"role": "system", "content": self.system_prompt()},
            {
                "role": "user",
                "content": "IMPLEMENTATION_PACKET\n" + json.dumps(self.packet, ensure_ascii=False),
            },
        ]
        try:
            self.write_lock.acquire()
            self._prepare_run_archive()
            for _turn in range(1, self.max_turns + 1):
                self._remaining_seconds("model request")
                original_timeout = getattr(self.client, "timeout", None)
                if isinstance(original_timeout, (int, float)):
                    self.client.timeout = max(
                        1, min(original_timeout, int(self._remaining_seconds("model request")))
                    )
                try:
                    self.archive.mark_model_started()
                    raw = self.client.complete(self._trim_messages(messages))
                    self._remaining_seconds("model request")
                except WorkerError as exc:
                    try:
                        self._remaining_seconds("model request")
                    except InvocationInterrupted as interrupted:
                        return self._complete_run(self._interrupted_report(interrupted))
                    return self._complete_run(
                        self.report("failed", ["Model transport failed."], str(exc), [])
                    )
                finally:
                    if isinstance(original_timeout, (int, float)):
                        self.client.timeout = original_timeout
                messages.append({"role": "assistant", "content": raw})
                try:
                    action = parse_action(raw)
                    warnings = action.pop("_warnings")
                    self.protocol_normalizations += len(warnings)
                    observation, finished = self.execute(action)
                    self.archive.event(
                        "tool_action",
                        {
                            "turn": _turn,
                            "action": action["action"],
                            "status": observation.get("status") if finished is None else finished.get("status"),
                        },
                    )
                    if warnings and finished is None:
                        observation["protocol_warnings"] = warnings
                except InvocationInterrupted as exc:
                    return self._complete_run(self._interrupted_report(exc))
                except PreflightBlocked as exc:
                    return self._complete_run(self.report(
                        "blocked",
                        [str(exc)],
                        str(exc),
                        [],
                        blocked={
                            "reason_code": exc.reason_code,
                            "reason": str(exc),
                            "requested_scope": {"read": [], "modify": [], "create": []},
                        },
                    ))
                except PolicyViolation as exc:
                    return self._complete_run(self.report(
                        "policy_violation",
                        [str(exc)],
                        str(exc),
                        ["Primary must inspect the lock and process state before continuing."],
                    ))
                except (WorkerError, SafeEditError, OSError, re.error) as exc:
                    self.archive.event(
                        "tool_error",
                        {"turn": _turn, "error_type": type(exc).__name__, "error": str(exc)[:1000]},
                    )
                    if isinstance(exc, PermissionError):
                        return self._complete_run(self.report(
                            "blocked",
                            ["The host denied an authorized operation."],
                            str(exc),
                            [],
                            blocked={
                                "reason_code": "permission_denied",
                                "reason": str(exc),
                                "requested_scope": {"read": [], "modify": [], "create": []},
                            },
                        ))
                    self.protocol_errors += 1
                    self.protocol_error_details.append(
                        {"error": str(exc), "response": raw[:1000]}
                    )
                    observation = {"status": "error", "error": str(exc)}
                    finished = None
                    if self.protocol_errors >= self.max_protocol_errors:
                        return self._complete_run(self.report(
                            "failed",
                            ["The model exceeded the protocol error budget."],
                            str(exc),
                            [],
                        ))
                if finished is not None:
                    return self._complete_run(finished)
                encoded = json.dumps(observation, ensure_ascii=False)
                messages.append({"role": "user", "content": "OBSERVATION\n" + encoded[: self.max_output]})
            return self._complete_run(
                self.report("failed", ["The model turn budget was exhausted."], "turn limit", [])
            )
        except InvocationInterrupted as exc:
            return self._complete_run(self._interrupted_report(exc))
        except PreflightBlocked as exc:
            return self._complete_run(self.report(
                "blocked",
                [str(exc)],
                str(exc),
                [],
                blocked={
                    "reason_code": exc.reason_code,
                    "reason": str(exc),
                    "requested_scope": {"read": [], "modify": [], "create": []},
                },
            ))
        except PolicyViolation as exc:
            return self._complete_run(self.report(
                "policy_violation",
                [str(exc)],
                str(exc),
                ["Primary must inspect the lock and process state before continuing."],
            ))
        except KeyboardInterrupt:
            return self._complete_run(
                self.report(
                    "interrupted",
                    ["The invocation was cancelled by the user."],
                    "keyboard interrupt",
                    ["Inspect partial changes before issuing another packet."],
                    interruption={
                        "reason_code": "user_interrupt",
                        "reason": "The invocation was cancelled by the user.",
                    },
                )
            )
        finally:
            self.close()

    @staticmethod
    def _trim_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        # The system prompt and packet remain authoritative. Older observations
        # are reproducible through READ_FILE/SEARCH, so retain only recent turns.
        if len(messages) <= 12:
            return messages
        return messages[:2] + messages[-10:]

    def execute(self, envelope: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        name = envelope["action"]
        args = envelope["arguments"]
        handlers = {
            "READ_FILE": self.read_file,
            "SEARCH": self.search,
            "SAFE_CREATE": self.safe_create,
            "SAFE_REPLACE": self.safe_replace,
            "VALIDATE": self.validate,
        }
        if name in handlers:
            return handlers[name](args), None
        if name == "FINISH_SUCCESS":
            if self.validation is None or self.validation.status != "passed":
                raise WorkerError("FINISH_SUCCESS requires a successful VALIDATE")
            if self.validated_revision != self.edit_revision:
                raise WorkerError("files changed after validation; run VALIDATE again")
            self._assert_validation_current()
            return {}, self.report(
                "ready_for_review",
                self._string_list(args.get("summary"), "summary"),
                None,
                self._string_list(args.get("remaining_uncertainty", []), "remaining_uncertainty"),
            )
        if name == "FINISH_FAILED":
            return {}, self.report(
                "failed",
                self._string_list(args.get("summary"), "summary"),
                require_string(args.get("reason"), "reason"),
                self._string_list(args.get("remaining_uncertainty", []), "remaining_uncertainty"),
            )
        if name == "FINISH_BLOCKED":
            return {}, self.blocked_report(args)
        raise WorkerError(f"unknown action: {name}")

    @staticmethod
    def _string_list(value: Any, name: str) -> list[str]:
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return require_string_list(value, name)

    def _assert_read_allowed(self, raw_path: str) -> tuple[str, Path]:
        relative, resolved = self.editor.resolve(raw_path)
        if any(part in EXCLUDED_PARTS for part in resolved.parts):
            raise WorkerError(f"path is excluded from Coder reads: {relative}")
        if path_matches_any(relative, self.forbidden_roots):
            raise WorkerError(f"path is forbidden: {relative}")
        if not path_matches_any(relative, self.read_roots):
            raise WorkerError(f"path is outside scope.read: {relative}")
        return relative, resolved

    def read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = require_string(args.get("path"), "path")
        relative, resolved = self._assert_read_allowed(path)
        if not resolved.is_file():
            raise WorkerError(f"file does not exist: {relative}")
        data = resolved.read_bytes()
        digest = SAFE_EDIT.sha256_bytes(data)
        self.observed_hashes[relative] = digest
        if len(data) > 2_000_000:
            raise WorkerError("file is too large to read")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise WorkerError("file is not UTF-8 text") from exc
        lines = text.splitlines()
        start = int(args.get("start_line", 1))
        end = int(args.get("end_line", min(len(lines), start + 199)))
        if start < 1 or end < start or end - start + 1 > 250:
            raise WorkerError("READ_FILE line range must contain 1-250 lines")
        body = "\n".join(f"{index}: {lines[index - 1]}" for index in range(start, min(end, len(lines)) + 1))
        return {
            "status": "ok",
            "path": relative,
            "sha256": digest,
            "start_line": start,
            "end_line": min(end, len(lines)),
            "total_lines": len(lines),
            "content": body,
        }

    def search(self, args: dict[str, Any]) -> dict[str, Any]:
        query = require_string(args.get("query"), "query")
        root_raw = args.get("path", ".")
        search_roots: list[Path] = []
        if root_raw == ".":
            for readable_root in self.read_roots:
                candidate = self.repo_root if readable_root == "." else (self.repo_root / readable_root).resolve()
                if candidate.exists():
                    search_roots.append(candidate)
        else:
            _, root = self._assert_read_allowed(require_string(root_raw, "path"))
            if not root.exists():
                raise WorkerError("search path does not exist")
            search_roots.append(root)
        pattern = require_string(args.get("glob", "*"), "glob")
        flags = 0 if args.get("case_sensitive", False) else re.IGNORECASE
        expression = re.compile(query, flags)
        max_results = min(max(int(args.get("max_results", 40)), 1), 100)
        results: list[dict[str, Any]] = []
        scanned = 0
        seen: set[str] = set()
        for root in search_roots:
            candidates = [root] if root.is_file() else root.rglob("*")
            for path in candidates:
                if len(results) >= max_results or scanned >= 1000:
                    break
                if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
                    continue
                relative = path.relative_to(self.repo_root).as_posix()
                if relative in seen or path_matches_any(relative, self.forbidden_roots):
                    continue
                seen.add(relative)
                if not (fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern)):
                    continue
                if path.stat().st_size > 1_000_000:
                    continue
                scanned += 1
                try:
                    raw = path.read_bytes()
                    lines = raw.decode("utf-8-sig").splitlines()
                except (UnicodeDecodeError, OSError):
                    continue
                for number, line in enumerate(lines, 1):
                    if expression.search(line):
                        self.observed_hashes[relative] = SAFE_EDIT.sha256_bytes(raw)
                        results.append({"path": relative, "line": number, "text": line[:500]})
                        if len(results) >= max_results:
                            break
        return {"status": "ok", "results": results, "truncated": len(results) >= max_results}

    def _begin_edit(self) -> None:
        if self.pending_failed_validation:
            if self.repairs >= self.max_repairs:
                raise WorkerError("local repair budget is exhausted; finish with failure")
            self.repairs += 1
            self.pending_failed_validation = False

    def _record_edit(self, result: dict[str, str]) -> dict[str, Any]:
        self.edit_revision += 1
        self.validation = None
        self.validated_input_facts = None
        self.changed[result["path"]] = result
        return {"status": "ok", **result, "edit_revision": self.edit_revision}

    def safe_create(self, args: dict[str, Any]) -> dict[str, Any]:
        self._begin_edit()
        return self._record_edit(
            self.editor.create(
                require_string(args.get("path"), "path"),
                require_string(args.get("content"), "content"),
            )
        )

    def safe_replace(self, args: dict[str, Any]) -> dict[str, Any]:
        self._begin_edit()
        return self._record_edit(
            self.editor.replace(
                require_string(args.get("path"), "path"),
                require_string(args.get("find"), "find"),
                require_string(args.get("replace"), "replace"),
                require_string(args.get("expected_sha256"), "expected_sha256"),
            )
        )

    def _terminate_process_tree(self, process: subprocess.Popen[str]) -> dict[str, Any]:
        event: dict[str, Any] = {"pid": process.pid, "termination": "requested"}
        try:
            if os.name == "nt":
                helper = subprocess.run(
                    ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    shell=False,
                )
                event["taskkill_exit_code"] = helper.returncode
                event["taskkill_output"] = (helper.stdout + helper.stderr)[-2000:]
            else:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name != "nt":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait(timeout=5)
            event["termination"] = "confirmed"
        except (OSError, subprocess.SubprocessError) as exc:
            event["termination"] = "uncertain"
            event["error"] = str(exc)
            self.process_state_uncertain = True
            try:
                process.kill()
            except OSError:
                pass
        self.process_events.append(event)
        return event

    def _run_command(self, argv: list[str]) -> dict[str, Any]:
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        remaining = self._remaining_seconds("validation command")
        timeout = max(1, min(self.command_timeout, int(remaining)))
        popen_options: dict[str, Any] = {}
        if os.name == "nt":
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_options["start_new_session"] = True
        try:
            process = subprocess.Popen(
                argv,
                cwd=self.repo_root,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                **popen_options,
            )
        except PermissionError as exc:
            raise PreflightBlocked(
                "permission_denied",
                f"host denied validation command {argv!r}: {exc}",
            ) from exc
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            termination = self._terminate_process_tree(process)
            if remaining <= self.command_timeout:
                raise InvocationInterrupted(
                    "invocation_deadline_exceeded",
                    f"the invocation deadline expired while running {argv!r}",
                )
            return {
                "status": "failed",
                "exit_code": None,
                "output": f"command timed out after {timeout} seconds",
                "timed_out": True,
                "termination": termination,
                "argv": argv,
            }
        except KeyboardInterrupt:
            self._terminate_process_tree(process)
            raise
        combined = stdout + stderr
        output = combined[-self.max_output :]
        return {
            "status": "passed" if process.returncode == 0 else "failed",
            "exit_code": process.returncode,
            "output": output,
            "output_truncated": len(combined) > self.max_output,
            "argv": argv,
        }

    def validate(self, args: dict[str, Any]) -> dict[str, Any]:
        if args:
            raise WorkerError("VALIDATE does not accept arguments")
        self.validation_count += 1
        profile = self.validation_profile()
        python_path = self.python_path()
        if not python_path.is_file():
            raise WorkerError(f"project Python was not found: {python_path}")
        input_facts_before = self._validation_facts()
        python_files = sorted(path for path in self.changed if path.lower().endswith(".py"))
        compile_results = []
        for path in python_files if profile.get("compile", True) else []:
            result = self._run_command(
                [
                    str(python_path),
                    "-B",
                    "-c",
                    (
                        "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
                        "compile(p.read_bytes(), str(p), 'exec')"
                    ),
                    path,
                ]
            )
            compile_results.append({"path": path, **result})
            if result["status"] != "passed":
                validation = ValidationResult(
                    "failed",
                    {"status": "failed", "files": compile_results},
                    {"status": "not_run"},
                )
                self.validation = validation
                self.pending_failed_validation = True
                self.validated_input_facts = None
                self.archive.event(
                    "validation_finished",
                    {"status": "failed", "stage": "syntax", "edit_revision": self.edit_revision},
                )
                return {"status": "failed", "validation": validation.__dict__}
        tests = self.packet["focused_tests"]
        pytest_argv = profile.get("pytest_argv", ["-B", "-m", "pytest"])
        if not isinstance(pytest_argv, list) or any(not isinstance(item, str) for item in pytest_argv):
            raise WorkerError("validation profile pytest_argv must be an array of strings")
        junit_path = self.archive.run_root / f"pytest-junit-{self.validation_count}.xml"
        runtime_pytest_args = [*tests, "-q", "-p", "no:cacheprovider", f"--junitxml={junit_path}"]
        test_result = self._run_command(
            [str(python_path), *pytest_argv, *runtime_pytest_args]
        )
        junit: dict[str, Any] = {"path": str(junit_path), "available": False}
        try:
            root = ET.parse(junit_path).getroot()
            if root.tag == "testsuite":
                suites = [root]
            elif root.attrib.get("tests") is not None:
                suites = [root]
            else:
                suites = list(root.findall("./testsuite"))
            totals = {
                name: sum(int(float(suite.attrib.get(name, 0))) for suite in suites)
                for name in ("tests", "failures", "errors", "skipped")
            }
            junit = {
                "path": junit_path.relative_to(self.repo_root).as_posix(),
                "available": True,
                **totals,
                "executed": totals["tests"] - totals["skipped"],
            }
        except (OSError, ValueError, ET.ParseError) as exc:
            junit["error"] = str(exc)
        status = "passed" if test_result["status"] == "passed" else "failed"
        if not junit.get("available"):
            status = "failed"
            test_result["output"] += "\nRuntime could not verify pytest collection statistics."
        elif junit["tests"] <= 0 or junit["executed"] <= 0:
            status = "failed"
            test_result["output"] += (
                f"\nRuntime rejected pytest result: tests={junit['tests']}, "
                f"skipped={junit['skipped']}, executed={junit['executed']}."
            )
        input_facts_after = self._validation_facts()
        inputs_unchanged = input_facts_before == input_facts_after
        if not inputs_unchanged:
            status = "failed"
            test_result["output"] += "\nValidation inputs changed while checks were running."
        validation = ValidationResult(
            status,
            {"status": "passed", "files": compile_results},
            {
                "argv": [*pytest_argv, *runtime_pytest_args],
                **test_result,
                "junit": junit,
                "inputs_unchanged": inputs_unchanged,
                "input_facts": input_facts_after,
            },
        )
        self.validation = validation
        if status == "passed":
            self.validated_revision = self.edit_revision
            self.validated_input_facts = input_facts_after
            self.pending_failed_validation = False
        else:
            self.validated_input_facts = None
            self.pending_failed_validation = True
        self.archive.event(
            "validation_finished",
            {
                "status": status,
                "edit_revision": self.edit_revision,
                "tests": junit.get("tests"),
                "executed": junit.get("executed"),
            },
        )
        return {"status": status, "validation": validation.__dict__}

    def blocked_report(self, args: dict[str, Any]) -> dict[str, Any]:
        reason_code = require_string(args.get("reason_code"), "reason_code")
        reason = require_string(args.get("reason"), "reason")
        requested_scope = args.get("requested_scope", {})
        if not isinstance(requested_scope, dict):
            raise WorkerError("requested_scope must be an object")
        normalized_scope: dict[str, list[str]] = {}
        for field in ("read", "modify", "create"):
            values = requested_scope.get(field, [])
            normalized_scope[field] = [
                normalize_scope_path(path)
                for path in require_string_list(values, f"requested_scope.{field}")
            ]
        blocked = {
            "reason_code": reason_code,
            "reason": reason,
            "requested_scope": normalized_scope,
            "evidence_refs": self._string_list(args.get("evidence_refs", []), "evidence_refs"),
            "proposed_next_step": args.get("proposed_next_step"),
        }
        if blocked["proposed_next_step"] is not None:
            blocked["proposed_next_step"] = require_string(
                blocked["proposed_next_step"], "proposed_next_step"
            )
        return self.report(
            "blocked",
            [reason],
            reason,
            self._string_list(args.get("remaining_uncertainty", []), "remaining_uncertainty"),
            blocked=blocked,
        )

    def report(
        self,
        status: str,
        summary: list[str],
        failure_reason: str | None,
        remaining_uncertainty: list[str],
        *,
        blocked: dict[str, Any] | None = None,
        interruption: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        changed_files = []
        for path, item in sorted(self.changed.items()):
            try:
                _, final_hash = self.editor.read_bytes(path)
            except SafeEditError:
                final_hash = None
            changed_files.append(
                {
                    "path": path,
                    "operation": item["operation"],
                    "initial_sha256": self.initial_hashes.get(path),
                    "final_sha256": final_hash,
                }
            )
        return {
            "schema_version": 2,
            "status": status,
            "identity": {
                "task_id": self.packet["task_id"],
                "unit_id": self.packet["unit_id"],
                "run_id": self.packet["run_id"],
                "attempt": self.packet["attempt"],
                "plan_revision": self.packet["plan_revision"],
                "packet_revision": self.packet["packet_revision"],
                "source_packet_schema": self.packet["_source_schema_version"],
            },
            "task_id": self.packet["task_id"],
            "unit_id": self.packet["unit_id"],
            "run_id": self.packet["run_id"],
            "attempt": self.packet["attempt"],
            "changed_files": changed_files,
            "worker_claims": {
                "summary": summary,
                "remaining_uncertainty": remaining_uncertainty,
            },
            "summary": summary,
            "failure_reason": failure_reason,
            "validation": self.validation.__dict__ if self.validation else None,
            "blocked": blocked,
            "interruption": interruption,
            "runtime_facts": {
                "managed_write_lock": str(self.write_lock.path),
                "process_state_uncertain": self.process_state_uncertain,
                "process_events": self.process_events,
                "invocation_timeout_seconds": self.invocation_timeout,
                "command_timeout_seconds": self.command_timeout,
            },
            "next_action_required": {
                "ready_for_review": "primary_review",
                "blocked": "primary_scope_or_environment_decision",
                "failed": "primary_rework_or_takeover_decision",
                "interrupted": "primary_inspect_partial_state",
                "policy_violation": "primary_takeover",
            }.get(status, "primary_review"),
            "repair_count": self.repairs,
            "protocol_error_count": self.protocol_errors,
            "protocol_normalization_count": self.protocol_normalizations,
            "protocol_error_details": self.protocol_error_details[-4:],
            "remaining_uncertainty": remaining_uncertainty,
            "primary_review_checklist": {
                "required_behavior_ids": [
                    item["id"] for item in self.packet["required_behavior"]
                ],
                "acceptance_criteria_ids": [
                    item["id"] for item in self.packet["acceptance_criteria"]
                ],
                "acceptance_scenario_ids": [
                    item["id"] for item in self.packet["acceptance_scenarios"]
                ],
            },
        }


def compact_handoff(report: dict[str, Any]) -> dict[str, Any]:
    validation = report.get("validation") or {}
    focused = validation.get("focused_tests") or {}
    junit = focused.get("junit") or {}
    changed = [
        {key: item.get(key) for key in ("path", "operation", "initial_sha256", "final_sha256")}
        for item in report.get("changed_files", [])
        if isinstance(item, dict)
    ]

    def clipped_strings(values: Any, *, count: int = 6, chars: int = 500) -> list[str]:
        if not isinstance(values, list):
            return []
        return [str(item)[:chars] for item in values[:count]]

    compact = {
        "schema_version": report.get("schema_version", 2),
        "status": report.get("status"),
        "identity": report.get("identity") or {
            key: report.get(key) for key in ("task_id", "unit_id", "run_id", "attempt")
        },
        "changed_files": changed,
        "worker_summary": clipped_strings(
            (report.get("worker_claims") or {}).get("summary", report.get("summary", []))
        ),
        "validation_summary": {
            "status": validation.get("status"),
            "syntax": (validation.get("py_compile") or {}).get("status"),
            "focused_tests": focused.get("status"),
            "tests": junit.get("tests"),
            "executed": junit.get("executed"),
            "failures": junit.get("failures"),
            "errors": junit.get("errors"),
            "skipped": junit.get("skipped"),
            "inputs_unchanged": focused.get("inputs_unchanged"),
        },
        "blocked": report.get("blocked"),
        "interruption": report.get("interruption"),
        "failure_reason": report.get("failure_reason"),
        "failure_signature": report.get("failure_signature"),
        "next_action_required": report.get("next_action_required"),
        "evidence_refs": report.get("evidence_refs", {}),
        "remaining_uncertainty": clipped_strings(report.get("remaining_uncertainty", [])),
        "primary_review_checklist": report.get("primary_review_checklist", {}),
    }
    if report.get("status") not in {"ready_for_review", "blocked"}:
        compact["recent_protocol_errors"] = [
            {"error": str(item.get("error", ""))[:500]}
            for item in report.get("protocol_error_details", [])[-2:]
            if isinstance(item, dict)
        ]
    return compact


def write_report(report: dict[str, Any], path: Path | None, *, compact: bool = True) -> bool:
    output = compact_handoff(report) if compact else report
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
    parser.add_argument("--packet", required=True)
    parser.add_argument("--config", default=str(SCRIPT_DIR / "config.json"))
    parser.add_argument("--report")
    parser.add_argument("--full-report", action="store_true")
    args = parser.parse_args()
    repo_root = Path.cwd().resolve()
    try:
        packet = load_json(Path(args.packet).resolve())
        config = load_json(Path(args.config).resolve())
        client = LMStudioClient(
            require_string(config.get("lmstudio_base_url"), "lmstudio_base_url"),
            require_string(config.get("coder_model"), "coder_model"),
            int(config.get("model_request_timeout_seconds", 180)),
            max_tokens=int(config.get("coder_max_tokens", 4096)),
            temperature=float(config.get("coder_temperature", 0.1)),
            top_p=float(config.get("coder_top_p", 0.9)),
            top_k=int(config.get("coder_top_k", 40)),
            min_p=float(config.get("coder_min_p", 0.0)),
            repeat_penalty=float(config.get("coder_repeat_penalty", 1.0)),
            structured_output=bool(config.get("coder_structured_output", True)),
        )
        runtime = WorkerRuntime(repo_root, packet, config, client)
        runtime.preflight()
        report = runtime.run()
    except KeyboardInterrupt:
        if "runtime" in locals():
            runtime.close()
            report = runtime.report(
                "interrupted",
                ["The invocation was cancelled by the user."],
                "keyboard interrupt",
                ["Inspect partial changes before issuing another packet."],
                interruption={
                    "reason_code": "user_interrupt",
                    "reason": "The invocation was cancelled by the user.",
                },
            )
        else:
            report = {
                "schema_version": 2,
                "status": "interrupted",
                "failure_reason": "keyboard interrupt",
                "changed_files": [],
                "interruption": {
                    "reason_code": "user_interrupt",
                    "reason": "The invocation was cancelled by the user.",
                },
                "next_action_required": "primary_inspect_partial_state",
            }
    except PreflightBlocked as exc:
        report = {
            "schema_version": 2,
            "status": "blocked",
            "task_id": packet.get("task_id") if "packet" in locals() else None,
            "unit_id": packet.get("unit_id") if "packet" in locals() else None,
            "run_id": packet.get("run_id") if "packet" in locals() else None,
            "failure_reason": str(exc),
            "blocked": {
                "reason_code": exc.reason_code,
                "reason": str(exc),
                "requested_scope": {"read": [], "modify": [], "create": []},
            },
            "changed_files": [],
            "next_action_required": "primary_environment_decision",
        }
    except (WorkerError, SafeEditError, OSError, ValueError) as exc:
        report = {
            "schema_version": 2,
            "status": "failed",
            "task_id": packet.get("task_id") if "packet" in locals() else None,
            "failure_reason": str(exc),
            "changed_files": [],
        }
    report_path = Path(args.report).resolve() if args.report else None
    report_written = write_report(report, report_path, compact=not args.full_report)
    if not report_written:
        return 1
    return {
        "ready_for_review": 0,
        "blocked": 3,
        "policy_violation": 4,
        "interrupted": 130,
    }.get(report.get("status"), 1)


if __name__ == "__main__":
    raise SystemExit(main())
