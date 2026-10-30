from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVIEW_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "READ_FILE",
                "SEARCH",
                "RUN_APPROVED_TEST",
                "RUN_APPROVED_STATIC_CHECK",
                "REPORT",
            ],
        },
        "arguments": {"type": "object", "additionalProperties": True},
    },
    "required": ["action", "arguments"],
    "additionalProperties": False,
}

REVIEW_SOURCE_REF_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "start_line": {"type": "integer", "minimum": 1},
        "end_line": {"type": "integer", "minimum": 1},
    },
    "required": ["path", "start_line", "end_line"],
    "additionalProperties": False,
}

REVIEW_NATIVE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": True,
            },
        },
    }
    for name, description, properties, required in (
        (
            "READ_FILE",
            "Read bounded source or test lines without modifying files.",
            {
                "path": {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"},
            },
            ["path"],
        ),
        (
            "SEARCH",
            "Search packet-readable files.",
            {"query": {"type": "string"}, "path": {"type": "string"}},
            ["query"],
        ),
        (
            "RUN_APPROVED_TEST",
            "Run only a registered focused test id.",
            {"test_id": {"type": "string", "enum": ["focused-tests"]}},
            ["test_id"],
        ),
        (
            "RUN_APPROVED_STATIC_CHECK",
            "Run only a registered static check id.",
            {"check_id": {"type": "string"}},
            ["check_id"],
        ),
        (
            "REPORT",
            "Submit the read-only review report and source-backed findings.",
            {
                "decision": {
                    "type": "string",
                    "enum": ["pass_to_primary", "rework", "escalate"],
                },
                "findings": {"type": "array", "items": {"type": "object"}},
                "verified_contract_ids": {"type": "array", "items": {"type": "string"}},
                "unverified_claims": {"type": "array", "items": {"type": "string"}},
                "ordering_review": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "constraint_id": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["verified", "violated", "uncertain"],
                            },
                            "evidence_type": {"type": "string", "enum": ["source", "diff"]},
                            "path": {"type": ["string", "null"]},
                            "line": {"type": ["integer", "null"]},
                            "evidence": {"type": "string"},
                        },
                        "required": [
                            "constraint_id",
                            "status",
                            "evidence_type",
                            "path",
                            "line",
                            "evidence",
                        ],
                        "additionalProperties": False,
                    },
                },
                "contract_review": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "obligation_id": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["verified", "violated", "uncertain"],
                            },
                            "source_ref": REVIEW_SOURCE_REF_SCHEMA,
                            "source_refs": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 3,
                                "items": REVIEW_SOURCE_REF_SCHEMA,
                            },
                            "evidence": {"type": "string"},
                        },
                    },
                },
                "verified_check_ids": {"type": "array", "items": {"type": "string"}},
            },
            ["decision", "findings", "ordering_review"],
        ),
    )
]


def canonical_citation_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One-request presentation repair; never normalize a submitted report."""
    result = json.loads(json.dumps(tools))
    for tool in result:
        function = tool.get("function", {})
        if function.get("name") != "REPORT":
            continue
        item = function["parameters"]["properties"]["contract_review"]["items"]
        item["properties"].pop("source_ref", None)
        transport = "evidence_ids" if "evidence_ids" in item["properties"] else "source_refs"
        item["required"] = ["obligation_id", "status", transport, "evidence"]
        item["additionalProperties"] = False
    return result


def evidence_id_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Present one citation transport; source selection and verdict remain untrusted."""
    result = canonical_citation_tools(tools)
    for tool in result:
        function = tool.get("function", {})
        if function.get("name") != "REPORT":
            continue
        item = function["parameters"]["properties"]["contract_review"]["items"]
        item["properties"].pop("source_refs")
        item["properties"]["evidence_ids"] = {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {"type": "string"},
            "uniqueItems": True,
        }
        item["required"] = ["obligation_id", "status", "evidence_ids", "evidence"]
    return result


ASSESSMENT_DECISIONS = {
    "consistent": "pass_to_primary",
    "optional_test_gap": "pass_to_primary",
    "implementation_defect": "rework",
    "required_test_gap": "rework",
    "contract_conflict": "escalate",
    "insufficient_evidence": "escalate",
}


def assessment_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = json.loads(json.dumps(tools))
    for tool in result:
        function = tool.get("function", {})
        if function.get("name") == "REPORT":
            parameters = function["parameters"]
            parameters["properties"].pop("decision")
            parameters["properties"]["assessment"] = {
                "type": "string",
                "enum": list(ASSESSMENT_DECISIONS),
            }
            parameters["required"] = [
                "assessment" if key == "decision" else key for key in parameters["required"]
            ]
    return result


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


WORKER = _load("local_reviewer_worker_runtime", "worker-runtime.py")
RUN_STATE = _load("local_reviewer_run_state", "run-state.py")
SAFE_EDIT = _load("local_reviewer_safe_edit", "safe-edit.py")


