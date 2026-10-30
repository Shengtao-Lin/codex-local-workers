"""Opt-in native-tool comparison. Current core classes remain the default."""

import time

from general_host import GeneralHost
from general_state import LIMITS, BudgetExhausted, StateError, TaskLedger

TRIAL_LIMITS = {
    **LIMITS,
    "model_requests": 12,
    "tool_actions": 32,
    "evidence_actions": 24,
    "edits": 4,
    "format_preparations": 8,
    "reserved_output_tokens": 147456,
}


class TrialLedger(TaskLedger):
    def spend(self, key, count=1):
        if type(count) is not int or count < 0 or key not in TRIAL_LIMITS:
            raise StateError("Invalid resource reservation")
        if key == "tool_actions" and count == 1 and getattr(self, "prepaid_tool", False):
            self.prepaid_tool = False
            self.record("prepaid_native_tool_consumed")
            return
        if self.state["used"][key] + count > TRIAL_LIMITS[key]:
            raise BudgetExhausted(key + " exhausted")
        self.state["used"][key] += count
        self.record("resource_reserved", {"resource": key, "count": count})

    def remaining_seconds(self):
        active = self.state["active"]
        elapsed = max(0, time.time() - active["started"]) if active else 0
        return max(0, 1200 - self.state["active_seconds"] - elapsed)

    def current(self):
        return {**super().current(), "limits": TRIAL_LIMITS}


class NativeTrialHost(GeneralHost):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("experimental_native_tools_trial") not in {"A", "B"}:
            raise StateError("Explicit trial arm required")
        self.ledger.__class__ = TrialLedger

    def evidence(self, action, args):
        value = super().evidence(action, args)
        if action == "read" and "content" in value:
            value["total_lines"] = len(
                self.editor.read_bytes(args["path"])[0].decode("utf-8-sig").splitlines()
            )
        if action == "read" and value.get("version_ref"):
            self.ledger.state.setdefault("native_observed", {})[args["path"]] = value["version_ref"]
            self.ledger.record("native_version_observed", {"path": args["path"]})
        return value

    def action(self, action, args):
        if action == "native_denied" and set(args) == {"reason"}:
            self.guard()
            self.assert_bound()
            self.ledger.spend("tool_actions")
            self.ledger.spend("protocol_recoveries")
            return {
                "observation": {"status": "native_rejected_no_write", "reason": args["reason"]},
                "context": self.context(),
            }
        if action not in {"native_edit", "native_create"}:
            return super().action(action, args)
        self.guard()
        self.assert_bound()
        if self.completion:
            raise StateError("Terminal task rejects further actions")
        self.ledger.spend("tool_actions")
        if self.config["experimental_native_tools_trial"] != "B":
            raise StateError("Native mutation unavailable in arm A")
        expected = {"path", "find", "replace"} if action == "native_edit" else {"path", "content"}
        if set(args) != expected or any(not isinstance(v, str) for v in args.values()):
            raise ValueError("Invalid native mutation fields")
        path = args["path"]
        if action == "native_create":
            before = None
            change = {"path": path, "operation": "create", "content": args["content"]}
        else:
            reference = self.ledger.state.get("native_observed", {}).get(path)
            if not reference:
                raise ValueError("Read current source before native edit")
            before = self.editor.read_bytes(path)[0].decode("utf-8-sig")
            change = {
                "path": path,
                "operation": "replace",
                "version_ref": reference,
                "edits": [{"find": args["find"], "replace": args["replace"]}],
            }
        self.ledger.prepaid_tool = True
        try:
            result = super().action("propose", {"changes": [change]})
        finally:
            self.ledger.prepaid_tool = False
        if result["observation"]["status"] != "changed_and_checked":
            return result
        after, version = self.editor.read_bytes(path)
        self.ledger.state.setdefault("native_observed", {}).pop(path, None)
        self.ledger.record("native_mutation_finished", {"path": path})
        result["observation"]["native_outcome"] = {
            "version": version,
            "before": before,
            "after": after.decode("utf-8-sig"),
        }
        if before is None:
            result["observation"]["native_outcome"]["operation"] = "create"
        return result
