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
    spec = importlib.util.spec_from_file_location(
        "local_worker_cache_state", SCRIPT_DIR / "run-state.py"
    )
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


def record_explorer_start(repo_root: Path, task: str, task_id: str | None = None) -> str | None:
    current_path = repo_root / ".agent" / "current-task.json"
    current = _load_object(current_path)
    if task_id is not None:
        if (
            not task_id
            or not task_id[0].isascii()
            or not task_id[0].isalnum()
            or not all(char.isascii() and (char.isalnum() or char in "._-") for char in task_id)
        ):
            raise ValueError(
                "task_id must contain only letters, digits, dot, underscore, or hyphen"
            )
        state_path = repo_root / ".agent" / "tasks" / task_id / "state.json"
        if not state_path.is_file():
            state_path.parent.mkdir(parents=True, exist_ok=True)
            RUN_STATE.write_json_once(
                state_path,
                {
                    "schema_version": 1,
                    "task_id": task_id,
                    "execution_history": [],
                    "recent_attempts": [],
                    "usage": {"coder_calls": 0, "explorer_calls": 0},
                },
            )
    else:
        if current is None or not isinstance(current.get("task_state"), str):
            return None
        state_path = repo_root / Path(current["task_state"])
    state = _load_object(state_path)
    if state is None:
        return None
    if task_id is not None and state.get("task_id") != task_id:
        raise ValueError("task state identity does not match task_id")
    run_id = f"explorer-{uuid.uuid4().hex[:12]}"
    unit_id = (
        (current or {}).get("unit_id")
        if (current or {}).get("task_id") == state.get("task_id")
        else None
    )
    unit_id = unit_id or state.get("current_unit_id") or "exploration"
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
    if (
        not isinstance(history, list)
        or not isinstance(attempts, list)
        or not isinstance(usage, dict)
    ):
        return None
    history.append(entry.copy())
    attempts.append(entry)
    if len(attempts) > 50:
        del attempts[:-50]
    usage["explorer_calls"] = int(usage.get("explorer_calls", 0)) + 1
    usage.setdefault("coder_calls", 0)
    state["updated_at"] = RUN_STATE.utc_now()
    RUN_STATE.atomic_json(state_path, state)
    if (
        current is not None
        and current.get("task_state") == state_path.relative_to(repo_root).as_posix()
    ):
        current["usage"] = usage
        current["recent_attempts"] = attempts
        current["updated_at"] = state["updated_at"]
        RUN_STATE.atomic_json(current_path, current)
    return run_id


