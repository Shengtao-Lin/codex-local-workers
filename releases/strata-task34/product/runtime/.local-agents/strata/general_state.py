"""Persistent task accounting. New attempts never replenish task resources."""

import hashlib
import json
import os
import re
import time
from pathlib import Path

from strata_artifacts import save

LIMITS = {
    "model_requests": 16,
    "tool_actions": 24,
    "evidence_actions": 16,
    "edits": 4,
    "initial_checks": 1,
    "post_edit_checks": 4,
    "format_preparations": 6,
    "protocol_recoveries": 2,
    "edit_recoveries": 2,
    "reserved_output_tokens": 196608,
}
SECONDS = 1800
TERMINAL = {
    "ready_for_primary",
    "blocked",
    "failed",
    "budget_exhausted",
    "conflicted",
    "cancelled",
    "interrupted",
}


class StateError(ValueError):
    pass


class BudgetExhausted(StateError):
    pass


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", value):
        raise StateError("Invalid task/attempt identifier")
    return value


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise StateError("Duplicate JSON field: " + key)
            result[key] = value
        return result

    return json.loads(
        Path(path).read_text(encoding="utf-8-sig"),
        object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(StateError(value)),
    )


class TaskLedger:
    """Append-only hash-linked snapshots; caller holds the existing project lock."""

    def __init__(self, root, task_id):
        self.root = Path(root)
        self.task_id = identifier(task_id)
        self.path = self.root / ".agent/tasks" / self.task_id / "general"
        self.events = self.path / "ledger"
        self.sequence = 0
        self.digest = None
        self.state = {
            "task_id": task_id,
            "used": dict.fromkeys(LIMITS, 0),
            "active_seconds": 0,
            "active": None,
            "status": "prepared",
            "attempts": [],
            "pending_model": None,
            "noops": 0,
            "no_evidence": 0,
            "last_observation": None,
        }
        if self.events.exists():
            entries = sorted(self.events.glob("*.json"))
            for number, entry in enumerate(entries, 1):
                if entry.name != f"{number:04d}.json":
                    raise StateError("Noncontiguous task ledger")
                value = read(entry)
                expected = value.pop("sha256", None)
                if fingerprint(value) != expected or value["previous"] != self.digest:
                    raise StateError("Task ledger changed")
                if value["sequence"] != number or value["state"]["task_id"] != task_id:
                    raise StateError("Task ledger identity differs")
                self.state, self.digest, self.sequence = (
                    value["state"],
                    expected,
                    number,
                )
        self.limits = LIMITS
        self.seconds = SECONDS
        if self.state.get("budget_profile"):
            from review_rework_budget import budgets

            total = budgets(self.state["budget_profile"])[2]
            self.limits = {k: v for k, v in total.items() if k != "seconds"}
            self.seconds = total["seconds"]

    def record(self, kind, facts=None):
        value = {
            "sequence": self.sequence + 1,
            "previous": self.digest,
            "kind": kind,
            "facts": facts or {},
            "state": self.state,
            "recorded_at": time.time(),
        }
        digest = fingerprint(value)
        save(self.events / f"{self.sequence + 1:04d}.json", {**value, "sha256": digest})
        self.digest, self.sequence = digest, self.sequence + 1

    def spend(self, key, count=1):
        if type(count) is not int or count < 0 or key not in self.limits:
            raise StateError("Invalid resource reservation")
        if self.state["used"].get(key, 0) + count > self.limits[key]:
            self.state["exhausted_resource"] = key
            self.record("resource_exhausted", {"resource": key})
            raise BudgetExhausted(key + " exhausted")
        self.state["used"][key] = self.state["used"].get(key, 0) + count
        self.record("resource_reserved", {"resource": key, "count": count})

    def remaining_seconds(self):
        active = self.state["active"]
        elapsed = max(0, time.time() - active["started"]) if active else 0
        return max(0, self.seconds - self.state["active_seconds"] - elapsed)

    def check_begin(self, attempt_id, *, resume=False):
        identifier(attempt_id)
        if attempt_id in self.state["attempts"]:
            raise StateError("Attempt identity already used")
        if self.state["attempts"] and not resume:
            raise StateError("Existing task requires explicit resume, never a new budget")
        if resume and not self.state["attempts"]:
            raise StateError("No attempt to resume")
        if len(self.state["attempts"]) >= 3:
            raise StateError("At most three attempts, all sharing the task budget")
        if self.state["active"] or self.state["pending_model"]:
            raise StateError("Unsettled prior process/request; reconcile before resume")
        if self.state["status"] == "conflicted":
            raise StateError("Conflicted task cannot resume")
        if self.remaining_seconds() <= 0:
            raise BudgetExhausted("Task time exhausted")

    def begin(self, attempt_id, *, resume=False):
        self.check_begin(attempt_id, resume=resume)
        self.state["attempts"].append(attempt_id)
        self.state["active"] = {
            "attempt_id": attempt_id,
            "pid": os.getpid(),
            "started": time.time(),
        }
        self.state["status"] = "running"
        self.record("attempt_started")

    def end(self, status):
        if status not in TERMINAL:
            raise StateError("Unknown terminal state")
        if self.state["active"]:
            self.state["active_seconds"] += max(0, time.time() - self.state["active"]["started"])
        self.state["active"] = None
        self.state["status"] = status
        self.record("attempt_ended")

    def current(self):
        return {
            "status": self.state["status"],
            "used": self.state["used"],
            "limits": self.limits,
            "remaining_seconds": round(self.remaining_seconds(), 3),
            "ledger_sha256": self.digest,
            "active": self.state["active"],
            "pending_model": self.state["pending_model"],
        }

    def cancelled(self):
        active = self.state["active"]
        return bool(active and (self.path / "cancel" / (active["attempt_id"] + ".json")).exists())

    def cancel(self):
        if not self.state["active"]:
            raise StateError("Task is not active")
        active_id = self.state["active"]["attempt_id"]
        marker = self.path / "cancel" / (active_id + ".json")
        if marker.exists() and read(marker).get("attempt_id") == active_id:
            return
        save(marker, {"task_id": self.task_id, "attempt_id": active_id})
