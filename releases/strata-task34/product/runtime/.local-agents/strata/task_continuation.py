"""One task-bound follow-up, shared credits and explicit first-stage reserves."""

import copy

from general_state import BudgetExhausted, StateError, fingerprint, read

FLAG = "experimental_strata_continuation"
VERSION = "task-v1"
FIRST = {
    "investigate": {
        "model_requests": 4,
        "tool_actions": 8,
        "evidence_actions": 6,
        "protocol_recoveries": 1,
        "seconds": 450,
    },
    "implement": {
        "model_requests": 10,
        "tool_actions": 16,
        "evidence_actions": 10,
        "edits": 3,
        "post_edit_checks": 3,
        "protocol_recoveries": 1,
        "seconds": 1100,
    },
}


def enabled(config):
    from review_rework_budget import selected

    return config.get(FLAG) == VERSION or selected(config)


def validate_config(config, kind):
    if config.get(FLAG) is None:
        return
    if not enabled(config) or config.get("experimental_strata_task") is not True:
        raise StateError("Explicit task-v1 continuation opt-in required")
    if config.get("experimental_strata_capabilities") or config.get(
        "experimental_native_tools_trial"
    ):
        raise StateError("Continuation trial supports ordinary task profiles only")
    if kind not in FIRST:
        raise StateError("Continuation not a Reviewer profile")
    from review_rework_budget import selected

    if selected(config) and kind != "implement":
        raise StateError("Review-rework budget is implementation-only")


class StageLedger:
    """Delegate durable accounting; add no credits and change no global limits."""

    def __init__(self, ledger, kind, stage):
        self.delegate, self.kind, self.stage = ledger, kind, stage

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def spend(self, key, count=1):
        if type(count) is not int or count < 0:
            raise StateError("Invalid stage resource reservation")
        if self.state.get("budget_profile"):
            cap = self.current()["limits"].get(key)
            if cap is not None and self.state["used"].get(key, 0) + count > cap:
                raise BudgetExhausted("Review-rework stage " + key + " exhausted")
            return self.delegate.spend(key, count)
        cap = FIRST[self.kind].get(key)
        used = self.state["used"].get(key, 0)
        if self.state.get("report_repair_profile") and key == "model_requests":
            from investigation_delivery import repairs

            used -= repairs(self.state)
            cap = 4 if self.stage == 1 else 8
        if (
            cap is not None
            and (
                self.stage == 1
                or (self.state.get("report_repair_profile") and key == "model_requests")
            )
            and used + count > cap
        ):
            raise BudgetExhausted("First-stage " + key + " exhausted;no automatic follow-up")
        self.delegate.spend(key, count)

    def remaining_seconds(self):
        remaining = self.delegate.remaining_seconds()
        if self.state.get("budget_profile"):
            import time

            from review_rework_budget import budgets

            initial, reserve, _ = budgets(self.state["budget_profile"])

            active = self.state["active"]
            elapsed = max(0, time.time() - active["started"]) if active else 0
            base = (
                self.state.get("review_rework_start", {}).get("active_seconds", 0)
                if self.stage == 2
                else 0
            )
            cap = initial["seconds"] if self.stage == 1 else reserve["seconds"]
            return max(0, min(remaining, cap - self.state["active_seconds"] + base - elapsed))
        if self.stage == 1:
            active = self.state["active"]
            import time

            elapsed = max(0, time.time() - active["started"]) if active else 0
            remaining = min(
                remaining, FIRST[self.kind]["seconds"] - self.state["active_seconds"] - elapsed
            )
        return max(0, remaining)

    def current(self):
        total = self.delegate.current()
        effective = dict(total["limits"])
        if self.state.get("budget_profile"):
            from review_rework_budget import budgets

            initial, reserve, _ = budgets(self.state["budget_profile"])

            base = self.state.get("review_rework_start", {}).get("used", {})
            for key in effective:
                effective[key] = min(
                    effective[key],
                    initial[key] if self.stage == 1 else base.get(key, 0) + reserve[key],
                )
            return {
                **total,
                "limits": effective,
                "task_limits": total["limits"],
                "remaining_seconds": round(self.remaining_seconds(), 3),
                "continuation_stage": self.stage,
                "credits_replenished": False,
                "budget_profile": self.state["budget_profile"],
            }
        if self.stage == 1:
            for key, cap in FIRST[self.kind].items():
                if key in effective:
                    effective[key] = min(effective[key], cap)
        repair_budget = {}
        if self.state.get("report_repair_profile"):
            from investigation_delivery import repairs

            stage_repairs = self.state.get("report_repair_requests", {}).get(str(self.stage), 0)
            if self.stage == 1:
                effective["model_requests"] = 5
            repair_budget = {
                "report_repair": {
                    "ordinary_remaining": (4 if self.stage == 1 else 8)
                    - self.state["used"]["model_requests"]
                    + repairs(self.state),
                    "reserved_remaining_this_stage": 1 - stage_repairs,
                    "only_report": bool(
                        self.state.get("report_only_request")
                        or self.state.get("report_retry_pending")
                    ),
                    "pending": self.state.get("report_retry_pending", False),
                    "requests_by_stage": dict(self.state.get("report_repair_requests", {})),
                    "rule": "Reserved request only after host-confirmed report protocol failure;no read/search;all requests/time/output charged",
                }
            }
        return {
            **total,
            "limits": effective,
            "task_limits": total["limits"],
            "remaining_seconds": round(self.remaining_seconds(), 3),
            "continuation_stage": self.stage,
            "first_stage_limits": FIRST[self.kind],
            "credits_replenished": False,
            **repair_budget,
        }