class ReviewError(RuntimeError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    value = WORKER.load_json(path)
    if not isinstance(value, dict):
        raise ReviewError(f"expected object in {path}")
    return value


class ReviewerRuntime:
    def __init__(
        self,
        repo_root: Path,
        request: dict[str, Any],
        config: dict[str, Any],
        client: Any,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.request = request
        self.config = config
        self.diagnostic_logging = config.get("diagnostic_logging", True) is not False
        self.client = client
        self.evidence_ids_enabled = config.get("reviewer_evidence_ids", False)
        if type(self.evidence_ids_enabled) is not bool:
            raise ReviewError("reviewer_evidence_ids must be a boolean")
        self.evidence_catalog: dict[str, dict[str, Any]] = {}
        if self.evidence_ids_enabled and isinstance(getattr(client, "native_tools", None), list):
            client.native_tools = evidence_id_tools(client.native_tools)
        self.assessment_protocol = config.get("reviewer_assessment_protocol", False)
        if type(self.assessment_protocol) is not bool:
            raise ReviewError("reviewer_assessment_protocol must be a boolean")
        if self.assessment_protocol and isinstance(getattr(client, "native_tools", None), list):
            client.native_tools = assessment_tools(client.native_tools)
        self.native_history = config.get("reviewer_native_history", False)
        if type(self.native_history) is not bool:
            raise ReviewError("reviewer_native_history must be a boolean")
        self.prepass_challenge_pending = config.get("reviewer_prepass_challenge", False)
        if type(self.prepass_challenge_pending) is not bool:
            raise ReviewError("reviewer_prepass_challenge must be a boolean")
        self.finding_challenge_pending = config.get("reviewer_finding_challenge", False)
        if type(self.finding_challenge_pending) is not bool:
            raise ReviewError("reviewer_finding_challenge must be a boolean")
        self.prepass_challenge_context: dict[str, Any] | None = None
        self.approved_execution: list[dict[str, Any]] = []
        self.search_count = 0
        self.deferred_report: dict[str, Any] | None = None
        self.task_id = WORKER.require_identifier(request.get("task_id"), "task_id")
        self.unit_id = WORKER.require_identifier(request.get("unit_id"), "unit_id")
        self.run_id = WORKER.require_identifier(request.get("run_id"), "run_id")
        self.review_id = WORKER.require_identifier(request.get("review_id"), "review_id")
        self.run_root = self.repo_root / ".agent" / "tasks" / self.task_id / "runs" / self.run_id
        self.review_root = (
            self.repo_root / ".agent" / "tasks" / self.task_id / "reviews" / self.review_id
        )
        if self.review_root.exists():
            raise ReviewError(f"review_id already has an archive: {self.review_id}")
        if not (self.run_root / "completed.json").is_file():
            raise ReviewError(f"Coder run is incomplete or missing: {self.run_id}")
        self.packet = WORKER.validate_packet(load_object(self.run_root / "packet.json"))
        if self.packet["unit_id"] != self.unit_id:
            raise ReviewError("review unit_id does not match the Coder run")
        self.handoff = load_object(self.run_root / "handoff.json")
        if self.handoff.get("status") == "validation_passed_pending_review":
            spec = importlib.util.spec_from_file_location(
                "reviewer_host_handoff", SCRIPT_DIR / "local-unit.py"
            )
            gate = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gate)
            if request.get("execution_protocol") != gate.HOST.PROTOCOL:
                raise ReviewError("Host review requires its explicit protocol")
            gate.verify_handoff(self.repo_root, self.handoff, config=config)
        elif self.handoff.get("status") != "ready_for_review":
            raise ReviewError("only ready_for_review Coder runs can enter local review")
        elif (
            self.handoff.get("execution_protocol") is not None
            or request.get("execution_protocol") is not None
        ):
            raise ReviewError("Unknown review execution protocol")
        self.validation = load_object(self.run_root / "validation.json")
        self.post_state = load_object(self.run_root / "post-state.json")
        self.expected_inputs = self.post_state.get("validation_inputs")
        if not isinstance(self.expected_inputs, dict):
            raise ReviewError("Coder run post-state is missing validation input facts")
        self.diff = (self.run_root / "cumulative.diff").read_text(
            encoding="utf-8", errors="replace"
        )
        self.read_roots = self.packet["scope"]["read"]
        self.forbidden_roots = self.packet["scope"]["forbidden"]
        self.editor = SAFE_EDIT.SafeEditor(self.repo_root, allowed_modify=[], allowed_create=[])
        self.max_turns = int(config.get("max_reviewer_turns", 16))
        self.max_protocol_errors = int(config.get("max_reviewer_protocol_errors", 4))
        self.max_duplicate_read_streak = int(config.get("max_reviewer_duplicate_reads", 3))
        self.max_output = int(config.get("max_tool_output_chars", 16000))
        self.invocation_timeout = int(config.get("reviewer_invocation_timeout_seconds", 600))
        self.protocol_errors = 0
        self.last_protocol_error: str | None = None
        self.same_protocol_error_streak = 0
        self.read_paths: set[str] = set()
        self.read_lines: dict[str, set[int]] = {}
        self.observed_read_hashes: dict[str, str] = {}
        self.displayed_diff_hunks: set[str] = set()
        self.context_recovery = config.get("reviewer_context_recovery", False)
        if type(self.context_recovery) is not bool:
            raise ReviewError("reviewer_context_recovery must be boolean")
        self.context_retention = config.get("reviewer_context_retention", "recent")
        if not isinstance(self.context_retention, str) or self.context_retention not in {
            "recent",
            "budgeted",
        }:
            raise ReviewError("reviewer_context_retention must be recent or budgeted")
        self.active_read_lines: dict[str, set[int]] | None = None
        self.context_recoveries: dict[tuple[str, int, int], int] = {}
        self.duplicate_read_streak = 0
        if (
            self.max_turns < 1
            or self.max_protocol_errors < 1
            or self.max_duplicate_read_streak < 1
            or self.max_output < 1
            or self.invocation_timeout < 1
        ):
            raise ReviewError("reviewer limits must be positive")
        self._assert_inputs_current()

    @staticmethod
    def _content_identity(fact: dict[str, Any] | None) -> tuple[Any, Any, Any, Any]:
        if fact is None:
            return (None, None, None, None)
        return (
            fact.get("exists"),
            fact.get("kind"),
            fact.get("sha256"),
            fact.get("size"),
        )

    def _assert_inputs_current(self) -> None:
        current = RUN_STATE.facts_for_paths(self.repo_root, self.expected_inputs)
        changed = [
            path
            for path in sorted(set(self.expected_inputs) | set(current))
            if self._content_identity(self.expected_inputs.get(path))
            != self._content_identity(current.get(path))
        ]
        if changed:
            raise ReviewError("review inputs changed after the Coder run: " + ", ".join(changed))
        self._assert_observed_sources_current()

    def _assert_observed_sources_current(self) -> None:
        for relative, observed_hash in self.observed_read_hashes.items():
            _, resolved = self._assert_read_allowed(relative)
            try:
                current_hash = RUN_STATE.sha256_bytes(resolved.read_bytes())
            except OSError as exc:
                raise ReviewError("read source changed or disappeared: " + relative) from exc
            if current_hash != observed_hash:
                raise ReviewError("read source changed after observation: " + relative)

    def prepare(self) -> None:
        if self.handoff.get("status") == "validation_passed_pending_review":
            # One dispatch per host run, including failed/interrupted reviews.
            # A new review id is not permission to replay the same unit.
            try:
                RUN_STATE.write_json_once(self.run_root / "host-review-dispatch.json", self.request)
            except (OSError, ValueError) as exc:
                raise ReviewError(
                    "Host run already dispatched or dispatch could not be recorded"
                ) from exc
        try:
            self.review_root.mkdir(parents=True)
        except FileExistsError as exc:
            raise ReviewError(f"review_id already has an archive: {self.review_id}") from exc
        RUN_STATE.write_json_once(self.review_root / "input.json", self.request)
        self.event("review_prepared", {"run_id": self.run_id, "unit_id": self.unit_id})

    def event(self, event: str, facts: dict[str, Any] | None = None) -> None:
        record = {"at": RUN_STATE.utc_now(), "event": event, "facts": facts or {}}
        with (self.review_root / "events.jsonl").open(
            "a", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _assert_read_allowed(self, raw_path: str) -> tuple[str, Path]:
        if raw_path == ".":
            relative, resolved = ".", self.repo_root
        else:
            relative, resolved = self.editor.resolve(raw_path)
        if any(part in WORKER.EXCLUDED_PARTS for part in resolved.parts):
            raise ReviewError(f"path is excluded from Reviewer reads: {relative}")
        if WORKER.path_matches_any(relative, self.forbidden_roots):
            raise ReviewError(f"path is forbidden: {relative}")
        if not WORKER.path_matches_any(relative, self.read_roots):
            raise ReviewError(f"path is outside review read scope: {relative}")
        return relative, resolved

    def read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        observation = self._read_file(args)
        if not self.evidence_ids_enabled:
            return observation
        path = observation["path"]
        if observation["status"] in {"ok", "context_restored"}:
            start = observation["start_line"]
            end = observation.get("end_line")
            if type(end) is int:
                for low in range(start, end + 1, 20):
                    reference = {
                        "path": path,
                        "start_line": low,
                        "end_line": min(low + 19, end),
                        "source_hash": self.observed_read_hashes[path],
                    }
                    if reference not in self.evidence_catalog.values():
                        self.evidence_catalog[f"E{len(self.evidence_catalog) + 1}"] = reference
        observation["citation_evidence"] = [
            {"id": evidence_id, **reference}
            for evidence_id, reference in self.evidence_catalog.items()
            if reference["path"] == path
        ]
        return observation

    def _read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        self._assert_observed_sources_current()
        relative, path = self._assert_read_allowed(args.get("path"))
        if not path.is_file():
            raise ReviewError(f"file does not exist: {relative}")
        start = args.get("start_line", 1)
        end = args.get("end_line")
        if type(start) is not int or start < 1:
            raise ReviewError("start_line must be a positive integer")
        if end is not None and (type(end) is not int or end < start):
            raise ReviewError("end_line must be at least start_line")
        source_bytes = path.read_bytes()
        source_hash = RUN_STATE.sha256_bytes(source_bytes)
        if (
            relative in self.observed_read_hashes
            and self.observed_read_hashes[relative] != source_hash
        ):
            raise ReviewError("read source changed during observation: " + relative)
        text = source_bytes.decode("utf-8-sig")
        lines = text.splitlines()
        selected = lines[start - 1 : end]
        content = "\n".join(
            f"{number}: {line}" for number, line in enumerate(selected, start=start)
        )
        visible = content[: self.max_output]
        if len(visible) == len(content):
            visible_count = len(selected)
        else:
            visible_count = visible.count("\n")
        self.read_paths.add(relative)
        self.observed_read_hashes[relative] = source_hash
        seen_lines = self.read_lines.setdefault(relative, set())
        visible_lines = set(range(start, start + visible_count))
        new_lines = visible_lines - seen_lines
        if not new_lines and visible_count:
            recovery_key = (relative, start, start + visible_count - 1)
            if (
                self.context_recovery
                and self.active_read_lines is not None
                and not visible_lines <= self.active_read_lines.get(relative, set())
                and visible_count <= 40
                and self.context_recoveries.get(recovery_key, 0) < 2
                and sum(self.context_recoveries.values()) < 8
            ):
                self.context_recoveries[recovery_key] = (
                    self.context_recoveries.get(recovery_key, 0) + 1
                )
                self.event(
                    "read_context_restored",
                    {
                        "path": relative,
                        "start_line": start,
                        "end_line": recovery_key[2],
                        "new_evidence_count": 0,
                    },
                )
                return {
                    "status": "context_restored",
                    "path": relative,
                    "start_line": start,
                    "end_line": recovery_key[2],
                    "content": visible,
                    "truncated": len(content) > self.max_output,
                    "new_evidence_count": 0,
                    "next_step": "Previously read source restored. Continue investigating relevant dependencies or report when ready.",
                }
            next_unread = next(
                (number for number in range(1, len(lines) + 1) if number not in seen_lines),
                None,
            )
            observation: dict[str, Any] = {
                "status": "already_read",
                "path": relative,
                "start_line": start,
                "end_line": start + visible_count - 1 if visible_count else None,
                "next_step": (
                    "This range adds no visible source evidence. Do not repeat this "
                    "READ_FILE. READ_FILE a narrower unread range only when more source "
                    "evidence is required; otherwise submit REPORT with the evidence already read."
                ),
            }
            if next_unread is not None:
                observation["suggested_action"] = {
                    "action": "READ_FILE",
                    "arguments": {
                        "path": relative,
                        "start_line": next_unread,
                        "end_line": min(next_unread + 39, len(lines)),
                    },
                }
            if (
                self.config.get("reviewer_require_source_and_test_reads", False)
                and relative not in self.focused_test_paths()
                and not any(self.read_lines.get(path) for path in self.focused_test_paths())
            ):
                # A missing protected test is more useful than an arbitrary unread
                # import. Only actually displayed, scope-checked lines enter the
                # existing read ledger; no contract verdict is inferred here.
                for selector in self.packet["focused_tests"]:
                    test_path = selector.split("::", 1)[0]
                    try:
                        _, resolved = self._assert_read_allowed(test_path)
                        lines = resolved.read_text(encoding="utf-8-sig").splitlines()
                        name = selector.split("::")[-1] if "::" in selector else None
                        start_line = next(
                            (
                                i
                                for i, line in enumerate(lines, 1)
                                if (
                                    name
                                    and line.lstrip().startswith(
                                        (f"def {name}(", f"async def {name}(")
                                    )
                                )
                                or (
                                    not name
                                    and line.lstrip().startswith(("def test_", "async def test_"))
                                )
                            ),
                            1,
                        )
                        evidence = self.read_file(
                            {
                                "path": test_path,
                                "start_line": start_line,
                                "end_line": min(start_line + 39, len(lines)),
                            }
                        )
                        observation["required_test_read"] = evidence
                        self.event(
                            "required_test_evidence_prefetched",
                            {
                                "path": test_path,
                                "start_line": start_line,
                                "visible_end_line": evidence.get("end_line"),
                            },
                        )
                        break
                    except (OSError, UnicodeError, ReviewError, SAFE_EDIT.SafeEditError):
                        continue
            if self.required_reads_complete():
                observation["required_next_action"] = "REPORT"
                observation["evidence_replay"] = self.replay_read_evidence()
                observation["next_step"] = (
                    "This range adds no visible source evidence and the required source/test "
                    "reads are complete. The bounded evidence_replay restores source lines that "
                    "may have left the active context. Do not issue another READ_FILE or SEARCH; "
                    "submit REPORT now."
                )
            return observation
        seen_lines.update(visible_lines)
        observation = {
            "status": "ok",
            "path": relative,
            "start_line": start,
            "end_line": start + visible_count - 1 if visible_count else None,
            "requested_end_line": min(end or len(lines), len(lines)),
            "content": visible,
            "truncated": len(content) > self.max_output,
        }
        if not visible_count and selected:
            observation["next_step"] = (
                "No complete source line was visible; READ_FILE a narrower range "
                "before citing source evidence."
            )
        return observation

    def _trim_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        if self.context_retention == "recent":
            return messages if len(messages) <= 12 else messages[:2] + messages[-10:]
        context = getattr(self.client, "context_length", None)
        if type(context) is not int or context <= 0:
            raise ReviewError("budgeted reviewer retention requires configured context length")
        available = max(
            0,
            context
            - getattr(self.client, "max_tokens", 4096)
            - getattr(self.client, "context_safety_margin", 1024),
        )
        target = int(available * 0.8)
        retained = list(messages)
        # Same conservative estimate as Coder. Client preflight remains authoritative;
        # preserve the initial contract and latest five exchanges even if irreducible.
        while len(retained) > 12 and (
            len(retained) > 64 or (len(json.dumps(retained, ensure_ascii=False)) + 3) // 4 > target
        ):
            del retained[2:4]
        return retained

    def _update_active_read_context(self, messages: list[dict[str, str]]) -> None:
        """Track structured source observations actually retained in the next request.

        This is a visibility index, never a replacement for the citation ledger.
        Replay strings are deliberately not parsed into new source authority.
        """
        active: dict[str, set[int]] = {}

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                path, content = value.get("path"), value.get("content")
                if isinstance(path, str) and isinstance(content, str):
                    for line in content.splitlines():
                        number, sep, _text = line.partition(": ")
                        if sep and number.isdigit():
                            active.setdefault(path, set()).add(int(number))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        for message in messages:
            content = message.get("content", "")
            if message.get("role") in {"user", "tool"} and content.startswith("OBSERVATION\n"):
                try:
                    visit(json.loads(content.split("\n", 1)[1]))
                except ValueError:
                    continue
        self.active_read_lines = active

    def replay_read_evidence(self) -> str:
        """Restore previously displayed changed-source and focused-test lines first."""
        primary_paths = list(dict.fromkeys([*self.diff_paths(), *self.focused_test_paths()]))
        paths = [*primary_paths, *(path for path in self.read_lines if path not in primary_paths)]
        chunks: list[str] = []
        remaining = min(self.max_output, 6000)
        for path in paths:
            seen = self.read_lines.get(path)
            if not seen or remaining <= 0:
                continue
            try:
                _relative, resolved = self._assert_read_allowed(path)
                lines = resolved.read_text(encoding="utf-8-sig").splitlines()
            except (OSError, UnicodeError, ReviewError, SAFE_EDIT.SafeEditError):
                continue
            selected = [
                f"{number}: {lines[number - 1]}"
                for number in sorted(seen)
                if 1 <= number <= len(lines)
            ]
            if not selected:
                continue
            block = f"{path}\n" + "\n".join(selected) + "\n"
            chunks.append(block[:remaining])
            remaining -= len(chunks[-1])
        return "".join(chunks)

    def focused_test_paths(self) -> list[str]:
        """Map pytest node selectors to the files Reviewer can actually read."""
        return list(
            dict.fromkeys(selector.split("::", 1)[0] for selector in self.packet["focused_tests"])
        )

    def required_reads_complete(self) -> bool:
        changed_sources = [
            path
            for path in self.diff_paths()
            if path not in self.focused_test_paths() and path.endswith(".py")
        ]
        source_read = not changed_sources or any(
            self.read_lines.get(path) for path in changed_sources
        )
        focused = self.focused_test_paths()
        test_read = not focused or any(self.read_lines.get(path) for path in focused)
        # Do not restrict the next action to REPORT while its coverage gate
        # still requires source or test lines that have not been displayed.
        return source_read and test_read and not self.coverage_facts()["missing"]

    def search(self, args: dict[str, Any]) -> dict[str, Any]:
        query = WORKER.require_string(args.get("query"), "query")
        root = args.get("path", ".")
        if root == ".":
            relative_root = "."
            search_roots = [
                self.repo_root if item == "." else self.repo_root / item for item in self.read_roots
            ]
        else:
            relative_root, resolved_root = self._assert_read_allowed(root)
            search_roots = [resolved_root]
        glob = args.get("glob", "*")
        if not isinstance(glob, str) or not glob:
            raise ReviewError("glob must be a non-empty string")
        limit = args.get("max_results", 50)
        if not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ReviewError("max_results must be between 1 and 200")
        case_sensitive = args.get("case_sensitive", False)
        needle = query if case_sensitive else query.lower()
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for search_root in search_roots:
            if not search_root.exists():
                continue
            candidates = [search_root] if search_root.is_file() else search_root.rglob("*")
            for path in candidates:
                if len(results) >= limit:
                    break
                if any(part in WORKER.EXCLUDED_PARTS for part in path.parts):
                    continue
                try:
                    if not path.is_file():
                        continue
                    relative = path.relative_to(self.repo_root).as_posix()
                    if relative in seen:
                        continue
                    seen.add(relative)
                    if not RUN_STATE.matches_repo_glob(relative, glob):
                        continue
                    self._assert_read_allowed(relative)
                    lines = path.read_text(encoding="utf-8-sig").splitlines()
                except (OSError, UnicodeError, ReviewError, SAFE_EDIT.SafeEditError):
                    continue
                for number, line in enumerate(lines, 1):
                    haystack = line if case_sensitive else line.lower()
                    if needle in haystack:
                        results.append({"path": relative, "line": number, "text": line[:500]})
                        self.read_paths.add(relative)
                        if len(results) >= limit:
                            break
        self.search_count += 1
        return {"status": "ok", "root": relative_root, "results": results}

    def validation_profile(self) -> dict[str, Any]:
        profiles = self.config.get("validation_profiles", {})
        if not isinstance(profiles, dict):
            raise ReviewError("validation_profiles must be an object")
        profile = profiles.get(self.packet["validation_profile"])
        if profile is None and self.packet["validation_profile"] == "python-focused":
            profile = {
                "python": self.config.get("python", sys.executable),
                "pytest_argv": ["-B", "-m", "pytest"],
                "commands": [],
            }
        if not isinstance(profile, dict):
            raise ReviewError(
                f"validation profile is not configured: {self.packet['validation_profile']}"
            )
        return profile

    def approved_execution_catalog(self) -> dict[str, list[dict[str, Any]]]:
        profile = self.validation_profile()
        tests = (
            [
                {
                    "id": "focused-tests",
                    "action": "RUN_APPROVED_TEST",
                    "arguments": {"test_id": "focused-tests"},
                    "targets": self.packet["focused_tests"],
                }
            ]
            if self.packet["focused_tests"]
            else []
        )
        checks = []
        for item in profile.get("commands", []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                checks.append(
                    {
                        "id": item["id"],
                        "action": "RUN_APPROVED_STATIC_CHECK",
                        "arguments": {"check_id": item["id"]},
                    }
                )
        return {"tests": tests, "static_checks": checks}

    def _run_approved(
        self, kind: str, action_id: str, argv: list[str], *, junit_path: Path | None = None
    ) -> dict[str, Any]:
        timeout = int(self.config.get("command_timeout_seconds", 180))
        try:
            completed = subprocess.run(
                argv,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                shell=False,
            )
            output = (completed.stdout + completed.stderr)[-8000:]
            result = {
                "kind": kind,
                "id": action_id,
                "status": "passed" if completed.returncode == 0 else "failed",
                "exit_code": completed.returncode,
                "output": output,
            }
        except subprocess.TimeoutExpired as exc:
            result = {
                "kind": kind,
                "id": action_id,
                "status": "timed_out",
                "exit_code": None,
                "output": str(exc)[-2000:],
            }
        if junit_path is not None:
            junit: dict[str, Any] = {
                "path": junit_path.relative_to(self.repo_root).as_posix(),
                "available": False,
            }
            try:
                cases = list(ET.parse(junit_path).getroot().iter("testcase"))
                counts = {
                    tag: sum(case.find(tag) is not None for case in cases)
                    for tag in ("failure", "error", "skipped")
                }
                junit.update(
                    available=True,
                    tests=len(cases),
                    executed=len(cases) - counts["skipped"],
                    **counts,
                )
                if junit["executed"] <= 0 or counts["failure"] or counts["error"]:
                    if result["status"] == "passed":
                        result["status"] = "failed"
                    result["output"] += (
                        "\nRuntime rejected empty, all-skipped or failing JUnit evidence."
                    )
            except (OSError, ET.ParseError) as exc:
                junit["error"] = str(exc)
                if result["status"] == "passed":
                    result["status"] = "failed"
                result["output"] += "\nRuntime rejected missing or invalid JUnit evidence."
            result["junit"] = junit
        self.approved_execution.append(result)
        self.event(
            "approved_execution",
            {
                "kind": kind,
                "id": action_id,
                "status": result["status"],
                "exit_code": result["exit_code"],
            },
        )
        return result

    def run_approved_test(self, args: dict[str, Any]) -> dict[str, Any]:
        test_id = WORKER.require_string(args.get("test_id"), "test_id")
        if test_id != "focused-tests" or not self.packet["focused_tests"]:
            raise ReviewError(f"unregistered approved test id: {test_id}")
        profile = self.validation_profile()
        python = str(profile.get("python") or self.config.get("python") or sys.executable)
        pytest_argv = profile.get("pytest_argv", ["-B", "-m", "pytest"])
        if not isinstance(pytest_argv, list) or not all(
            isinstance(item, str) for item in pytest_argv
        ):
            raise ReviewError("validation profile pytest_argv must be a string array")
        junit_path = self.review_root / f"approved-tests-{len(self.approved_execution) + 1}.xml"
        if junit_path.exists():
            raise ReviewError("approved test evidence already exists; never overwrite history")
        return self._run_approved(
            "test",
            test_id,
            [python, *pytest_argv, *self.packet["focused_tests"], f"--junitxml={junit_path}"],
            junit_path=junit_path,
        )

    def run_approved_static_check(self, args: dict[str, Any]) -> dict[str, Any]:
        check_id = WORKER.require_string(args.get("check_id"), "check_id")
        profile = self.validation_profile()
        matches = [
            item
            for item in profile.get("commands", [])
            if isinstance(item, dict) and item.get("id") == check_id
        ]
        if len(matches) != 1:
            raise ReviewError(f"unregistered approved static check id: {check_id}")
        argv = matches[0].get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or not all(isinstance(item, str) for item in argv)
        ):
            raise ReviewError(f"approved static check has invalid argv: {check_id}")
        python = str(profile.get("python") or self.config.get("python") or sys.executable)
        expanded = [python if item == "{python}" else item for item in argv]
        return self._run_approved("static_check", check_id, expanded)

    def system_prompt(self) -> str:
        prompt = """You are a read-only code reviewer. Use one JSON action per turn:
READ_FILE, SEARCH, RUN_APPROVED_TEST, RUN_APPROVED_STATIC_CHECK, or REPORT.
Review the actual cumulative diff and executed validation against the packet; Coder
claims are not evidence. Read changed source and focused tests, follow relevant callers,
error paths and side effects, and report concrete bugs or test gaps beyond listed
obligations. Escalate missing readable context or conflicting architecture/security
evidence. Never edit, use arbitrary commands, Git, or delegation. Execute only ids
listed in approved_execution and never claim an unexecuted check passed.
Passing focused tests do not prove untested inputs. For each added conditional or
early return in the cumulative diff, check whether it bypasses required behavior
or validation on an untested path before choosing pass_to_primary.
For changed exception handlers, trace both the original failure and failures of
cleanup operations (rollback, release, close, compensating writes). An awaited
cleanup call can raise before a later raise/return executes. Check which exception
actually reaches the caller, what state remains, and whether the packet requires
preserving the original error. A bare raise after cleanup alone does not prove
that guarantee. Assess the contract, not a preferred implementation shape; do not
invent a defect when the contract permits cleanup errors or source handles them.
Explain uncovered error-path reasoning in the relevant contract_review evidence.

Review this implementation unit, not premature completion of the whole feature.
Use owned_contract_ids and required_behavior to distinguish a defect of this unit
from unfinished behavior explicitly owned by a separate pending unit. Do not
assign that other unit's known pending work to an owned contract merely because
its caller is readable. Example: a correct collector preserves each fetched
value, while an unchanged receipt caller still passes raw labels; if the packet
explicitly assigns receipt composition elsewhere, that pending caller is not a
collector rework finding. Record pending integration uncertainty in
unverified_claims; the unit pass never accepts the whole feature.
Counterexample: if the changed collector drops zero values or changes exception
propagation, report the owned-contract defect even when the caller is unchanged
or read-only. Read-only location alone never excludes a genuine regression.
If the packet does not establish ownership or a cross-unit requirement conflicts,
escalate with evidence instead of assuming pending work is safe or requiring
an out-of-scope implementation.

REPORT arguments: decision, findings, verified_contract_ids, unverified_claims,
ordering_review, contract_review, verified_check_ids. Pass requires no findings,
all owned contracts and configured checks verified. Each finding needs id,
severity, category, path, line, evidence, contract_id, suggested_fix. For high
risk or verify_in_review feedback, give one contract_review per required
review_obligation with source_ref {path,start_line,end_line} pointing to actually
read lines and a whole-obligation explanation. The runtime materializes exact
source text; do not copy source_quote. contract_review.status must be exactly
"verified", "violated", or "uncertain"; for a contract-breaking rework finding,
use "violated". Otherwise contract_review may be []. Use the short
constraint_id values from ordering_constraints. Required order needs read source
evidence; forbidden order may use read source or cumulative diff. Pass only when
all constraints are verified. If evidence is missing, choose rework or escalate.
"""
        if self.config.get("reviewer_assessment_protocol", False):
            start = prompt.index("REPORT arguments:")
            prompt = (
                prompt[:start]
                + """REPORT arguments: assessment, findings, verified_contract_ids, unverified_claims,
ordering_review, contract_review, verified_check_ids. Choose the nature of the issue first:
- consistent: implementation satisfies the owned hard contract.
- optional_test_gap: additional test would be useful but is not a hard requirement and no concrete implementation violation exists; put advice in unverified_claims, not defect findings.
- implementation_defect: source violates a satisfiable owned requirement; give concrete source-backed defect findings.
- required_test_gap: an explicitly required test is missing; give the specific unmet test obligation.
- contract_conflict: requirements are incompatible, or authority/ownership conflicts need Primary to revise the contract; do not propose an implementation that silently changes an invariant.
- insufficient_evidence: scope or observations cannot support a decision; name the unresolved evidence.
The runtime maps your explicit assessment to pass_to_primary, rework or escalate. It does
not infer the assessment from keywords, source or tests. No automatic Coder rework is allowed.
Consistent/optional_test_gap require no defect findings, all owned contracts and configured
checks verified, and current complete displayed evidence. Defect findings need id, severity,
category, path, line, evidence, contract_id, suggested_fix. For required review_obligations,
select actual read evidence and give independent contract-specific reasoning; status is
verified, violated or uncertain. A contract conflict must not become a piecewise fix that
abandons one of the simultaneous requirements. Ordering review uses real constraint_id,
status, evidence_type, path, line and evidence; required order needs actually read source,
forbidden order may use read source or actual cumulative diff. Pass requires all ordering
constraints verified. Never populate a verification claim solely because a field is required.
"""
            )
        strength = self.config.get("reviewer_reasoning_strength")
        prompt += (
            "For a contract obligation spanning an anchor and distant implementation, use "
            "source_refs: an array of 1 to 3 actually read source_ref ranges, each at most "
            "20 lines. One range must contain the required source_anchor; other ranges "
            "must support the semantic reasoning. Single source_ref remains supported. "
            "The runtime materializes every quote; never invent quotes or unread ranges.\n"
        )
        if self.config.get("reviewer_evidence_ids", False):
            prompt = prompt.replace(
                "review_obligation with source_ref {path,start_line,end_line} pointing to actually\nread lines",
                "review_obligation with evidence_ids selected from citation_evidence in READ_FILE observations",
            )
            begin = prompt.index("For a contract obligation spanning an anchor")
            finish = prompt.index("\n", begin)
            prompt = (
                prompt[:begin]
                + (
                    "For contract_review select one to three runtime-issued evidence_ids from actually "
                    "displayed READ_FILE ranges, including the required source_anchor and relevant "
                    "implementation. Use only obligation_id, status, evidence_ids, evidence in each "
                    "entry. IDs prove display, not correctness; choose status and explain the whole "
                    "obligation independently. The runtime derives exact quotes for your selected IDs."
                )
                + prompt[finish:]
            )
        if strength is not None:
            if not isinstance(strength, str) or strength not in {"low", "medium", "high", "xhigh"}:
                raise ReviewError("reviewer_reasoning_strength must be low, medium, high, or xhigh")
            prompt += f"Reasoning strength: {strength}.\n"
        if self.config.get("reviewer_native_tools") is True:
            prompt += (
                "Use exactly one provided native tool call per turn; its function name is the "
                "action and its arguments are the action arguments. Never type native tool "
                "syntax in assistant text. The runtime still enforces every action boundary.\n"
            )
        return prompt

    def ordering_constraints(self) -> list[dict[str, Any]]:
        return [
            {
                "id": f"RO-{index}",
                "kind": "required_order",
                "text": item,
                "allowed_evidence_types": ["source"],
            }
            for index, item in enumerate(self.packet["required_order"], 1)
        ] + [
            {
                "id": f"FO-{index}",
                "kind": "forbidden_ordering",
                "text": item,
                "allowed_evidence_types": ["source", "diff"],
            }
            for index, item in enumerate(self.packet["forbidden_orderings"], 1)
        ]

    def review_obligations(self) -> list[dict[str, Any]]:
        obligations = [
            {
                "id": item["id"],
                "kind": "required_behavior",
                "text": item["text"],
                **(
                    {"implementation_ref": item["implementation_ref"]}
                    if "implementation_ref" in item
                    else {}
                ),
            }
            for item in self.packet["required_behavior"]
            if item["id"] in self.packet["owned_contract_ids"]
        ]
        for index, feedback in enumerate(self.packet.get("review_feedback", []), 1):
            if not isinstance(feedback, dict) or feedback.get("verify_in_review") is not True:
                continue
            finding_id = WORKER.require_identifier(
                feedback.get("finding_id"), f"review_feedback[{index}].finding_id"
            )
            contract_id = WORKER.require_string(
                feedback.get("contract_id"), f"review_feedback[{index}].contract_id"
            )
            if contract_id not in self.packet["owned_contract_ids"]:
                raise ReviewError(f"review feedback references unowned contract: {contract_id}")
            source_anchor = WORKER.require_string(
                feedback.get("source_anchor"), f"review_feedback[{index}].source_anchor"
            )
            obligations.append(
                {
                    "id": f"RF-{finding_id}",
                    "kind": "focused_rework",
                    "text": WORKER.require_string(
                        feedback.get("text"), f"review_feedback[{index}].text"
                    ),
                    "source_anchor": source_anchor,
                }
            )
        ids = [item["id"] for item in obligations]
        if len(ids) != len(set(ids)):
            raise ReviewError("review obligation ids must be unique")
        return obligations

    def diff_paths(self) -> list[str]:
        return sorted(
            {line[6:] for line in self.diff.splitlines() if line.startswith(("+++ b/", "--- a/"))}
        )

    def search_hint_action(self) -> dict[str, Any]:
        for path in self.diff_paths():
            try:
                relative, resolved = self._assert_read_allowed(path)
                if not resolved.is_file():
                    continue
                query = next(
                    (
                        line.strip()[:100]
                        for line in resolved.read_text(encoding="utf-8-sig").splitlines()
                        if line.strip()
                    ),
                    None,
                )
                if query:
                    return {"action": "SEARCH", "arguments": {"query": query, "path": relative}}
            except (OSError, UnicodeError, ReviewError, SAFE_EDIT.SafeEditError):
                continue
        return {"action": "SEARCH", "arguments": {"query": self.packet["goal"][:100]}}

    def empty_search_repair(self) -> dict[str, Any]:
        return {
            "suggested_action": self.search_hint_action(),
            "instruction": (
                "SEARCH requires a non-empty literal query. Send suggested_action exactly, "
                "inspect the bounded result, then continue the review."
            ),
        }

    def report_repair(self, error: str, args: dict[str, Any]) -> dict[str, Any]:
        valid_obligation_ids = [item["id"] for item in self.review_obligations()]
        repair: dict[str, Any] = {
            "valid_constraint_ids": [item["id"] for item in self.ordering_constraints()],
            "valid_obligation_ids": valid_obligation_ids,
        }
        if self.assessment_protocol and "assessment" in error:
            repair["valid_assessments"] = list(ASSESSMENT_DECISIONS)
            repair["instruction"] = (
                "Choose one explicit issue assessment; do not submit decision as well. Preserve your independent evidence and claim."
            )
            return repair
        if self.evidence_ids_enabled and "evidence_ids" in error:
            repair["citation_evidence"] = [
                {"id": key, **value} for key, value in self.evidence_catalog.items()
            ]
            repair["instruction"] = (
                "Select 1 to 3 distinct IDs already issued by READ_FILE. Do not combine IDs "
                "with another citation representation. Preserve your independent claim and reasoning."
            )
            return repair
        if error == "decision must be pass_to_primary, rework, or escalate":
            repair["valid_decisions"] = ["pass_to_primary", "rework", "escalate"]
            repair["instruction"] = (
                "Set decision to exactly one valid_decisions value: pass_to_primary only "
                "when the evidence supports every owned contract, rework for concrete "
                "findings, or escalate when evidence is insufficient."
            )
        elif "requires one successful SEARCH" in error:
            repair["required_actions"] = [self.search_hint_action()]
            repair["instruction"] = (
                "Execute the required SEARCH once, inspect its bounded results, then retry REPORT."
            )
        elif "requires successful approved execution ids" in error:
            catalog = self.approved_execution_catalog()
            passed = {
                (item.get("kind"), item.get("id"))
                for item in self.approved_execution
                if item.get("status") == "passed"
            }
            required_actions = []
            for item in catalog["tests"]:
                if ("test", item["id"]) not in passed:
                    required_actions.append(
                        {"action": item["action"], "arguments": item["arguments"]}
                    )
            for item in catalog["static_checks"]:
                if ("static_check", item["id"]) not in passed:
                    required_actions.append(
                        {"action": item["action"], "arguments": item["arguments"]}
                    )
            repair["required_actions"] = required_actions
            repair["instruction"] = (
                "Execute each required_actions item, one action per turn, before retrying "
                "REPORT. Do not report pass until every registered execution returns passed."
            )
        elif "requires acknowledgement of every configured check id" in error:
            repair["required_verified_check_ids"] = [
                item.get("id") for item in self.validation.get("configured_checks", [])
            ]
            repair["instruction"] = (
                "Retry REPORT with verified_check_ids exactly equal to "
                "required_verified_check_ids; preserve the already grounded findings and citations."
            )
        elif "contract_review has unknown or duplicate obligation_id" in error:
            submitted = [
                item.get("obligation_id")
                for item in args.get("contract_review", [])
                if isinstance(item, dict)
            ]
            repair["unknown_obligation_ids"] = sorted(
                {str(item) for item in submitted if item not in valid_obligation_ids}
            )
            repair["duplicate_obligation_ids"] = sorted(
                {str(item) for item in submitted if submitted.count(item) > 1}
            )
            repair["instruction"] = (
                "Use only valid_obligation_ids, once each. For high-risk pass, cite "
                "actual READ_FILE source evidence for every required obligation."
            )
        elif error == "contract_review must choose source_ref or source_refs, not both":
            repair["instruction"] = (
                "Submit only source_refs, an array of actually read bounded ranges. "
                "Remove source_ref entirely. Do not change the claim to fit a citation; "
                "all original range, anchor, freshness and semantic requirements remain."
            )
        elif "contract_review status must be" in error:
            repair["instruction"] = (
                "Each contract_review status must be exactly verified, violated, or uncertain. "
                "Omit optional contract_review entries for small/medium units."
            )
        elif match := re.fullmatch(
            r"contract_review (\S+) source_quote must contain the required source_anchor", error
        ):
            obligation = next(
                (item for item in self.review_obligations() if item["id"] == match.group(1)),
                {},
            )
            anchor = obligation.get("source_anchor")
            repair["obligation_id"] = match.group(1)
            repair["required_source_anchor"] = anchor
            if isinstance(anchor, str) and anchor:
                for path in self.diff_paths():
                    try:
                        relative, resolved = self._assert_read_allowed(path)
                        lines = resolved.read_text(encoding="utf-8-sig").splitlines()
                    except (OSError, UnicodeError, ReviewError, SAFE_EDIT.SafeEditError):
                        continue
                    line = next((n for n, text in enumerate(lines, 1) if anchor in text), None)
                    if line is not None:
                        expected = self.expected_inputs.get(relative, {})
                        already_read = line in self.read_lines.get(
                            relative, set()
                        ) and expected.get("sha256") == RUN_STATE.sha256_bytes(
                            resolved.read_bytes()
                        )
                        repair["anchor_already_read"] = already_read
                        if not already_read:
                            repair["suggested_action"] = {
                                "action": "READ_FILE",
                                "arguments": {
                                    "path": relative,
                                    "start_line": line,
                                    "end_line": line,
                                },
                            }
                        repair["anchor_citation"] = {
                            "path": relative,
                            "line": line,
                            "exact_source_quote": lines[line - 1].strip(),
                        }
                        repair["anchor_source_ref"] = {
                            "path": relative,
                            "start_line": line,
                            "end_line": line,
                        }
                        break
            repair["instruction"] = (
                (
                    "This current anchor line was already read. Do not reread it; correct "
                    "REPORT using anchor_source_ref plus actually read semantic ranges. "
                    if repair.get("anchor_already_read")
                    else "Read suggested_action before citing anchor_citation for this obligation. "
                    if "suggested_action" in repair
                    else "Locate and read the required anchor within readable scope before citing it. "
                )
                + "The anchor only identifies the reviewed symbol, not proof of semantics: "
                "independently inspect its implementation, tests and callers, and explain "
                "the evidence. Do not mark verified merely to satisfy citation shape. "
                "Use source_refs with anchor_source_ref and up to two actually read "
                "implementation ranges (each at most 20 lines); remove an obsolete single "
                "source_ref when switching to source_refs. "
                "If the anchor or semantic evidence is unavailable, escalate to Primary."
            )
        elif error.startswith("verified_contract_ids contradicts "):
            repair["conflicting_contract_ids"] = error.rsplit(": ", 1)[-1].split(", ")
            repair["instruction"] = (
                "A whole contract cannot simultaneously be verified and have a finding or "
                "an uncertain/violated contract_review. Reconcile the actual source evidence; "
                "remove unsupported verification, or withdraw a disproven finding. Do not "
                "invent certainty or change a semantic verdict just to satisfy this gate. "
                "If the evidence remains uncertain, escalate rather than accepting."
            )
        elif match := re.fullmatch(
            r"contract_review (\S+) requires bound implementation citation", error
        ):
            obligation = next(
                (item for item in self.review_obligations() if item["id"] == match.group(1)), {}
            )
            binding = obligation.get("implementation_ref")
            repair["obligation_id"] = match.group(1)
            repair["required_implementation_ref"] = binding
            if isinstance(binding, dict):
                try:
                    relative, source = self._assert_read_allowed(binding["path"])
                    text = source.read_text(encoding="utf-8-sig")
                    module = WORKER.citation_binding()
                    lines = module.statement_lines(text, binding["symbol"])
                    repair["eligible_evidence_ids"] = [
                        key
                        for key, ref in self.evidence_catalog.items()
                        if module.covers(binding, text, [ref])
                    ]
                    if not repair["eligible_evidence_ids"]:
                        first = min(lines)
                        repair["suggested_action"] = {
                            "action": "READ_FILE",
                            "arguments": {
                                "path": relative,
                                "start_line": max(1, first - 1),
                                "end_line": first,
                            },
                        }
                except (
                    OSError,
                    UnicodeError,
                    ValueError,
                    ReviewError,
                    SAFE_EDIT.SafeEditError,
                ) as exc:
                    repair["binding_unavailable"] = str(exc)
        elif "contract_review.source_ref must name a real range" in error:
            repair["read_source_bounds"] = {
                path: {"first_line": min(numbers), "last_line": max(numbers)}
                for path, numbers in self.read_lines.items()
                if numbers
            }
            displayed_ranges = {}
            for path, numbers in self.read_lines.items():
                ranges = []
                for number in sorted(numbers):
                    if not ranges or number != ranges[-1]["end_line"] + 1:
                        ranges.append({"start_line": number, "end_line": number})
                    else:
                        ranges[-1]["end_line"] = number
                if ranges:
                    displayed_ranges[path] = ranges[:12]
            repair["displayed_source_ranges"] = displayed_ranges
            invalid_refs = []
            for item in args.get("contract_review", []):
                if not isinstance(item, dict):
                    continue
                refs = item.get("source_refs", [item.get("source_ref")])
                if not isinstance(refs, list):
                    continue
                for ref in refs:
                    if not isinstance(ref, dict):
                        continue
                    start, end = ref.get("start_line"), ref.get("end_line")
                    if (
                        type(start) is not int
                        or type(end) is not int
                        or not 1 <= start <= end
                        or end - start >= 20
                    ):
                        invalid_refs.append(
                            {
                                "obligation_id": item.get("obligation_id"),
                                "path": ref.get("path"),
                                "start_line": start,
                                "end_line": end,
                                "maximum_lines_per_ref": 20,
                            }
                        )
            repair["invalid_source_refs"] = invalid_refs[:8]
            repair["instruction"] = (
                "Choose source_ref.start_line and end_line from actually displayed "
                "source lines within read_source_bounds, with start_line <= end_line "
                "and at most 20 consecutive lines. Cite the lines that support the "
                "obligation; do not invent a wider range. For each invalid_source_refs entry, "
                "choose only the necessary actually displayed lines. If an obligation needs "
                "distant evidence, use source_refs with up to three ranges of <=20 lines each "
                "and remove source_ref; do not discard needed evidence merely to shorten it. "
                "displayed_source_ranges preserves unread gaps; read_source_bounds alone "
                "does not prove that every intervening line was displayed."
            )
        elif match := re.search(
            r"(?:ordering_review|contract_review|finding) source line was not read: ([^:]+):(\d+)",
            error,
        ):
            line = int(match.group(2))
            repair["suggested_action"] = {
                "action": "READ_FILE",
                "arguments": {
                    "path": match.group(1),
                    "start_line": max(1, line - 4),
                    "end_line": line + 4,
                },
            }
            repair["instruction"] = (
                "Read the cited source line before retrying REPORT, or remove the "
                "unsupported source claim. Repeating REPORT unchanged will fail."
            )
        elif error.startswith("contract_review source was not read: "):
            path = error.split(": ", 1)[1]
            cited = next(
                (
                    item
                    for item in args.get("contract_review", [])
                    if isinstance(item, dict) and item.get("path") == path
                ),
                {},
            )
            line = cited.get("line")
            arguments: dict[str, Any] = {"path": path}
            if isinstance(line, int) and line > 0:
                arguments.update({"start_line": max(1, line - 4), "end_line": line + 4})
            repair["suggested_action"] = {"action": "READ_FILE", "arguments": arguments}
            repair["instruction"] = (
                "Read this exact source path before citing it in contract_review. "
                "Then verify that the displayed line supports the entire obligation."
            )
        elif error == "contract_review source_quote must match the cited source line":
            citation_fixes = []
            for item in args.get("contract_review", []):
                if not isinstance(item, dict):
                    continue
                path, line = item.get("path"), item.get("line")
                if not isinstance(path, str) or not isinstance(line, int) or line < 1:
                    continue
                try:
                    _relative, resolved = self._assert_read_allowed(path)
                    lines = resolved.read_text(encoding="utf-8-sig").splitlines()
                except (OSError, UnicodeError, ReviewError, SAFE_EDIT.SafeEditError):
                    continue
                if line <= len(lines) and item.get("source_quote") != lines[line - 1].strip():
                    fix = {
                        "obligation_id": item.get("obligation_id"),
                        "path": path,
                        "line": line,
                        "exact_source_quote": lines[line - 1].strip(),
                    }
                    citation_fixes.append(fix)
            if citation_fixes:
                repair["source_citation"] = citation_fixes[0]
                repair["citation_fixes"] = citation_fixes[:8]
            repair["instruction"] = (
                "For every citation_fixes entry, replace only that obligation's source_quote "
                "with exact_source_quote at the displayed path and line. Check that the actual "
                "line supports the obligation; otherwise report rework or escalate. Do not "
                "resubmit the previous REPORT unchanged or reread an already displayed range."
            )
        elif error == "diff evidence path must be an actual changed path":
            repair["actual_changed_paths"] = sorted(self.diff_paths())
            repair["diff_evidence_shape"] = {"path": "actual changed path or null", "line": None}
            repair["instruction"] = (
                "For diff evidence, path must be one of actual_changed_paths, or null for "
                "a genuine whole-cumulative-diff absence claim; line must be null. "
                "Do not cite readable but unchanged files as changed diff evidence. "
                "Required order still needs actual read source evidence. These path hints "
                "grant no source-read credit and do not establish any semantic constraint. "
                "If the actual diff does not support the claim, use source evidence after "
                "reading it, or report uncertainty rather than fabricating verification."
            )
        elif (
            "ordering_review.path must be a non-empty string" in error
            or "source evidence line must be a positive integer" in error
        ):
            repair["evidence_shapes"] = {
                "source": {
                    "path": "non-empty actually read source path",
                    "line": "positive actually read integer line",
                },
                "diff": {"path": "actual changed path or null", "line": None},
            }
            repair["ordering_entry_fields"] = [
                "constraint_id",
                "status",
                "evidence_type",
                "path",
                "line",
                "evidence",
            ]
            repair["ordering_shape_instruction"] = (
                "ordering_review uses flat path and line fields in each entry, not the "
                "nested source_ref/source_refs used by contract_review. Put path and line "
                "beside constraint_id. Do not copy contract_review's field layout here. "
                "This is field-shape guidance only, never a semantic verification."
            )
            repair["read_changed_source_paths"] = [
                path
                for path in self.diff_paths()
                if self.read_lines.get(path) and path not in self.focused_test_paths()
            ]
            repair["instruction"] = (
                "For evidence_type=source, path cannot be null or empty and line must be a "
                "positive integer from an actual READ_FILE observation. Choose the read source "
                "whose lines establish this constraint, or READ_FILE the needed source first. "
                "Required order needs source evidence. Forbidden order may instead use actual "
                "cumulative diff evidence with line=null. Do not mark a constraint verified "
                "merely to repair field shape; if evidence is insufficient, report escalate."
            )
        elif "observed approved execution failures" in error:
            repair["observed_execution_failures"] = [
                {key: item.get(key) for key in ("kind", "id", "status", "exit_code")}
                for item in self.approved_execution
                if item.get("status") != "passed"
            ]
            repair["instruction"] = (
                "Choose rework for a concrete defect or escalate for unresolved infrastructure "
                "or conflicting evidence. Explain the actual failed execution, do not claim "
                "it passed. Repeating an execution cannot erase an observed failure in this "
                "review; Primary must resolve it before a new review invocation."
            )
        elif "diff evidence must not claim a source line" in error:
            repair["evidence_shapes"] = {
                "source": {
                    "path": "actually read source path",
                    "line": "positive actually read line",
                },
                "diff": {"path": "actual changed path or null", "line": None},
            }
            repair["instruction"] = (
                "For evidence_type=diff, set line to null and cite the actual cumulative "
                "diff; otherwise use evidence_type=source after READ_FILE."
            )
        elif "every ordering constraint" in error:
            entries = args.get("ordering_review", [])
            supplied = {
                item["constraint_id"]: item
                for item in (entries if isinstance(entries, list) else [])
                if isinstance(item, dict) and isinstance(item.get("constraint_id"), str)
            }
            repair["unverified_constraints"] = [
                {
                    "constraint_id": item["id"],
                    "text": item["text"],
                    "allowed_evidence_types": item["allowed_evidence_types"],
                }
                for item in self.ordering_constraints()
                if supplied.get(item["id"], {}).get("status") != "verified"
            ]
            repair["instruction"] = (
                "Do not omit ordering_review when retrying. For a pass, independently assess "
                "every listed constraint and include its exact ID once with verified evidence. "
                "Required order needs read source path/line. Forbidden order also permits "
                "actual cumulative diff evidence with line=null. If any constraint is violated "
                "or uncertain, choose rework or escalate; do not manufacture verification."
            )
        elif error.startswith("pass requires displayed coverage:"):
            missing = self.coverage_facts()["missing"]
            repair["coverage_missing"] = missing[:8]
            target = next((item for item in missing if item.get("line_count", 1) > 0), None)
            if target:
                start = max(1, target.get("start_line", 1))
                end = target.get("end_line", start + target.get("line_count", 40) - 1)
                repair["suggested_action"] = {
                    "action": "READ_FILE",
                    "arguments": {
                        "path": target["path"],
                        "start_line": start,
                        "end_line": min(end, start + 39),
                    },
                }
            repair["instruction"] = (
                "Read missing bounded evidence or report unresolved; display coverage is not semantic verification."
            )
        elif "pass requires READ_FILE of at least one focused test file" in error:
            repair["suggested_action"] = {
                "action": "READ_FILE",
                "arguments": {"path": self.focused_test_paths()[0]},
            }
            repair["instruction"] = (
                "Read a focused test and assess what behavior it does and does not cover."
            )
        elif "pass requires READ_FILE of at least one changed source file" in error:
            changed = [path for path in self.diff_paths() if path.endswith(".py")]
            if changed:
                repair["suggested_action"] = {
                    "action": "READ_FILE",
                    "arguments": {"path": changed[0]},
                }
            repair["instruction"] = (
                "Read changed source and assess it independently before passing."
            )
        else:
            repair["instruction"] = (
                "Correct the reported field using the valid IDs and the initial REPORT "
                "template. Do not resend an unchanged invalid REPORT."
            )
        return repair

    def report_template(self) -> dict[str, Any]:
        result = {
            "action": "REPORT",
            "arguments": {
                "decision": "CHOOSE pass_to_primary, rework, or escalate AFTER reviewing",
                "findings": [],
                "verified_contract_ids": [],
                "unverified_claims": [],
                "verified_check_ids": [
                    item["id"]
                    for item in self.validation.get("configured_checks", [])
                    if item.get("status") == "passed"
                ],
                "contract_review": [
                    {
                        "obligation_id": item["id"],
                        "status": "CHOOSE verified, violated, or uncertain",
                        "source_ref": {
                            "path": "REPLACE WITH READABLE SOURCE PATH",
                            "start_line": 1,
                            "end_line": 1,
                        },
                        "evidence": "REPLACE WITH CONTRACT-SPECIFIC REASONING",
                    }
                    for item in self.review_obligations()
                    if self.packet["risk"]["unit"] == "high" or item["kind"] == "focused_rework"
                ],
                "ordering_review": [
                    {
                        "constraint_id": item["id"],
                        "status": "verified",
                        "evidence_type": "source" if item["kind"] == "required_order" else "diff",
                        "path": None,
                        "line": None,
                        "evidence": "REPLACE WITH ACTUAL EVIDENCE",
                    }
                    for item in self.ordering_constraints()
                ],
            },
        }
        if self.evidence_ids_enabled:
            for item in result["arguments"]["contract_review"]:
                item.pop("source_ref")
                item["evidence_ids"] = ["REPLACE WITH ACTUALLY DISPLAYED E-ID"]
        if self.assessment_protocol:
            result["arguments"].pop("decision")
            result["arguments"]["assessment"] = "CHOOSE issue nature AFTER independent review"
        return result

    def initial_payload(self) -> dict[str, Any]:
        # Re-entering an adapter must never rebase previously observed evidence.
        self._assert_observed_sources_current()
        max_diff = int(self.config.get("reviewer_initial_diff_chars", 24000))
        diff = self.diff[:max_diff]
        if len(diff) == len(self.diff):
            for hunk in self.coverage_hunks():
                self.displayed_diff_hunks.add(hunk["id"])
                path, resolved = self._assert_read_allowed(hunk["path"])
                if resolved.is_file():
                    self.observed_read_hashes.setdefault(
                        path, RUN_STATE.sha256_bytes(resolved.read_bytes())
                    )
        return {
            "identity": {
                "task_id": self.task_id,
                "unit_id": self.unit_id,
                "run_id": self.run_id,
                "review_id": self.review_id,
            },
            "risk": self.packet["risk"],
            "review_route": {
                "small": "primary_evidence_acceptance",
                "medium": "primary_lightweight_review",
                "high": "primary_full_review",
            }[self.packet["risk"]["unit"]],
            "owned_contract_ids": self.packet["owned_contract_ids"],
            "review_obligations": self.review_obligations(),
            "review_feedback": self.packet.get("review_feedback", []),
            "required_behavior": self.packet["required_behavior"],
            "acceptance_criteria": self.packet["acceptance_criteria"],
            "acceptance_scenarios": self.packet["acceptance_scenarios"],
            "required_order": self.packet["required_order"],
            "forbidden_orderings": self.packet["forbidden_orderings"],
            "ordering_constraints": self.ordering_constraints(),
            "changed_paths": self.diff_paths(),
            "report_template_replace_evidence_before_use": self.report_template(),
            "scope": self.packet["scope"],
            "runtime_validation": self.validation,
            "approved_execution": self.approved_execution_catalog(),
            "approved_execution_required_for_pass": bool(
                self.config.get("reviewer_require_approved_execution", False)
            ),
            "search_required_for_pass": bool(self.config.get("reviewer_require_search", False)),
            "cumulative_diff": diff,
            "diff_truncated": len(self.diff) > len(diff),
            "display_coverage": self.coverage_facts(),
        }

    def coverage_hunks(self) -> list[dict[str, Any]]:
        """Parse actual archived hunks; a header or SEARCH is not a displayed hunk."""
        hunks: list[dict[str, Any]] = []
        path = None
        for line in self.diff.splitlines():
            if line.startswith("+++ b/"):
                path = line[6:]
            elif line.startswith("--- a/"):
                path = line[6:]
            elif path and (match := re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)):
                start = int(match[1])
                count = int(match[2]) if match[2] is not None else 1
                hunks.append(
                    {
                        "id": f"hunk-{len(hunks) + 1}",
                        "path": path,
                        "start_line": start,
                        "line_count": count,
                    }
                )
        return hunks

    def coverage_facts(self) -> dict[str, Any]:
        self._assert_observed_sources_current()
        requirements: list[dict[str, Any]] = []
        for hunk in self.coverage_hunks():
            numbers = set(range(hunk["start_line"], hunk["start_line"] + hunk["line_count"]))
            displayed = hunk["id"] in self.displayed_diff_hunks
            read = bool(numbers) and numbers <= self.read_lines.get(hunk["path"], set())
            requirements.append(
                {
                    **hunk,
                    "displayed": displayed or read,
                    "via": "diff" if displayed else "read" if read else None,
                }
            )
        for path in self.diff_paths():
            if not any(item["path"] == path for item in requirements):
                # Binary/mode-only changes have no precise textual hunk evidence.
                requirements.append(
                    {"id": "changed-path:" + path, "path": path, "displayed": False, "via": None}
                )
        targets = self.request.get("coverage_targets")
        if targets is None:
            targets = [{"path": path} for path in self.focused_test_paths()]
        if not isinstance(targets, list):
            raise ReviewError("coverage_targets must be an array")
        for index, target in enumerate(targets):
            if not isinstance(target, dict):
                raise ReviewError("coverage target must be an object")
            path, resolved = self._assert_read_allowed(target.get("path"))
            if not resolved.is_file():
                raise ReviewError("coverage target does not exist: " + path)
            total = len(resolved.read_text(encoding="utf-8-sig").splitlines())
            start, end = target.get("start_line", 1), target.get("end_line", total)
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= total:
                raise ReviewError("coverage target requires a real source range")
            numbers = set(range(start, end + 1))
            requirements.append(
                {
                    "id": f"critical-{index + 1}",
                    "path": path,
                    "start_line": start,
                    "end_line": end,
                    "displayed": numbers <= self.read_lines.get(path, set()),
                    "via": "read" if numbers <= self.read_lines.get(path, set()) else None,
                }
            )
        return {
            "requirements": requirements,
            "missing": [item for item in requirements if not item["displayed"]],
            "semantic_understanding": "not_inferred_from_display",
        }

    def _canonical_contract_ref(self, ref: dict[str, Any]) -> dict[str, Any]:
        self._assert_observed_sources_current()
        path, resolved = self._assert_read_allowed(
            WORKER.require_string(ref.get("path"), "contract_review.path")
        )
        if path not in self.read_paths or not resolved.is_file():
            raise ReviewError(f"contract_review source was not read: {path}")
        source_bytes = resolved.read_bytes()
        source_hash = RUN_STATE.sha256_bytes(source_bytes)
        if self.observed_read_hashes.get(path) != source_hash:
            raise ReviewError("read source changed during citation: " + path)
        lines = source_bytes.decode("utf-8-sig").splitlines()
        start, end = ref.get("start_line"), ref.get("end_line")
        if (
            type(start) is not int
            or type(end) is not int
            or not 1 <= start <= end <= len(lines)
            or end - start >= 20
        ):
            raise ReviewError(
                "contract_review.source_ref must name a real range of at most 20 lines"
            )
        for line in range(start, end + 1):
            if line not in self.read_lines.get(path, set()):
                raise ReviewError(f"contract_review source line was not read: {path}:{line}")
        return {
            "path": path,
            "start_line": start,
            "end_line": end,
            "canonical_quote": "\n".join(lines[start - 1 : end]),
            "source_hash": "sha256:" + source_hash,
        }

    def validate_report(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self.assessment_protocol:
            if "assessment" in args:
                raise ReviewError("assessment transport is not enabled")
            return self._validate_report_core(args)
        assessment = args.get("assessment")
        if not isinstance(assessment, str) or assessment not in ASSESSMENT_DECISIONS:
            raise ReviewError("assessment must select a valid issue nature")
        if "decision" in args:
            raise ReviewError("assessment cannot be combined with decision")
        normalized = json.loads(json.dumps(args))
        normalized.pop("assessment")
        normalized["decision"] = ASSESSMENT_DECISIONS[assessment]
        result = self._validate_report_core(normalized)
        result["model_assessment"] = assessment
        return result

    def _validate_report_core(self, args: dict[str, Any]) -> dict[str, Any]:
        self._assert_observed_sources_current()
        args = json.loads(json.dumps(args))
        for item in (
            args.get("contract_review", [])
            if isinstance(args.get("contract_review", []), list)
            else []
        ):
            if not isinstance(item, dict) or "evidence_ids" not in item:
                continue
            ids = item["evidence_ids"]
            if not self.evidence_ids_enabled:
                raise ReviewError("evidence_ids transport is not enabled")
            if any(
                field in item
                for field in ("source_ref", "source_refs", "path", "line", "source_quote")
            ):
                raise ReviewError(
                    "evidence_ids cannot be combined with another citation representation"
                )
            if (
                not isinstance(ids, list)
                or not 1 <= len(ids) <= 3
                or any(not isinstance(key, str) or key not in self.evidence_catalog for key in ids)
                or len(set(ids)) != len(ids)
            ):
                raise ReviewError("evidence_ids must select 1 to 3 distinct actually displayed IDs")
            item["source_refs"] = [
                {
                    field: self.evidence_catalog[key][field]
                    for field in ("path", "start_line", "end_line")
                }
                for key in ids
            ]
            item.pop("evidence_ids")
        decision = args.get("decision")
        if decision not in {"pass_to_primary", "rework", "escalate"}:
            raise ReviewError("decision must be pass_to_primary, rework, or escalate")
        findings = args.get("findings")
        if not isinstance(findings, list):
            raise ReviewError("findings must be an array")
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, finding in enumerate(findings, 1):
            if not isinstance(finding, dict):
                raise ReviewError(f"findings[{index}] must be an object")
            finding_id = WORKER.require_identifier(finding.get("id"), f"findings[{index}].id")
            if finding_id in seen:
                raise ReviewError("finding ids must be unique")
            seen.add(finding_id)
            severity = WORKER.require_string(
                finding.get("severity"), f"findings[{index}].severity"
            ).lower()
            if severity not in {"low", "medium", "high", "critical"}:
                raise ReviewError("finding severity must be low, medium, high, or critical")
            path = finding.get("path")
            if path is not None:
                path, _resolved = self._assert_read_allowed(path)
            line = finding.get("line")
            if line is not None and (type(line) is not int or line < 1):
                raise ReviewError("finding line must be a positive integer or null")
            if path is not None and line is not None:
                if line not in self.read_lines.get(path, set()):
                    raise ReviewError(f"finding source line was not read: {path}:{line}")
            contract_id = finding.get("contract_id")
            if contract_id is not None and contract_id not in self.packet["owned_contract_ids"]:
                raise ReviewError(f"finding references unknown owned contract: {contract_id}")
            normalized.append(
                {
                    "id": finding_id,
                    "severity": severity,
                    "category": WORKER.require_string(
                        finding.get("category"), f"findings[{index}].category"
                    ),
                    "path": path,
                    "line": line,
                    "evidence": WORKER.require_string(
                        finding.get("evidence"), f"findings[{index}].evidence"
                    ),
                    "contract_id": contract_id,
                    "suggested_fix": WORKER.require_string(
                        finding.get("suggested_fix"), f"findings[{index}].suggested_fix"
                    ),
                }
            )
        if decision == "pass_to_primary" and normalized:
            raise ReviewError("pass_to_primary requires an empty findings array")
        if decision == "rework" and not normalized:
            raise ReviewError("rework requires at least one finding")
        verified = WORKER.require_string_list(
            args.get("verified_contract_ids", []), "verified_contract_ids"
        )
        unknown = sorted(set(verified) - set(self.packet["owned_contract_ids"]))
        if unknown:
            raise ReviewError("verified_contract_ids contains unknown ids: " + ", ".join(unknown))
        missing = sorted(set(self.packet["owned_contract_ids"]) - set(verified))
        if decision == "pass_to_primary" and missing:
            raise ReviewError(
                "pass_to_primary requires every owned contract to be verified: "
                + ", ".join(missing)
            )
        constraints = {item["id"]: item for item in self.ordering_constraints()}
        ordering_review = args.get("ordering_review", [])
        if not isinstance(ordering_review, list):
            raise ReviewError("ordering_review must be an array")
        reviewed: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(ordering_review, 1):
            if not isinstance(item, dict):
                raise ReviewError(f"ordering_review[{index}] must be an object")
            constraint_id = WORKER.require_string(
                item.get("constraint_id"), "ordering_review.constraint_id"
            )
            if constraint_id not in constraints or constraint_id in reviewed:
                raise ReviewError(
                    "ordering_review has unknown or duplicate constraint_id; expected: "
                    + ", ".join(constraints)
                )
            status = item.get("status")
            if status not in {"verified", "violated", "uncertain"}:
                raise ReviewError("ordering_review status must be verified, violated, or uncertain")
            evidence_type = item.get("evidence_type")
            if evidence_type not in constraints[constraint_id]["allowed_evidence_types"]:
                raise ReviewError(
                    f"{constraint_id} evidence_type must be one of "
                    + ", ".join(constraints[constraint_id]["allowed_evidence_types"])
                )
            path = item.get("path")
            line = item.get("line")
            if evidence_type == "source":
                path, _resolved = self._assert_read_allowed(
                    WORKER.require_string(path, "ordering_review.path")
                )
                if type(line) is not int or line < 1:
                    raise ReviewError("source evidence line must be a positive integer")
                source_lines = _resolved.read_text(encoding="utf-8-sig").splitlines()
                if line > len(source_lines):
                    raise ReviewError("source evidence line is beyond the end of the file")
                if line not in self.read_lines.get(path, set()):
                    raise ReviewError(f"ordering_review source line was not read: {path}:{line}")
            else:
                if path is not None and path not in self.diff_paths():
                    raise ReviewError("diff evidence path must be an actual changed path")
                if line is not None:
                    raise ReviewError("diff evidence must not claim a source line")
            evidence = WORKER.require_string(item.get("evidence"), "ordering_review.evidence")
            if "REPLACE WITH ACTUAL EVIDENCE" in evidence:
                raise ReviewError("ordering_review still contains template evidence")
            reviewed[constraint_id] = {
                "constraint_id": constraint_id,
                "constraint": constraints[constraint_id]["text"],
                "status": status,
                "evidence_type": evidence_type,
                "path": path,
                "line": line,
                "evidence": evidence,
            }
        if decision == "pass_to_primary" and (
            set(reviewed) != set(constraints)
            or any(item["status"] != "verified" for item in reviewed.values())
        ):
            raise ReviewError(
                "pass_to_primary requires verified evidence of an allowed type for every ordering constraint"
            )
        obligations = {item["id"]: item for item in self.review_obligations()}
        contract_review = args.get("contract_review", [])
        if not isinstance(contract_review, list):
            raise ReviewError("contract_review must be an array")
        required_obligations = {
            item_id
            for item_id, item in obligations.items()
            if self.packet["risk"]["unit"] == "high"
            or item["kind"] == "focused_rework"
            or item.get("implementation_ref") is not None
        }
        # Small/medium units need not submit optional contract_review entries.
        # Once supplied, however, their claims must not be silently discarded:
        # explicit violated/uncertain evidence cannot coexist with a pass.
        verified_obligations: dict[str, dict[str, Any]] = {}
        for item in contract_review:
            if not isinstance(item, dict):
                raise ReviewError("contract_review items must be objects")
            obligation_id = WORKER.require_string(item.get("obligation_id"), "obligation_id")
            if obligation_id not in obligations or obligation_id in verified_obligations:
                raise ReviewError("contract_review has unknown or duplicate obligation_id")
            status = item.get("status")
            if status not in {"verified", "violated", "uncertain"}:
                raise ReviewError("contract_review status must be verified, violated, or uncertain")
            source_ref = item.get("source_ref")
            canonical_refs = []
            if "source_refs" in item:
                refs = item["source_refs"]
                if (
                    not isinstance(refs, list)
                    or not 1 <= len(refs) <= 3
                    or not all(isinstance(ref, dict) for ref in refs)
                ):
                    raise ReviewError(
                        "contract_review.source_refs must contain 1 to 3 source_ref objects"
                    )
                if source_ref is not None:
                    raise ReviewError(
                        "contract_review must choose source_ref or source_refs, not both"
                    )
                canonical_refs = [self._canonical_contract_ref(ref) for ref in refs]
                source_ref = refs[0]
            if source_ref is not None and not isinstance(source_ref, dict):
                raise ReviewError("contract_review.source_ref must be an object")
            raw_path = source_ref.get("path") if isinstance(source_ref, dict) else item.get("path")
            path, resolved = self._assert_read_allowed(
                WORKER.require_string(raw_path, "contract_review.path")
            )
            if path not in self.read_paths or not resolved.is_file():
                raise ReviewError(f"contract_review source was not read: {path}")
            source_bytes = resolved.read_bytes()
            source_hash = RUN_STATE.sha256_bytes(source_bytes)
            if self.observed_read_hashes.get(path) != source_hash:
                raise ReviewError("read source changed during citation: " + path)
            lines = source_bytes.decode("utf-8-sig").splitlines()
            if isinstance(source_ref, dict):
                line = source_ref.get("start_line")
                end_line = source_ref.get("end_line")
                if (
                    type(line) is not int
                    or type(end_line) is not int
                    or not 1 <= line <= end_line <= len(lines)
                    or end_line - line >= 20
                ):
                    raise ReviewError(
                        "contract_review.source_ref must name a real range of at most 20 lines"
                    )
                if any(
                    number not in self.read_lines.get(path, set())
                    for number in range(line, end_line + 1)
                ):
                    raise ReviewError(f"contract_review source line was not read: {path}:{line}")
                source_quote = "\n".join(lines[line - 1 : end_line])
            else:
                line = item.get("line")
                end_line = line
                if type(line) is not int or not 1 <= line <= len(lines):
                    raise ReviewError("contract_review line must be a real positive source line")
                if line not in self.read_lines.get(path, set()):
                    raise ReviewError(f"contract_review source line was not read: {path}:{line}")
                source_quote = WORKER.require_string(
                    item.get("source_quote"), "contract_review.source_quote"
                )
                if source_quote != lines[line - 1].strip():
                    raise ReviewError(
                        "contract_review source_quote must match the cited source line"
                    )
            required_anchor = obligations[obligation_id].get("source_anchor")
            anchor_quotes = [ref["canonical_quote"] for ref in canonical_refs] or [source_quote]
            if required_anchor and not any(required_anchor in quote for quote in anchor_quotes):
                raise ReviewError(
                    f"contract_review {obligation_id} source_quote must contain "
                    "the required source_anchor"
                )
            binding = obligations[obligation_id].get("implementation_ref")
            if binding is not None and status == "verified":
                # Selected evidence, not every previously read file, must contain the
                # Primary-bound implementation. Tests may supplement but not replace it.
                _, implementation = self._assert_read_allowed(binding["path"])
                selected = canonical_refs or [
                    {"path": path, "start_line": line, "end_line": end_line}
                ]
                try:
                    supported = WORKER.citation_binding().covers(
                        binding, implementation.read_text(encoding="utf-8-sig"), selected
                    )
                except (OSError, UnicodeError, ValueError):
                    supported = False
                if not supported:
                    raise ReviewError(
                        f"contract_review {obligation_id} requires bound implementation citation"
                    )
            evidence = WORKER.require_string(item.get("evidence"), "contract_review.evidence")
            if evidence.startswith("REPLACE WITH"):
                raise ReviewError("contract_review still contains template evidence")
            verified_obligations[obligation_id] = {
                "obligation_id": obligation_id,
                "obligation": obligations[obligation_id]["text"],
                "status": status,
                "path": path,
                "line": line,
                "source_quote": source_quote,
                "source_ref": {
                    "path": path,
                    "start_line": line,
                    "end_line": end_line,
                },
                "canonical_quote": source_quote,
                "source_hash": "sha256:" + source_hash,
                "evidence": evidence,
            }
            if canonical_refs:
                verified_obligations[obligation_id]["source_refs"] = canonical_refs
            if binding is not None:
                verified_obligations[obligation_id]["implementation_ref"] = dict(binding)
        if decision == "pass_to_primary":
            if not required_obligations <= set(verified_obligations) or any(
                verified_obligations[item_id]["status"] != "verified"
                for item_id in required_obligations & set(verified_obligations)
            ):
                raise ReviewError(
                    "pass requires source-backed contract_review for every required "
                    "review_obligation: " + ", ".join(sorted(required_obligations))
                )
        contradictory = set(verified) & {
            item["contract_id"] for item in normalized if item["contract_id"] is not None
        }
        contradictory.update(
            set(verified)
            & {
                item_id
                for item_id, item in verified_obligations.items()
                if item["status"] != "verified" and item_id in self.packet["owned_contract_ids"]
            }
        )
        if contradictory:
            raise ReviewError(
                "verified_contract_ids contradicts findings or non-verified contract_review: "
                + ", ".join(sorted(contradictory))
            )
        configured_checks = self.validation.get("configured_checks", [])
        if not isinstance(configured_checks, list):
            raise ReviewError("runtime configured_checks must be an array")
        passed_check_ids = WORKER.require_string_list(
            args.get("verified_check_ids", []), "verified_check_ids"
        )
        expected_check_ids = [item.get("id") for item in configured_checks]
        if decision == "pass_to_primary":
            observed_failures = [
                f"{item.get('kind')}:{item.get('id')}:{item.get('status')}"
                for item in self.approved_execution
                if item.get("status") != "passed"
            ]
            if observed_failures:
                raise ReviewError(
                    "pass_to_primary contradicts observed approved execution failures: "
                    + ", ".join(observed_failures)
                    + "; choose rework or escalate with the actual evidence. "
                    "A retry success cannot erase a failure in this review invocation."
                )
            if self.validation.get("status") != "passed":
                raise ReviewError("pass_to_primary requires passed runtime validation")
            if any(item.get("status") != "passed" for item in configured_checks):
                raise ReviewError("pass_to_primary requires every configured check to pass")
            if sorted(passed_check_ids) != sorted(expected_check_ids):
                raise ReviewError(
                    "pass_to_primary requires acknowledgement of every configured check id"
                )
            if self.config.get("reviewer_require_search", False) and self.search_count < 1:
                raise ReviewError(
                    "pass_to_primary requires one successful SEARCH for compatibility qualification"
                )
            if self.config.get("reviewer_require_approved_execution", False):
                passed_execution = {
                    (item.get("kind"), item.get("id"))
                    for item in self.approved_execution
                    if item.get("status") == "passed"
                }
                required_execution = (
                    {("test", "focused-tests")} if self.packet["focused_tests"] else set()
                ) | {("static_check", item) for item in expected_check_ids}
                missing_execution = sorted(required_execution - passed_execution)
                if missing_execution:
                    raise ReviewError(
                        "pass_to_primary requires successful approved execution ids: "
                        + ", ".join(f"{kind}:{item}" for kind, item in missing_execution)
                    )
            if self.config.get("reviewer_require_source_and_test_reads", False):
                missing = self.coverage_facts()["missing"]
                if missing:
                    raise ReviewError(
                        "pass requires displayed coverage: "
                        + ", ".join(f"{item['id']}:{item['path']}" for item in missing[:8])
                        + " (changed hunks and focused test/call boundaries must be displayed)"
                    )
        unverified = WORKER.require_string_list(
            args.get("unverified_claims", []), "unverified_claims"
        )
        placeholders = {"none", "no", "n/a", "na", "nothing", "无", "没有"}
        if any(item.strip().lower() in placeholders for item in unverified):
            raise ReviewError(
                "unverified_claims must be an empty array when there are no unverified claims"
            )
        return {
            "schema_version": 1,
            "decision": decision,
            "identity": {
                "task_id": self.task_id,
                "unit_id": self.unit_id,
                "run_id": self.run_id,
                "review_id": self.review_id,
            },
            "risk": self.packet["risk"],
            "review_route": {
                "small": "primary_evidence_acceptance",
                "medium": "primary_lightweight_review",
                "high": "primary_full_review",
            }[self.packet["risk"]["unit"]],
            "findings": normalized,
            "verified_contract_ids": sorted(set(verified)),
            "ordering_review": list(reviewed.values()),
            "contract_review": list(verified_obligations.values()),
            "verified_check_ids": passed_check_ids,
            "unverified_claims": unverified,
            "runtime_facts": {
                "read_only": True,
                "inputs_unchanged": True,
                "read_paths": sorted(self.read_paths),
                "observed_read_hashes": dict(sorted(self.observed_read_hashes.items())),
                "approved_execution": self.approved_execution,
                "protocol_error_count": self.protocol_errors,
                "display_coverage": self.coverage_facts(),
            },
            "next_action_required": {
                "pass_to_primary": "primary_review_by_risk_route",
                "rework": "primary_adjudicate_review_findings",
                "escalate": "primary_takeover_or_replan",
            }[decision],
            "automatic_coder_rework_authorized": False,
        }

    def _prepass_challenge(self, report: dict[str, Any]) -> dict[str, Any] | None:
        if self.finding_challenge_pending and report.get("decision") == "rework":
            self.finding_challenge_pending = False
            self.prepass_challenge_pending = False
            self.deferred_report = None
            RUN_STATE.write_json_once(
                self.review_root / "provisional-report.json",
                {
                    "schema_version": 1,
                    "terminal": False,
                    "trigger": "finding_challenge",
                    "report": report,
                },
            )
            self.event(
                "finding_challenge_issued",
                {"finding_ids": [item["id"] for item in report["findings"]]},
            )
            self.prepass_challenge_context = {
                "status": "review_pending",
                "instruction": (
                    "Your provisional rework is not finalized. Attempt to falsify your own "
                    "finding before requesting an implementation change: trace the cited "
                    "operation together with its enclosing caller/control flow, and identify "
                    "a concrete input and observable contract violation. A helper need not "
                    "independently enforce a protection already supplied by its caller; "
                    "an unfamiliar but equivalent implementation is not a defect. Reconcile "
                    "contradictory explanations against the actual source and executed evidence. "
                    "Do not automatically withdraw a genuine defect: retain it with causal "
                    "evidence if the counterexample survives, withdraw it if disproven, or "
                    "escalate if unresolved. Submit a new REPORT subject to all existing "
                    "citation, freshness and validation gates. No additional execution or "
                    "model budget is authorized."
                ),
            }
            return self.prepass_challenge_context
        if not self.prepass_challenge_pending or report.get("decision") != "pass_to_primary":
            return None
        self.prepass_challenge_pending = False
        self.finding_challenge_pending = False
        self.deferred_report = None
        RUN_STATE.write_json_once(
            self.review_root / "provisional-report.json",
            {
                "schema_version": 1,
                "terminal": False,
                "trigger": "prepass_challenge",
                "report": report,
            },
        )
        self.event("prepass_challenge_issued", {"decision": "pass_to_primary"})
        self.prepass_challenge_context = {
            "status": "review_pending",
            "instruction": (
                "Your provisional pass is not finalized. Perform one adversarial contract check: "
                "choose an important boundary not established by the executed tests and trace its "
                "actual source control flow. For error/cleanup paths, consider the operation AND "
                "cleanup both raising: which exception reaches the caller, and does that match "
                "the contract? Do not assume a later bare raise executes. For other changes, "
                "try an input that distinguishes the required invariant from the apparent happy "
                "path. Submit a new REPORT: a concrete source-backed finding if violated, "
                "or explain why that boundary satisfies the contract. Do not invent a defect; "
                "missing context should be uncertain/escalate. All citation and validation "
                "requirements still apply. No additional execution is authorized."
            ),
        }
        return self.prepass_challenge_context

    def finalize(self, report: dict[str, Any]) -> dict[str, Any]:
        self._assert_inputs_current()
        RUN_STATE.write_json_once(self.review_root / "findings.json", report["findings"])
        RUN_STATE.write_json_once(self.review_root / "handoff.json", report)
        RUN_STATE.write_json_once(
            self.review_root / "completed.json",
            {"completed_at": RUN_STATE.utc_now(), "decision": report["decision"]},
        )
        self.event("review_completed", {"decision": report["decision"]})
        state_path = self.repo_root / ".agent" / "tasks" / self.task_id / "state.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            state = {"schema_version": 1, "task_id": self.task_id}
        history = state.setdefault("execution_history", [])
        attempts = state.setdefault("recent_attempts", [])
        entry = {
            "review_id": self.review_id,
            "run_id": self.run_id,
            "unit_id": self.unit_id,
            "worker": "reviewer",
            "result": report["decision"],
            "risk": self.packet["risk"],
            "review_route": report["review_route"],
            "finding_count": len(report["findings"]),
            "recorded_at": RUN_STATE.utc_now(),
            "archive": self.review_root.relative_to(self.repo_root).as_posix(),
        }
        history.append(entry)
        attempts.append(entry)
        if len(attempts) > 50:
            del attempts[:-50]
        usage = state.setdefault("usage", {})
        usage["reviewer_calls"] = int(usage.get("reviewer_calls", 0)) + 1
        state["latest_review_id"] = self.review_id
        state["updated_at"] = RUN_STATE.utc_now()
        RUN_STATE.atomic_json(state_path, state)
        RUN_STATE.atomic_json(
            self.repo_root / ".agent" / "current-task.json",
            {
                "schema_version": 1,
                "task_id": self.task_id,
                "unit_id": self.unit_id,
                "latest_run_id": self.run_id,
                "latest_review_id": self.review_id,
                "task_state": state_path.relative_to(self.repo_root).as_posix(),
                "usage": state.get("usage", {}),
                "recent_attempts": state.get("recent_attempts", []),
                "fallback_policy": state.get("fallback_policy", {}),
                "open_issues": state.get("open_issues", []),
                "updated_at": RUN_STATE.utc_now(),
            },
        )
        return report

    def run(self) -> dict[str, Any]:
        if self.config.get("reviewer_preload_model") is True:
            ensure_loaded = getattr(self.client, "ensure_loaded", None)
            if callable(ensure_loaded):
                ensure_loaded(
                    timeout_seconds=int(self.config.get("reviewer_model_load_timeout_seconds", 360))
                )
        preflight = getattr(self.client, "preflight", None)
        if callable(preflight):
            preflight()
        probe = getattr(self.client, "probe_structured_output", None)
        model_mode = probe() if callable(probe) else "not_probed"
        self.prepare()
        self.event("reviewer_model_compatibility", {"mode": model_mode})
        messages = [
            {"role": "system", "content": self.system_prompt()},
            {
                "role": "user",
                "content": "LOCAL_REVIEW_INPUT\n"
                + json.dumps(self.initial_payload(), ensure_ascii=False),
            },
        ]
        deadline = time.monotonic() + self.invocation_timeout
        report_only_next = False
        citation_shape_next = False
        pending_report_repair: dict[str, Any] | None = None
        for turn in range(1, self.max_turns + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ReviewError("reviewer invocation deadline exhausted")
            original_timeout = getattr(self.client, "timeout", None)
            original_native_tools = getattr(self.client, "native_tools", None)
            original_native_choice = getattr(self.client, "native_tool_choice", None)
            report_only_turn = (
                report_only_next
                and isinstance(original_native_tools, list)
                and any(
                    tool.get("function", {}).get("name") == "REPORT"
                    for tool in original_native_tools
                    if isinstance(tool, dict)
                )
            )
            report_only_next = False
            citation_shape_turn = citation_shape_next and isinstance(original_native_tools, list)
            citation_shape_next = False
            if report_only_turn:
                self.client.native_tools = [
                    tool
                    for tool in original_native_tools
                    if isinstance(tool, dict) and tool.get("function", {}).get("name") == "REPORT"
                ]
                self.client.native_tool_choice = "required"
                self.event("report_only_nudge", {"turn": turn})
            if citation_shape_turn:
                self.client.native_tools = canonical_citation_tools(self.client.native_tools)
                self.event("canonical_citation_transport_nudge", {"turn": turn})
            if isinstance(original_timeout, (int, float)):
                self.client.timeout = max(1, min(original_timeout, int(remaining)))
            try:
                try:
                    try:
                        if self.context_recovery:
                            self._update_active_read_context(messages)
                        raw = self.client.complete(messages)
                    except WORKER.WorkerError as fallback_exc:
                        fallback_detail = str(fallback_exc)
                        fallback_format_rejected = "HTTP Error 400" in fallback_detail and (
                            "peg-native format" in fallback_detail
                            or "does not match the expected" in fallback_detail
                        )
                        if not fallback_format_rejected:
                            raise
                        original_temperature = getattr(self.client, "temperature", None)
                        if not isinstance(original_temperature, (int, float)):
                            raise
                        self.client.temperature = 0.0
                        self.event(
                            "reviewer_model_compatibility",
                            {
                                "mode": "deterministic_plain_json_retry",
                                "turn": turn,
                                "reason": "plain_json_format_rejected",
                            },
                        )
                        try:
                            raw = self.client.complete(messages)
                        except WORKER.WorkerError as deterministic_exc:
                            deterministic_detail = str(deterministic_exc)
                            deterministic_format_rejected = (
                                "HTTP Error 400" in deterministic_detail
                                and (
                                    "peg-native format" in deterministic_detail
                                    or "does not match the expected" in deterministic_detail
                                )
                            )
                            fallback_model = getattr(self.client, "protocol_fallback_model", None)
                            current_model = getattr(self.client, "model", None)
                            if (
                                not deterministic_format_rejected
                                or not isinstance(fallback_model, str)
                                or not fallback_model.strip()
                                or fallback_model == current_model
                            ):
                                raise
                            self.client.model = fallback_model
                            self.client.structured_output = True
                            self.client.temperature = float(
                                self.config.get("reviewer_fallback_temperature", 0.1)
                            )
                            self.event(
                                "reviewer_model_compatibility",
                                {
                                    "mode": "protocol_fallback_model",
                                    "turn": turn,
                                    "from_model": current_model,
                                    "to_model": fallback_model,
                                    "reason": "deterministic_plain_json_format_rejected",
                                },
                            )
                            raw = self.client.complete(messages)
                except WORKER.WorkerError as exc:
                    detail = str(exc)
                    structured_output = getattr(self.client, "structured_output", False)
                    format_rejected = "HTTP Error 400" in detail and (
                        "peg-native format" in detail or "does not match the expected" in detail
                    )
                    if not structured_output or not format_rejected:
                        raise
                    self.client.structured_output = False
                    self.event(
                        "reviewer_model_compatibility",
                        {
                            "mode": "unstructured_runtime_fallback",
                            "turn": turn,
                            "reason": "structured_output_format_rejected",
                        },
                    )
                    raw = self.client.complete(messages)
            finally:
                if isinstance(original_timeout, (int, float)):
                    self.client.timeout = original_timeout
                if report_only_turn or citation_shape_turn:
                    self.client.native_tools = original_native_tools
                    self.client.native_tool_choice = original_native_choice
            self.event(
                "model_turn",
                {
                    "turn": turn,
                    "model_request": getattr(self.client, "last_request_stats", {}),
                    **(
                        RUN_STATE.diagnostic_facts(None, {}, raw) if self.diagnostic_logging else {}
                    ),
                },
            )
            name: str | None = None
            args: dict[str, Any] = {}
            try:
                envelope = WORKER.parse_action(raw)
                name = envelope["action"]
                args = envelope["arguments"]
                if name == "READ_FILE":
                    observation = self.read_file(args)
                elif name == "SEARCH":
                    observation = self.search(args)
                elif name == "RUN_APPROVED_TEST":
                    observation = self.run_approved_test(args)
                elif name == "RUN_APPROVED_STATIC_CHECK":
                    observation = self.run_approved_static_check(args)
                elif name == "REPORT":
                    report = self.validate_report(args)
                    pending_report_repair = None
                    observation = self._prepass_challenge(report)
                    if observation is None and self.diagnostic_logging:
                        self.event(
                            "diagnostic_action",
                            {
                                "turn": turn,
                                **RUN_STATE.diagnostic_facts(name, args, raw, {"status": "ok"}),
                            },
                        )
                    if observation is None:
                        return self.finalize(report)
                else:
                    raise ReviewError(f"unknown reviewer action: {name}")
                if self.diagnostic_logging:
                    self.event(
                        "diagnostic_action",
                        {
                            "turn": turn,
                            **RUN_STATE.diagnostic_facts(name, args, raw, observation),
                        },
                    )
                if (
                    name in {"RUN_APPROVED_TEST", "RUN_APPROVED_STATIC_CHECK"}
                    and observation.get("status") == "passed"
                    and self.deferred_report is not None
                ):
                    try:
                        report = self.validate_report(self.deferred_report)
                    except ReviewError as deferred_exc:
                        if "requires successful approved execution ids" not in str(deferred_exc):
                            raise
                    else:
                        pending_report_repair = None
                        challenge = self._prepass_challenge(report)
                        if challenge is not None:
                            observation = challenge
                        else:
                            self.event(
                                "deferred_report_finalized",
                                {"turn": turn, "after_action": name},
                            )
                            return self.finalize(report)
                self.last_protocol_error = None
                self.same_protocol_error_streak = 0
            except (ReviewError, WORKER.WorkerError, SAFE_EDIT.SafeEditError) as exc:
                self.protocol_errors += 1
                error = str(exc)
                self.same_protocol_error_streak = (
                    self.same_protocol_error_streak + 1 if error == self.last_protocol_error else 1
                )
                self.last_protocol_error = error
                if error == "contract_review must choose source_ref or source_refs, not both":
                    citation_shape_next = True
                observation = {"status": "error", "error": error}
                if name == "REPORT":
                    if error.startswith(
                        "pass_to_primary requires successful approved execution ids:"
                    ):
                        self.deferred_report = json.loads(json.dumps(args))
                    repair = self.report_repair(error, args)
                    suggested = repair.get("suggested_action")
                    citation_read_repair = "source line was not read:" in error or error.startswith(
                        "contract_review source was not read: "
                    )
                    if (
                        citation_read_repair
                        and isinstance(suggested, dict)
                        and suggested.get("action") == "READ_FILE"
                    ):
                        try:
                            repair["source_read"] = self.read_file(suggested["arguments"])
                            repair["instruction"] = (
                                repair.get("instruction", "")
                                + " "
                                + (
                                    "The cited range has now been shown. Compare the actual "
                                    "source with the claim, then retry REPORT or report rework."
                                )
                            )
                        except (OSError, UnicodeError, ReviewError, SAFE_EDIT.SafeEditError):
                            pass
                    observation["report_repair"] = repair
                    # Retain only trusted correction facts, never the invalid report.
                    # A duplicate read may compact history before a valid replacement.
                    pending_report_repair = json.loads(json.dumps(observation))
                if name is None and error.startswith("response does not begin with a JSON object"):
                    if self.required_reads_complete():
                        example_action = self.report_template()
                        next_step = (
                            "Use REPORT after checking the displayed source and test evidence."
                        )
                    else:
                        changed = [path for path in self.diff_paths() if path.endswith(".py")]
                        example_action = (
                            {
                                "action": "READ_FILE",
                                "arguments": {"path": changed[0]},
                            }
                            if changed
                            else self.empty_search_repair()["suggested_action"]
                        )
                        next_step = "First read a changed file."
                    observation["protocol_repair"] = {
                        "instruction": (
                            "Return exactly one JSON object with action and arguments; no prose, "
                            f"Markdown fence, or reasoning text. {next_step}"
                        ),
                        "example_action": example_action,
                    }
                if name == "SEARCH" and (
                    not isinstance(args.get("query"), str) or not args["query"].strip()
                ):
                    observation["search_repair"] = self.empty_search_repair()
                self.event(
                    "protocol_error",
                    {
                        "turn": turn,
                        "error": str(exc),
                        **(
                            RUN_STATE.diagnostic_facts(name, args, raw, observation)
                            if self.diagnostic_logging
                            else {}
                        ),
                    },
                )
                if (
                    self.protocol_errors >= self.max_protocol_errors
                    or self.same_protocol_error_streak >= 3
                ):
                    raise ReviewError("reviewer protocol error budget exhausted") from exc
            if observation.get("status") == "already_read":
                self.duplicate_read_streak += 1
                if (
                    self.duplicate_read_streak == 1
                    and observation.get("required_next_action") == "REPORT"
                ):
                    report_only_next = True
                if self.duplicate_read_streak >= self.max_duplicate_read_streak:
                    raise ReviewError("reviewer repeated reads made no progress")
            else:
                self.duplicate_read_streak = 0
            native_call = getattr(self.client, "last_native_call", None)
            if (
                self.native_history
                and isinstance(native_call, dict)
                and native_call.get("function", {}).get("name") == name
                and observation.get("status") != "error"
            ):
                messages.extend(
                    [
                        {"role": "assistant", "content": "", "tool_calls": [native_call]},
                        {
                            "role": "tool",
                            "name": name,
                            "tool_call_id": native_call["id"],
                            "content": "OBSERVATION\n"
                            + json.dumps(observation, ensure_ascii=False),
                        },
                    ]
                )
                self.event("native_tool_history_retained", {"action": name, "turn": turn})
            else:
                messages.extend(
                    [
                        {
                            "role": "assistant",
                            "content": (
                                "INVALID_REPORT_SUBMITTED"
                                if name == "REPORT" and observation.get("status") == "error"
                                else "INVALID_SEARCH_SUBMITTED"
                                if name == "SEARCH" and observation.get("status") == "error"
                                else "INVALID_NON_JSON_RESPONSE"
                                if name is None and observation.get("status") == "error"
                                else "DUPLICATE_READ_REJECTED"
                                if observation.get("status") == "already_read"
                                else raw
                            ),
                        },
                        {
                            "role": "user",
                            "content": "OBSERVATION\n"
                            + json.dumps(observation, ensure_ascii=False),
                        },
                    ]
                )
            if (
                observation.get("status") == "already_read"
                and observation.get("required_next_action") == "REPORT"
            ):
                messages = messages[:2] + messages[-2:]
            else:
                messages = self._trim_messages(messages)
            messages = [
                message
                for message in messages
                if not message.get("content", "").startswith("PENDING_REPORT_REPAIR\n")
            ]
            if pending_report_repair is not None and observation.get("report_repair") is None:
                messages.append(
                    {
                        "role": "user",
                        "content": "PENDING_REPORT_REPAIR\n"
                        + json.dumps(pending_report_repair, ensure_ascii=False),
                    }
                )
            if (
                self.prepass_challenge_context is not None
                and observation.get("status") != "review_pending"
            ):
                # Duplicate-read compaction can drop the still-unanswered
                # challenge. Keep it explicit until a new report is validated;
                # this is not source evidence or an additional model budget.
                messages.append(
                    {
                        "role": "user",
                        "content": "PREPASS_CHALLENGE\n"
                        + json.dumps(self.prepass_challenge_context, ensure_ascii=False),
                    }
                )
        raise ReviewError("reviewer model turn limit exhausted")


def write_report(report: dict[str, Any], path: Path | None) -> bool:
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    print(encoded, flush=True)
    if path is None:
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded + "\n", encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"REPORT_WRITE_ERROR: {exc}", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--request", required=True)
    parser.add_argument("--config", default=str(SCRIPT_DIR / "config.json"))
    parser.add_argument("--report")
    parser.add_argument("--max-tokens", type=int)
    args = parser.parse_args()
    if args.max_tokens is not None and args.max_tokens < 512:
        parser.error("--max-tokens must be at least 512")
    try:
        repo_root = Path.cwd().resolve()
        request = load_object(Path(args.request).resolve())
        config = load_object(Path(args.config).resolve())
        client = WORKER.LMStudioClient(
            WORKER.require_string(config.get("lmstudio_base_url"), "lmstudio_base_url"),
            WORKER.require_string(
                config.get("reviewer_model", config.get("coder_model")), "reviewer_model"
            ),
            int(config.get("model_request_timeout_seconds", 180)),
            max_tokens=(
                args.max_tokens
                if args.max_tokens is not None
                else int(config.get("reviewer_max_tokens", 4096))
            ),
            temperature=float(config.get("reviewer_temperature", 0.1)),
            top_p=float(config.get("reviewer_top_p", 0.9)),
            top_k=int(config.get("reviewer_top_k", 40)),
            min_p=float(config.get("reviewer_min_p", 0.0)),
            repeat_penalty=float(config.get("reviewer_repeat_penalty", 1.0)),
            structured_output=(
                False
                if config.get("reviewer_native_tools") is True
                else bool(config.get("reviewer_structured_output", True))
            ),
            action_schema=REVIEW_ACTION_SCHEMA,
            schema_name="local_reviewer_action",
            native_tools=(
                REVIEW_NATIVE_TOOLS if config.get("reviewer_native_tools") is True else None
            ),
            context_length=(
                int(config["reviewer_context_length"])
                if config.get("reviewer_context_length") is not None
                else None
            ),
            context_safety_margin=int(config.get("model_context_safety_margin", 1024)),
        )
        fallback_model = config.get("reviewer_protocol_fallback_model")
        if fallback_model is not None:
            client.protocol_fallback_model = WORKER.require_string(
                fallback_model, "reviewer_protocol_fallback_model"
            )
        with WORKER.MODEL_RESIDENCY.role_model_lease(client, config):
            report = ReviewerRuntime(repo_root, request, config, client).run()
    except (
        ReviewError,
        WORKER.WorkerError,
        WORKER.MODEL_RESIDENCY.ModelResidencyError,
        SAFE_EDIT.SafeEditError,
        OSError,
        ValueError,
    ) as exc:
        report = {
            "schema_version": 1,
            "decision": "failed",
            "failure_reason": str(exc),
            "next_action_required": "primary_inspect_reviewer_failure",
        }
        request_stats = (
            getattr(client, "last_request_stats", None) if "client" in locals() else None
        )
        if isinstance(request_stats, dict) and request_stats:
            report["model_request"] = request_stats
        message = str(exc).lower()
        if isinstance(exc, WORKER.ModelRequestError):
            report["infra_failure"] = {
                "reason_code": exc.reason_code,
                "reason": str(exc),
                "diagnostics": exc.diagnostics,
            }
        elif isinstance(exc, WORKER.PreflightBlocked):
            report["infra_failure"] = {
                "reason_code": exc.reason_code,
                "reason": str(exc),
            }
        elif isinstance(exc, WORKER.MODEL_RESIDENCY.ModelResidencyError):
            report["infra_failure"] = {
                "reason_code": exc.reason_code,
                "reason": str(exc),
            }
        elif isinstance(exc, WORKER.WorkerError) and any(
            marker in message
            for marker in ("request failed", "empty assistant message", "unexpected response shape")
        ):
            report["infra_failure"] = {
                "reason_code": "malformed_or_rejected_model_response",
                "reason": str(exc),
            }
    report_path = Path(args.report).resolve() if args.report else None
    if not write_report(report, report_path):
        return 1
    return 0 if report.get("decision") in {"pass_to_primary", "rework", "escalate"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
