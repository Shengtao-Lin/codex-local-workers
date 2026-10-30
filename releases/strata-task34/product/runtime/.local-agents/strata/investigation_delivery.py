"""Opt-in investigation completion, bounded final delivery and report repairs."""

from general_state import BudgetExhausted, StateError

FLAG = "experimental_strata_investigation_delivery"
REPAIR = "experimental_strata_report_repair"
ANSWER = "experimental_strata_answer_transport"


def compact_enabled(config):
    return config.get(ANSWER) == "compact-v1"


def enabled(config):
    return config.get(FLAG) == "investigation-v1"


def repair_enabled(config):
    return enabled(config) and config.get(REPAIR) in {"reserved-v1", "finalize-v1"}


def finalize_enabled(config):
    return enabled(config) and config.get(REPAIR) == "finalize-v1"


def validate(config, kind):
    if config.get(ANSWER) is not None and (
        not compact_enabled(config) or not finalize_enabled(config) or kind != "investigate"
    ):
        raise StateError("Compact answer requires finalize-v1 ordinary investigation")
    if config.get(FLAG) is None and config.get(REPAIR) is None:
        return
    if (
        not enabled(config)
        or kind != "investigate"
        or config.get("experimental_strata_task") is not True
        or config.get("experimental_strata_report_receipt") is not True
        or config.get("experimental_strata_report_binding") != "observed-line-v1"
        or (
            not finalize_enabled(config)
            and config.get("experimental_strata_continuation") != "task-v1"
        )
        or config.get("experimental_strata_continuation") not in (None, "task-v1")
        or config.get("experimental_strata_capabilities")
        or config.get("experimental_native_tools_trial")
        or config.get(REPAIR) not in (None, "reserved-v1", "finalize-v1")
    ):
        raise StateError("Investigation delivery requires ordinary bound task-v1 investigation")


def repairs(state):
    return sum(state.get("report_repair_requests", {}).values())


def report_failure(host, action, error=None, *, bridge=False):
    if not repair_enabled(host.config) or action != "report":
        return
    mechanical = {
        "exact_fields_required",
        "legal_status_required",
        "character_bound",
        "array_required",
        "item_bound",
        "wire_fields_required",
        "positive_integer_line_required",
        "finding_fields_required",
        "legal_severity_required",
        "description_bound",
        "zero_based_evidence_index_required",
    }
    errors = getattr(error, "details", {}).get("report_errors", [])
    if not bridge and (not errors or any(e["code"] not in mechanical for e in errors)):
        return
    stage = str(getattr(host.ledger, "stage", 1))
    if host.ledger.state.get("report_repair_requests", {}).get(stage, 0):
        raise BudgetExhausted("This stage's reserved report repair already used")
    host.ledger.state["report_retry_pending"] = True
    host.ledger.record("report_repair_pending", {"stage": stage, "extra_evidence": False})


def reserve_request(host):
    state = host.ledger.state
    if repair_enabled(host.config) and state.get("report_retry_pending"):
        stage = str(getattr(host.ledger, "stage", 1))
        if state.get("report_repair_requests", {}).get(stage, 0):
            raise BudgetExhausted("Reserved report repair exhausted")
        # Both reservations have to fit before either counter changes.
        ledger = getattr(host.ledger, "delegate", host.ledger)
        if (
            state["used"]["model_requests"] >= ledger.limits["model_requests"]
            or state["used"]["reserved_output_tokens"] + 12288
            > ledger.limits["reserved_output_tokens"]
        ):
            raise BudgetExhausted("Shared report repair resources exhausted")
        ledger.spend("model_requests")
        ledger.spend("reserved_output_tokens", 12288)
        state.setdefault("report_repair_requests", {})[stage] = 1
        state["report_retry_pending"] = False
        state["report_only_request"] = True
        ledger.record("reserved_report_request", {"stage": stage})
    else:
        if finalize_enabled(host.config):
            cap = 4 if getattr(host.ledger, "stage", None) == 1 else 8
            ordinary_used = state["used"]["model_requests"] - repairs(state)
            if ordinary_used >= cap:
                raise BudgetExhausted("Ordinary investigation requests exhausted")
        host.ledger.spend("model_requests")
        host.ledger.spend("reserved_output_tokens", 12288)
        state["report_only_request"] = False
        if finalize_enabled(host.config):
            state["final_delivery_request"] = ordinary_used + 1 == cap
            if state["final_delivery_request"]:
                host.ledger.record("final_delivery_reserved", {"new_evidence_allowed": False})


def assert_action(host, action):
    if (
        finalize_enabled(host.config)
        and host.ledger.state.get("final_delivery_request")
        and not host.ledger.state.get("report_only_request")
        and action not in {"report", "blocked"}
    ):
        raise StateError("Final delivery permits only report or blocked;no new evidence")
    if (
        repair_enabled(host.config)
        and (
            host.ledger.state.get("report_only_request")
            or host.ledger.state.get("report_retry_pending")
        )
        and action != "report"
    ):
        raise StateError(
            "Reserved report repair permits only report;no new evidence or other action"
        )


def delivery_context(host):
    if not finalize_enabled(host.config):
        return {}
    state = host.ledger.state
    cap = 4 if getattr(host.ledger, "stage", None) == 1 else 8
    remaining = cap - state["used"]["model_requests"] + repairs(state)
    return {
        "final_delivery": {
            "ordinary_requests_remaining": remaining,
            "next_request_report_only": remaining <= 1 or state.get("report_retry_pending", False),
            "instruction": "The last ordinary request must deliver report or blocked using existing evidence. Report insufficient_evidence when unresolved;do not invent a conclusion. One host-confirmed mechanical report correction is available;all calls,time,tools and output count.",
        }
    }


def normalize_answer(host, args):
    if not compact_enabled(host.config):
        return args
    fields = {"status", "summary", "evidence", "unknowns"}
    if not isinstance(args, dict) or set(args) != fields:
        from report_binding import ReportFeedbackError

        raise ReportFeedbackError(
            [{"field": "report", "code": "exact_fields_required", "required": sorted(fields)}]
        )
    # The mounted tool explicitly omits findings. No submitted information is
    # dropped; canonical compatibility gets an empty field, never model judgment.
    return {**args, "findings": []}