def record_explorer_finish(
    repo_root: Path, run_id: str | None, report: dict[str, Any], task_id: str | None = None
) -> None:
    if run_id is None:
        return
    if task_id is not None and (
        not task_id
        or not task_id[0].isascii()
        or not task_id[0].isalnum()
        or not all(char.isascii() and (char.isalnum() or char in "._-") for char in task_id)
    ):
        raise ValueError("task_id must be a safe identifier")
    current_path = repo_root / ".agent" / "current-task.json"
    current = _load_object(current_path)
    if task_id is not None:
        state_path = repo_root / ".agent" / "tasks" / task_id / "state.json"
    elif current is not None and isinstance(current.get("task_state"), str):
        state_path = repo_root / Path(current["task_state"])
    else:
        return
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
                if isinstance(report.get("diagnostic_log"), str):
                    item["diagnostic_log"] = report["diagnostic_log"]
                if isinstance(report.get("diagnostic_report"), str):
                    item["diagnostic_report"] = report["diagnostic_report"]
                item["completed_at"] = RUN_STATE.utc_now()
                break
    state["updated_at"] = RUN_STATE.utc_now()
    RUN_STATE.atomic_json(state_path, state)
    if (
        current is not None
        and current.get("task_state") == state_path.relative_to(repo_root).as_posix()
    ):
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

    def navigation_hints(
        self,
        *,
        task_id: str | None = None,
        readable: list[str] | None = None,
        forbidden: list[str] | None = None,
        max_entries: int = 3,
        max_files: int = 8,
    ) -> list[dict[str, Any]]:
        """Return bounded prior Explorer notes only for unchanged, readable files."""
        entries = list(self._load()["entries"].values())
        entries = [item for item in entries if isinstance(item, dict)]
        entries.sort(
            key=lambda item: (
                (isinstance(item.get("report"), dict) and item["report"].get("task_id") == task_id)
                if task_id
                else False,
                str(item.get("created_at", "")),
            ),
            reverse=True,
        )
        hints: list[dict[str, Any]] = []
        used_paths: set[str] = set()
        root_key = os.path.normcase(str(self.repo_root))
        accepted = self._load().get("accepted_changes", [])
        if isinstance(accepted, list):
            for item in reversed(accepted):
                if len(used_paths) >= max_files:
                    break
                if not isinstance(item, dict):
                    continue
                relative = item.get("path")
                expected = item.get("sha256")
                if not isinstance(relative, str) or not isinstance(expected, str):
                    continue
                if readable is not None and not any(
                    root == "." or relative == root or relative.startswith(root.rstrip("/") + "/")
                    for root in readable
                ):
                    continue
                if forbidden and any(
                    relative == root or relative.startswith(root.rstrip("/") + "/")
                    for root in forbidden
                ):
                    continue
                candidate = (self.repo_root / relative).resolve()
                try:
                    if os.path.commonpath((root_key, os.path.normcase(str(candidate)))) != root_key:
                        continue
                    if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
                        continue
                except (OSError, ValueError):
                    continue
                if relative not in used_paths:
                    used_paths.add(relative)
                    hints.append(
                        {
                            "source_task_id": item.get("task_id"),
                            "source_question": "Accepted implementation; inspect current code for semantics.",
                            "files": [
                                {
                                    "path": relative,
                                    "sha256": expected,
                                    "prior_reason": "Primary accepted a change to this path.",
                                }
                            ],
                        }
                    )
                if len(hints) >= max_entries:
                    return hints
        for entry in entries:
            if len(hints) >= max_entries or len(used_paths) >= max_files:
                break
            report = entry.get("report")
            if not isinstance(report, dict) or report.get("status") != "success":
                continue
            observed = report.get("observed_hashes")
            if not isinstance(observed, dict):
                continue
            files: list[dict[str, str]] = []
            relevant_files = report.get("relevant_files")
            if not isinstance(relevant_files, list):
                continue
            for item in relevant_files:
                if len(used_paths) + len(files) >= max_files:
                    break
                if not isinstance(item, dict):
                    continue
                relative = item.get("path")
                if (
                    not isinstance(relative, str)
                    or not relative
                    or relative in used_paths
                    or any(
                        part in {"", ".", ".."} or part in EXCLUDED_PARTS
                        for part in relative.replace("\\", "/").split("/")
                    )
                    or not isinstance(observed.get(relative), str)
                ):
                    continue
                if readable is not None and not any(
                    root == "." or relative == root or relative.startswith(root.rstrip("/") + "/")
                    for root in readable
                ):
                    continue
                if forbidden and any(
                    relative == root or relative.startswith(root.rstrip("/") + "/")
                    for root in forbidden
                ):
                    continue
                candidate = (self.repo_root / relative).resolve()
                try:
                    if os.path.commonpath((root_key, os.path.normcase(str(candidate)))) != root_key:
                        continue
                    if (
                        not candidate.is_file()
                        or hashlib.sha256(candidate.read_bytes()).hexdigest() != observed[relative]
                    ):
                        continue
                except (OSError, ValueError):
                    continue
                files.append(
                    {
                        "path": relative,
                        "sha256": observed[relative],
                        "prior_reason": str(item.get("reason", ""))[:180],
                    }
                )
            if files:
                used_paths.update(item["path"] for item in files)
                hints.append(
                    {
                        "source_task_id": report.get("task_id"),
                        "source_question": str(report.get("task", ""))[:180],
                        "files": files,
                    }
                )
        return hints

    def record_accepted_paths(self, task_id: str, run_id: str, paths: list[str]) -> bool:
        """Index accepted changed paths, never model-authored semantics."""
        records = []
        root_key = os.path.normcase(str(self.repo_root))
        for relative in paths:
            if not isinstance(relative, str) or not relative or "\\" in relative:
                continue
            if any(
                part in {"", ".", ".."} or part in EXCLUDED_PARTS for part in relative.split("/")
            ):
                continue
            candidate = (self.repo_root / relative).resolve()
            try:
                if os.path.commonpath((root_key, os.path.normcase(str(candidate)))) != root_key:
                    continue
                records.append(
                    {
                        "task_id": task_id,
                        "run_id": run_id,
                        "path": relative,
                        "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                        "accepted_at": RUN_STATE.utc_now(),
                    }
                )
            except (OSError, ValueError):
                continue
        if not records:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return False
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(f"{os.getpid()}\n".encode("ascii"))
            cache = self._load()
            existing = cache.get("accepted_changes", [])
            if not isinstance(existing, list):
                existing = []
            cache["accepted_changes"] = (existing + records)[-50:]
            cache["updated_at"] = RUN_STATE.utc_now()
            RUN_STATE.atomic_json(self.path, cache)
            return True
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

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
