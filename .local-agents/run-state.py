from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class RunStateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_fact(path: Path, relative: str) -> dict[str, Any]:
    if not path.exists():
        return {"path": relative, "exists": False, "sha256": None, "size": None}
    if not path.is_file():
        return {"path": relative, "exists": True, "kind": "non_file", "sha256": None}
    data = path.read_bytes()
    metadata = path.stat()
    return {
        "path": relative,
        "exists": True,
        "kind": "file",
        "sha256": sha256_bytes(data),
        "size": len(data),
        "mtime_ns": metadata.st_mtime_ns,
    }


def facts_for_paths(repo_root: Path, paths: Iterable[str]) -> dict[str, dict[str, Any]]:
    return {
        relative: file_fact(repo_root / Path(relative), relative)
        for relative in sorted(set(paths))
    }


def _run_git(repo_root: Path, args: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "error": str(exc)}
    return {
        "available": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def git_snapshot(repo_root: Path) -> dict[str, Any]:
    head = _run_git(repo_root, ["rev-parse", "--verify", "HEAD"])
    status = _run_git(
        repo_root, ["status", "--porcelain=v1", "--untracked-files=all", "-z"]
    )
    if not head.get("available") or not status.get("available"):
        return {
            "is_repository": False,
            "head": None,
            "status_entries": [],
            "diagnostic": head.get("stderr") or status.get("stderr") or head.get("error") or status.get("error"),
        }
    entries = [item for item in status["stdout"].split("\0") if item]
    return {
        "is_repository": True,
        "head": head["stdout"].strip(),
        "status_entries": entries,
    }


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = -1
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_json_once(path: Path, value: Any) -> None:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


class RunArchive:
    def __init__(self, repo_root: Path, task_id: str, unit_id: str, run_id: str) -> None:
        self.repo_root = repo_root.resolve()
        self.task_id = task_id
        self.unit_id = unit_id
        self.run_id = run_id
        self.agent_root = self.repo_root / ".agent"
        self.task_root = self.agent_root / "tasks" / task_id
        self.run_root = self.task_root / "runs" / run_id
        self.prepared = False
        self.model_started = False

    def prepare(self, packet: dict[str, Any], baseline: dict[str, Any]) -> None:
        self.run_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.run_root.mkdir()
        except FileExistsError as exc:
            raise RunStateError(f"run_id already has an archive: {self.run_id}") from exc
        self.prepared = True
        try:
            write_json_once(self.run_root / "packet.json", packet)
            write_json_once(self.run_root / "baseline.json", baseline)
            self.event("run_prepared", {"unit_id": self.unit_id})
        except BaseException:
            # Keep any partial directory as conflict evidence; never recycle the run id.
            raise

    def event(self, event: str, facts: dict[str, Any] | None = None) -> None:
        if not self.prepared:
            return
        record = {"at": utc_now(), "event": event, "facts": facts or {}}
        with (self.run_root / "events.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()

    def mark_model_started(self) -> None:
        if not self.model_started:
            self.model_started = True
            self.event("first_model_turn", {})

    def finalize(
        self,
        report: dict[str, Any],
        changes: dict[str, Any],
        validation: dict[str, Any] | None,
        post_state: dict[str, Any],
    ) -> None:
        if not self.prepared:
            return
        write_json_once(self.run_root / "changes.json", changes)
        write_json_once(self.run_root / "validation.json", validation)
        write_json_once(self.run_root / "handoff.json", report)
        write_json_once(self.run_root / "post-state.json", post_state)
        write_json_once(
            self.run_root / "completed.json",
            {"completed_at": utc_now(), "status": report.get("status")},
        )
        self._update_task_state(report)

    def _update_task_state(self, report: dict[str, Any]) -> None:
        state_path = self.task_root / "state.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            state = {
                "schema_version": 1,
                "task_id": self.task_id,
                "accepted_decisions": [],
                "completed_units": [],
                "open_issues": [],
                "execution_history": [],
                "recent_attempts": [],
            }
        if not isinstance(state, dict):
            raise RunStateError("task state root must be an object")
        history = state.setdefault("execution_history", [])
        attempts = state.setdefault("recent_attempts", [])
        if not isinstance(history, list) or not isinstance(attempts, list):
            raise RunStateError("task execution history fields must be arrays")
        entry = {
            "run_id": self.run_id,
            "unit_id": self.unit_id,
            "worker": "coder",
            "result": report.get("status"),
            "model_started": self.model_started,
            "failure_signature": report.get("failure_signature"),
            "progress": None,
            "recorded_at": utc_now(),
            "archive": self.run_root.relative_to(self.repo_root).as_posix(),
        }
        history.append(entry)
        attempts.append(entry)
        if len(attempts) > 50:
            del attempts[:-50]
        usage = state.setdefault("usage", {"coder_calls": 0, "explorer_calls": 0})
        if not isinstance(usage, dict):
            raise RunStateError("task usage must be an object")
        usage.setdefault("coder_calls", 0)
        usage.setdefault("explorer_calls", 0)
        if self.model_started:
            usage["coder_calls"] = int(usage["coder_calls"]) + 1
        state["latest_run_id"] = self.run_id
        state["current_unit_id"] = self.unit_id
        state["updated_at"] = utc_now()
        atomic_json(state_path, state)
        atomic_json(
            self.agent_root / "current-task.json",
            {
                "schema_version": 1,
                "task_id": self.task_id,
                "unit_id": self.unit_id,
                "latest_run_id": self.run_id,
                "task_state": state_path.relative_to(self.repo_root).as_posix(),
                "usage": state.get("usage", {}),
                "recent_attempts": state.get("recent_attempts", []),
                "fallback_policy": state.get("fallback_policy", {}),
                "open_issues": state.get("open_issues", []),
                "updated_at": utc_now(),
            },
        )
