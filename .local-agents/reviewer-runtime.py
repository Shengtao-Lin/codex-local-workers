from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVIEW_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["READ_FILE", "SEARCH", "REPORT"]},
        "arguments": {"type": "object", "additionalProperties": True},
    },
    "required": ["action", "arguments"],
    "additionalProperties": False,
}


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
        self.client = client
        self.task_id = WORKER.require_identifier(request.get("task_id"), "task_id")
        self.unit_id = WORKER.require_identifier(request.get("unit_id"), "unit_id")
        self.run_id = WORKER.require_identifier(request.get("run_id"), "run_id")
        self.review_id = WORKER.require_identifier(request.get("review_id"), "review_id")
        self.run_root = (
            self.repo_root / ".agent" / "tasks" / self.task_id / "runs" / self.run_id
        )
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
        if self.handoff.get("status") != "ready_for_review":
            raise ReviewError("only ready_for_review Coder runs can enter local review")
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
        self.editor = SAFE_EDIT.SafeEditor(
            self.repo_root, allowed_modify=[], allowed_create=[]
        )
        self.max_turns = int(config.get("max_reviewer_turns", 16))
        self.max_protocol_errors = int(config.get("max_reviewer_protocol_errors", 4))
        self.max_output = int(config.get("max_tool_output_chars", 16000))
        self.invocation_timeout = int(config.get("reviewer_invocation_timeout_seconds", 600))
        self.protocol_errors = 0
        self.read_paths: set[str] = set()
        if (
            self.max_turns < 1
            or self.max_protocol_errors < 1
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
            raise ReviewError(
                "review inputs changed after the Coder run: " + ", ".join(changed)
            )

    def prepare(self) -> None:
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
        relative, path = self._assert_read_allowed(args.get("path"))
        if not path.is_file():
            raise ReviewError(f"file does not exist: {relative}")
        start = args.get("start_line", 1)
        end = args.get("end_line")
        if not isinstance(start, int) or start < 1:
            raise ReviewError("start_line must be a positive integer")
        if end is not None and (not isinstance(end, int) or end < start):
            raise ReviewError("end_line must be at least start_line")
        text = path.read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        selected = lines[start - 1 : end]
        content = "\n".join(
            f"{number}: {line}" for number, line in enumerate(selected, start=start)
        )
        self.read_paths.add(relative)
        return {
            "status": "ok",
            "path": relative,
            "start_line": start,
            "end_line": min(end or len(lines), len(lines)),
            "content": content[: self.max_output],
            "truncated": len(content) > self.max_output,
        }

    def search(self, args: dict[str, Any]) -> dict[str, Any]:
        query = WORKER.require_string(args.get("query"), "query")
        root = args.get("path", ".")
        if root == ".":
            relative_root, resolved_root = ".", self.repo_root
        else:
            relative_root, resolved_root = self._assert_read_allowed(root)
        glob = args.get("glob", "*")
        if not isinstance(glob, str) or not glob:
            raise ReviewError("glob must be a non-empty string")
        limit = args.get("max_results", 50)
        if not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ReviewError("max_results must be between 1 and 200")
        case_sensitive = args.get("case_sensitive", False)
        needle = query if case_sensitive else query.lower()
        results: list[dict[str, Any]] = []
        candidates = [resolved_root] if resolved_root.is_file() else resolved_root.rglob("*")
        for path in candidates:
            if len(results) >= limit or not path.is_file():
                continue
            relative = path.relative_to(self.repo_root).as_posix()
            if not fnmatch.fnmatch(relative, glob) and not fnmatch.fnmatch(path.name, glob):
                continue
            try:
                self._assert_read_allowed(relative)
                lines = path.read_text(encoding="utf-8-sig").splitlines()
            except (OSError, UnicodeError, ReviewError):
                continue
            for number, line in enumerate(lines, 1):
                haystack = line if case_sensitive else line.lower()
                if needle in haystack:
                    results.append({"path": relative, "line": number, "text": line[:500]})
                    self.read_paths.add(relative)
                    if len(results) >= limit:
                        break
        return {"status": "ok", "root": relative_root, "results": results}

    def system_prompt(self) -> str:
        return """You are a read-only local code reviewer. Review the actual diff and runtime
evidence against the authoritative packet. Coder prose is an untrusted claim, not evidence.
Use one JSON action per turn: READ_FILE, SEARCH, or REPORT. You cannot edit files, run commands,
use Git, or delegate. Check scope, owned contracts, ordering, error paths, transaction/async API
semantics, suspicious compatibility code, test weakening, and claims unsupported by validation.
REPORT arguments must contain decision (pass_to_primary, rework, or escalate), findings,
verified_contract_ids, and unverified_claims. Every finding needs id, severity, category, path,
line, evidence, contract_id, and suggested_fix. Cite concrete code evidence; do not invent issues.
Use escalate for architecture/security uncertainty that a bounded rework should not decide."""

    def initial_payload(self) -> dict[str, Any]:
        max_diff = int(self.config.get("reviewer_initial_diff_chars", 24000))
        diff = self.diff[:max_diff]
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
            "required_behavior": self.packet["required_behavior"],
            "acceptance_criteria": self.packet["acceptance_criteria"],
            "acceptance_scenarios": self.packet["acceptance_scenarios"],
            "required_order": self.packet["required_order"],
            "forbidden_orderings": self.packet["forbidden_orderings"],
            "scope": self.packet["scope"],
            "runtime_validation": self.validation,
            "coder_claims": self.handoff.get("worker_claims", {}),
            "cumulative_diff": diff,
            "diff_truncated": len(self.diff) > len(diff),
        }

    def validate_report(self, args: dict[str, Any]) -> dict[str, Any]:
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
            if line is not None and (not isinstance(line, int) or line < 1):
                raise ReviewError("finding line must be a positive integer or null")
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
            "unverified_claims": unverified,
            "runtime_facts": {
                "read_only": True,
                "inputs_unchanged": True,
                "read_paths": sorted(self.read_paths),
                "protocol_error_count": self.protocol_errors,
            },
            "next_action_required": {
                "pass_to_primary": "primary_review_by_risk_route",
                "rework": "bounded_coder_rework",
                "escalate": "primary_takeover_or_replan",
            }[decision],
        }

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
        preflight = getattr(self.client, "preflight", None)
        if callable(preflight):
            preflight()
        self.prepare()
        messages = [
            {"role": "system", "content": self.system_prompt()},
            {
                "role": "user",
                "content": "LOCAL_REVIEW_INPUT\n"
                + json.dumps(self.initial_payload(), ensure_ascii=False),
            },
        ]
        deadline = time.monotonic() + self.invocation_timeout
        for turn in range(1, self.max_turns + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ReviewError("reviewer invocation deadline exhausted")
            original_timeout = getattr(self.client, "timeout", None)
            if isinstance(original_timeout, (int, float)):
                self.client.timeout = max(1, min(original_timeout, int(remaining)))
            try:
                raw = self.client.complete(messages)
            finally:
                if isinstance(original_timeout, (int, float)):
                    self.client.timeout = original_timeout
            self.event("model_turn", {"turn": turn})
            try:
                envelope = WORKER.parse_action(raw)
                name = envelope["action"]
                args = envelope["arguments"]
                if name == "READ_FILE":
                    observation = self.read_file(args)
                elif name == "SEARCH":
                    observation = self.search(args)
                elif name == "REPORT":
                    return self.finalize(self.validate_report(args))
                else:
                    raise ReviewError(f"unknown reviewer action: {name}")
            except (ReviewError, WORKER.WorkerError, SAFE_EDIT.SafeEditError) as exc:
                self.protocol_errors += 1
                observation = {"status": "error", "error": str(exc)}
                self.event("protocol_error", {"turn": turn, "error": str(exc)})
                if self.protocol_errors >= self.max_protocol_errors:
                    raise ReviewError("reviewer protocol error budget exhausted") from exc
            messages.extend(
                [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": "OBSERVATION\n"
                        + json.dumps(observation, ensure_ascii=False),
                    },
                ]
            )
            if len(messages) > 12:
                messages = messages[:2] + messages[-10:]
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--config", default=str(SCRIPT_DIR / "config.json"))
    parser.add_argument("--report")
    args = parser.parse_args()
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
            max_tokens=int(config.get("reviewer_max_tokens", 4096)),
            temperature=float(config.get("reviewer_temperature", 0.1)),
            top_p=float(config.get("reviewer_top_p", 0.9)),
            top_k=int(config.get("reviewer_top_k", 40)),
            min_p=float(config.get("reviewer_min_p", 0.0)),
            repeat_penalty=float(config.get("reviewer_repeat_penalty", 1.0)),
            structured_output=bool(config.get("reviewer_structured_output", True)),
            action_schema=REVIEW_ACTION_SCHEMA,
            schema_name="local_reviewer_action",
        )
        report = ReviewerRuntime(repo_root, request, config, client).run()
    except (ReviewError, WORKER.WorkerError, SAFE_EDIT.SafeEditError, OSError, ValueError) as exc:
        report = {
            "schema_version": 1,
            "decision": "failed",
            "failure_reason": str(exc),
            "next_action_required": "primary_inspect_reviewer_failure",
        }
    report_path = Path(args.report).resolve() if args.report else None
    if not write_report(report, report_path):
        return 1
    return 0 if report.get("decision") in {"pass_to_primary", "rework", "escalate"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
