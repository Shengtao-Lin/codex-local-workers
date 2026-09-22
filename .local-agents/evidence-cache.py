from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import uuid
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
EXCLUDED_PARTS = {
    ".agent",
    ".git",
    ".venv",
    ".local-agents",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}


def load_run_state() -> Any:
    spec = importlib.util.spec_from_file_location("local_worker_cache_state", SCRIPT_DIR / "run-state.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load run-state.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUN_STATE = load_run_state()


def _load_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def record_explorer_start(repo_root: Path, task: str) -> str | None:
    current_path = repo_root / ".agent" / "current-task.json"
    current = _load_object(current_path)
    if current is None:
        return None
    state_ref = current.get("task_state")
    if not isinstance(state_ref, str):
        return None
    state_path = repo_root / Path(state_ref)
    state = _load_object(state_path)
    if state is None:
        return None
    run_id = f"explorer-{uuid.uuid4().hex[:12]}"
    unit_id = current.get("unit_id") or state.get("current_unit_id") or "exploration"
    entry = {
        "run_id": run_id,
        "unit_id": unit_id,
        "worker": "explorer",
        "result": "running",
        "model_started": True,
        "failure_signature": None,
        "progress": None,
        "recorded_at": RUN_STATE.utc_now(),
        "task": task,
    }
    history = state.setdefault("execution_history", [])
    attempts = state.setdefault("recent_attempts", [])
    usage = state.setdefault("usage", {"coder_calls": 0, "explorer_calls": 0})
    if not isinstance(history, list) or not isinstance(attempts, list) or not isinstance(usage, dict):
        return None
    history.append(entry.copy())
    attempts.append(entry)
    if len(attempts) > 50:
        del attempts[:-50]
    usage["explorer_calls"] = int(usage.get("explorer_calls", 0)) + 1
    usage.setdefault("coder_calls", 0)
    state["updated_at"] = RUN_STATE.utc_now()
    RUN_STATE.atomic_json(state_path, state)
    current["usage"] = usage
    current["recent_attempts"] = attempts
    current["updated_at"] = state["updated_at"]
    RUN_STATE.atomic_json(current_path, current)
    return run_id


def record_explorer_finish(repo_root: Path, run_id: str | None, report: dict[str, Any]) -> None:
    if run_id is None:
        return
    current_path = repo_root / ".agent" / "current-task.json"
    current = _load_object(current_path)
    if current is None or not isinstance(current.get("task_state"), str):
        return
    state_path = repo_root / Path(current["task_state"])
    state = _load_object(state_path)
    if state is None:
        return
    status = report.get("status")
    reason = report.get("failure_reason") or "unknown"
    signature = None if status == "success" else f"explorer|{status}|{str(reason)[:160]}"
    for field in ("execution_history", "recent_attempts"):
        items = state.get(field, [])
        if not isinstance(items, list):
            continue
        for item in reversed(items):
            if isinstance(item, dict) and item.get("run_id") == run_id:
                item["result"] = status
                item["failure_signature"] = signature
                item["completed_at"] = RUN_STATE.utc_now()
                break
    state["updated_at"] = RUN_STATE.utc_now()
    RUN_STATE.atomic_json(state_path, state)
    current["recent_attempts"] = state.get("recent_attempts", [])
    current["updated_at"] = state["updated_at"]
    RUN_STATE.atomic_json(current_path, current)


def task_key(task: str) -> str:
    normalized = " ".join(task.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def repository_fingerprint(repo_root: Path, *, max_files: int = 20_000) -> dict[str, Any]:
    records: list[str] = []
    count = 0
    try:
        for path in repo_root.rglob("*"):
            relative_path = path.relative_to(repo_root)
            if any(part in EXCLUDED_PARTS for part in relative_path.parts):
                continue
            if not path.is_file():
                continue
            metadata = path.stat()
            records.append(
                f"{relative_path.as_posix()}\0{metadata.st_size}\0{metadata.st_mtime_ns}"
            )
            count += 1
            if count > max_files:
                return {"cacheable": False, "reason": "repository file limit exceeded"}
    except OSError as exc:
        return {"cacheable": False, "reason": str(exc)}
    digest = hashlib.sha256("\n".join(sorted(records)).encode("utf-8")).hexdigest()
    return {"cacheable": True, "sha256": digest, "file_count": count}


class EvidenceCache:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.path = self.repo_root / ".agent" / "repo-map.json"
        self.lock_path = self.repo_root / ".agent" / "repo-map.lock"

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            return {"schema_version": 1, "entries": {}}
        except (OSError, ValueError):
            return {"schema_version": 1, "entries": {}}
        if not isinstance(value, dict) or not isinstance(value.get("entries"), dict):
            return {"schema_version": 1, "entries": {}}
        return value

    def lookup(self, task: str, fingerprint: dict[str, Any]) -> dict[str, Any] | None:
        if not fingerprint.get("cacheable"):
            return None
        entry = self._load()["entries"].get(task_key(task))
        if not isinstance(entry, dict) or entry.get("fingerprint") != fingerprint.get("sha256"):
            return None
        report = entry.get("report")
        if not isinstance(report, dict) or report.get("status") != "success":
            return None
        observed = report.get("observed_hashes", {})
        if not isinstance(observed, dict):
            return None
        root_key = os.path.normcase(str(self.repo_root))
        for relative, expected in observed.items():
            if not isinstance(relative, str) or not isinstance(expected, str):
                return None
            candidate = (self.repo_root / Path(relative)).resolve()
            try:
                if os.path.commonpath((root_key, os.path.normcase(str(candidate)))) != root_key:
                    return None
                actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            except (OSError, ValueError):
                return None
            if actual != expected:
                return None
        return json.loads(json.dumps(report))

    def store(self, task: str, fingerprint: dict[str, Any], report: dict[str, Any]) -> bool:
        if not fingerprint.get("cacheable") or report.get("status") != "success":
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return False
        token = f"{os.getpid()}\n".encode("ascii")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(token)
                stream.flush()
            cache = self._load()
            entries = cache["entries"]
            entries[task_key(task)] = {
                "task": task,
                "fingerprint": fingerprint["sha256"],
                "file_count": fingerprint.get("file_count"),
                "created_at": RUN_STATE.utc_now(),
                "report": report,
            }
            if len(entries) > 50:
                oldest = sorted(
                    entries,
                    key=lambda key: str(entries[key].get("created_at", "")),
                )[: len(entries) - 50]
                for key in oldest:
                    del entries[key]
            cache["updated_at"] = RUN_STATE.utc_now()
            RUN_STATE.atomic_json(self.path, cache)
            return True
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
