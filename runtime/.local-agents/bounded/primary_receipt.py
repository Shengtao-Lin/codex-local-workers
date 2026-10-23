"""Output-only navigation receipt. Never an acceptance or rework authorization."""

import copy


def primary_next_step(report, summary, reviewer):
    """Describe a human-owned next step, never dispatch, repair or acceptance."""
    decision = summary.get("reviewer_decision")
    bound = (
        summary.get("reviewer_input_authenticated") is True and summary.get("reviewer_exit") == 0
    )
    coder_ready = (
        report.get("status") == "validation_passed_pending_review"
        and (report.get("validation") or {}).get("status") == "passed"
    )
    if decision in {"pass_to_primary", "rework", "escalate"}:
        if not (bound and coder_ready and summary.get("reviewer_started") is True):
            return "primary_evidence_reconciliation"
        return {
            "pass_to_primary": "primary_risk_routed_review",
            "rework": "primary_finding_disposition",
            "escalate": "primary_contract_or_scope_decision",
        }[decision]
    if decision == "failed":
        return "primary_review_infrastructure_diagnosis"
    if decision == "NOT_RUN" and summary.get("reviewer_started") is False:
        if bound and coder_ready and reviewer.get("mode") == "offline-input-inspection":
            return "offline_inspection_only"
        if report.get("status") in {"failed", "blocked", "interrupted", "policy_violation"}:
            return "primary_failure_disposition"
    return "primary_evidence_reconciliation"


def build(report, summary, reviewer, paths):
    truncated = []

    def text(value, label, limit=700):
        if value is None:
            return None
        value = str(value)
        if len(value) > limit:
            truncated.append(label)
            return value[:limit] + " ... [truncated; see full report]"
        return value

    def select(value, keys):
        value = value if isinstance(value, dict) else {}
        return {key: copy.deepcopy(value.get(key)) for key in keys}

    def rows(values, label, projector, limit=8):
        values = values if isinstance(values, list) else []
        if len(values) > limit:
            truncated.append(label)
        return {
            "items": [projector(item, index) for index, item in enumerate(values[:limit])],
            "total": len(values),
            "omitted": max(0, len(values) - limit),
        }

    validation = report.get("validation") or {}
    focused = validation.get("focused_tests") or {}
    references = report.get("evidence_refs") or {}
    attempts = references.get("validation_attempts") or []
    reviewer = reviewer or {}
    receipt = {
        "receipt_protocol": "bounded-primary-receipt-v1",
        "authority": "Navigation only. Not Primary acceptance, current-input verification, or permission to retry. Full canonical evidence and risk-routed review remain required.",
        "identity": select(report.get("identity"), ("task_id", "unit_id", "run_id")),
        "coder_status": report.get("status"),
        "stop_reason": text(report.get("failure_reason"), "stop_reason"),
        "failure_signature": text(report.get("failure_signature"), "failure_signature"),
        "coder_next_action_required": report.get("next_action_required"),
        "next_action_required": primary_next_step(report, summary, reviewer),
        "risk": copy.deepcopy(report.get("risk")),
        "review_route": report.get("review_route"),
        "execution": copy.deepcopy(report.get("consolidated_harness")),
        "infra_failure": select(report.get("infra_failure"), ("reason_code",)),
        "changed_files": rows(
            report.get("changed_files"),
            "changed_files",
            lambda item, _: select(item, ("path", "operation", "initial_sha256", "final_sha256")),
        ),
        "validation": {
            "status": validation.get("status"),
            "syntax": (validation.get("py_compile") or {}).get("status"),
            "focused_tests": focused.get("status"),
            "junit": select(
                focused.get("junit"), ("tests", "executed", "failures", "errors", "skipped")
            ),
            "recorded_inputs_unchanged": focused.get("inputs_unchanged"),
            "configured_checks": rows(
                validation.get("configured_checks"),
                "configured_checks",
                lambda item, index: {
                    **select(item, ("id", "status", "exit_code", "timed_out", "output_truncated")),
                    "failure_excerpt": text(item.get("output"), f"check_{index}", 1000)
                    if item.get("status") != "passed"
                    else None,
                },
            ),
            "test_failure_excerpt": text(
                (focused.get("diagnostic") or {}).get("excerpt"),
                "test_failure_excerpt",
                1000,
            )
            if focused.get("status") != "passed"
            else None,
            "supplemental_diagnostics": "Supplemental commands are counted in execution.actual; their raw results remain in run_archive/diagnostics-*.json, not acceptance credit.",
        },
        "reviewer": {
            **select(
                summary,
                (
                    "reviewer_started",
                    "reviewer_decision",
                    "reviewer_input_authenticated",
                    "reviewer_exit",
                    "reviewer_result_error",
                    "reviewer_reported_decision",
                ),
            ),
            "report_mode": reviewer.get("mode"),
            "judgment_source": "Independent model recommendation, not Primary acceptance.",
            "findings": rows(
                reviewer.get("findings"),
                "reviewer_findings",
                lambda item, index: {
                    **select(item, ("id", "severity", "category", "path", "line", "contract_id")),
                    "evidence": text(item.get("evidence"), f"finding_{index}_evidence"),
                    "suggested_fix": text(item.get("suggested_fix"), f"finding_{index}_fix"),
                },
            ),
            "uncertainties": rows(
                reviewer.get("unverified_claims"),
                "reviewer_uncertainties",
                lambda item, index: text(item, f"uncertainty_{index}"),
            ),
        },
        "automatic_coder_rework": summary.get("automatic_coder_rework"),
        "primary_acceptance": "not_recorded_by_this_entry",
        "evidence": {
            **copy.deepcopy(paths),
            **select(references, ("run_archive", "cumulative_diff", "events")),
            "latest_validation_attempt": attempts[-1] if attempts else None,
            "validation_attempt_count": len(attempts),
        },
        "truncated_fields": truncated,
    }
    return receipt