def feedback_shape(host, feedback):
    from failed_draft_diagnostic import enabled as diagnostic_enabled

    diagnostic = diagnostic_enabled(host.config)
    required = {
        "kind",
        "previous_attempt",
        "result_sha256",
        "source_hashes",
        "contract_ids",
        "text",
        "assisted",
    }
    if host.ledger.state.get("budget_profile"):
        required |= {"defect", "review_disposition"}
    if diagnostic:
        required.add("diagnostic")
    if not isinstance(feedback, dict) or set(feedback) not in (required, required | {"defect"}):
        raise StateError("Bound feedback fields required;unknown fields rejected")
    if feedback["kind"] not in (
        {"confirmed_defect", "failed_check_repair"}
        if diagnostic
        else {"verify_or_extend_evidence", "confirmed_defect"}
    ):
        raise StateError("Unknown follow-up kind")
    if (
        type(feedback["assisted"]) is not bool
        or not isinstance(feedback["text"], str)
        or not 1 <= len(feedback["text"]) <= 2000
    ):
        raise StateError("Bounded follow-up text and explicit assistance required")
    owned = {b["id"] for b in host.packet["required_behavior"]}
    ids = feedback["contract_ids"]
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(i, str) or i not in owned for i in ids)
    ):
        raise StateError("Follow-up requires existing contract IDs")
    if len(set(ids)) != len(ids):
        raise StateError("Duplicate follow-up contract ID")
    state = host.ledger.state
    attempts = state["attempts"]
    if (
        not host.resume_requested
        or len(attempts) != 1
        or state.get("task_followup")
        or state["active"]
        or state["pending_model"]
        or state["status"]
        not in ({"failed", "budget_exhausted"} if diagnostic else {"ready_for_primary"})
    ):
        raise StateError("One follow-up requires one settled ready task")
    if feedback["previous_attempt"] != attempts[-1]:
        raise StateError("Follow-up prior attempt mismatch")
    previous = (
        host.repo_root
        / ".agent/tasks"
        / host.packet["task_id"]
        / "workflow/runs"
        / attempts[-1]
        / "result.json"
    )
    from general_prepare import sha

    if not previous.is_file() or sha(previous) != feedback["result_sha256"]:
        raise StateError("Prior workflow result mismatch")
    result = read(previous)
    if result["status"] not in (
        {"failed", "budget_exhausted"}
        if diagnostic
        else {"ready_for_primary", "rework", "review_incomplete"}
    ):
        raise StateError("No settled complete worker artifact")
    if feedback["source_hashes"] != host.current_hashes():
        raise StateError("Follow-up source version mismatch")
    if feedback["kind"] == "confirmed_defect":
        if host.policy.get("role") == "investigate" or "defect" not in feedback:
            raise StateError("Confirmed defect uses existing implementation return only")
        if feedback["defect"].get("assisted") != feedback["assisted"]:
            raise StateError("Defect assistance classification mismatch")
    elif "defect" in feedback and not (diagnostic and feedback["defect"] is None):
        raise StateError("Evidence follow-up must not invent a defect")
    if state.get("budget_profile"):
        from review_rework_budget import validate_disposition

        validate_disposition(host, feedback, result)
    return result


def initialize(host):
    if not enabled(host.config):
        if getattr(host, "continuation_feedback", None) is not None:
            raise StateError("Continuation opt-in absent")
        return
    if host.policy.get("role") == "review":
        raise StateError("Continuation not a Reviewer profile")
    kind = "investigate" if host.policy.get("role") == "investigate" else "implement"
    validate_config(host.config, kind)
    host.ledger.check_begin(host.packet["run_id"], resume=host.resume_requested)
    feedback = getattr(host, "continuation_feedback", None)
    if host.resume_requested:
        previous = feedback_shape(host, feedback)
        if feedback["kind"] == "confirmed_defect":
            from general_return import record_primary_return

            record_primary_return(host, feedback["defect"])
        host.ledger.state["task_followup"] = {
            "feedback": copy.deepcopy(feedback),
            "previous_worker_report": previous["worker"].get("report"),
            "previous_worker_archive": previous["worker"]["archive"],
            "acceptance": False,
        }
        if host.ledger.state.get("budget_profile"):
            host.ledger.state["review_rework_start"] = {
                "used": copy.deepcopy(host.ledger.state["used"]),
                "active_seconds": host.ledger.state["active_seconds"],
            }
        host.ledger.record("task_followup_bound", {"feedback_sha256": fingerprint(feedback)})
        stage = 2
    else:
        if feedback is not None:
            raise StateError("Feedback requires explicit resume")
        stage = 1
    host.ledger = StageLedger(host.ledger, kind, stage)
    from investigation_delivery import repair_enabled

    if repair_enabled(host.config):
        host.ledger.state["report_repair_profile"] = "reserved-v1"
        host.ledger.state["report_only_request"] = False
        host.ledger.state["report_retry_pending"] = False


def context(host):
    if not enabled(host.config):
        return {}
    value = {
        "stage": host.ledger.stage,
        "shared_budget": True,
        "instruction": "Autonomously complete this stage within displayed limits. First-stage handoff is provisional;one Primary follow-up may use the remaining original credits. No permission or contract reset.",
    }
    if host.ledger.state.get("task_followup"):
        old = copy.deepcopy(host.ledger.state["task_followup"])
        old["feedback"].pop("source_hashes", None)
        old["feedback"].pop("review_disposition", None)
        value["followup"] = old
    return {"task_continuation": value}
