"""Explicit whole-job credits; sealed reserve requires a canonical Primary disposition."""

from pathlib import Path

from general_state import StateError, read

VERSION = "review-rework-v1"
REFOCUS_VERSION = "review-rework-refocus-v1"
DIAGNOSTIC_VERSION = "review-rework-diagnostic-v1"
TASK_VERSION = "task-rework-v1"
FIRST = {
    "model_requests": 16,
    "tool_actions": 24,
    "evidence_actions": 16,
    "edits": 4,
    "post_edit_checks": 4,
    "initial_checks": 1,
    "format_preparations": 6,
    "protocol_recoveries": 2,
    "edit_recoveries": 2,
    "reserved_output_tokens": 16 * 12288,
    "seconds": 1800,
}
RESERVE = {
    "model_requests": 8,
    "tool_actions": 12,
    "evidence_actions": 6,
    "edits": 2,
    "post_edit_checks": 2,
    "initial_checks": 0,
    "format_preparations": 4,
    "protocol_recoveries": 2,
    "edit_recoveries": 1,
    "reserved_output_tokens": 8 * 12288,
    "seconds": 600,
}
TOTAL = {key: FIRST[key] + RESERVE[key] for key in FIRST}
TASK_RESERVE = {
    **RESERVE,
    "model_requests": 14,
    "tool_actions": 24,
    "evidence_actions": 14,
    "edits": 4,
    "post_edit_checks": 4,
    "format_preparations": 7,
    "edit_recoveries": 2,
    "reserved_output_tokens": 14 * 12288,
    "seconds": 900,
}


def budgets(profile):
    if not selected({"experimental_strata_continuation": profile}):
        raise StateError("Unknown durable budget profile")
    reserve = TASK_RESERVE if profile == TASK_VERSION else RESERVE
    return FIRST, reserve, {key: FIRST[key] + reserve[key] for key in FIRST}


def selected(config):
    return config.get("experimental_strata_continuation") in (
        VERSION,
        REFOCUS_VERSION,
        DIAGNOSTIC_VERSION,
        TASK_VERSION,
    )


def bind(ledger, config):
    expected = config.get("experimental_strata_continuation") if selected(config) else None
    if ledger.sequence:
        if ledger.state.get("budget_profile") != expected:
            raise StateError("Prepared budget profile differs;old tasks cannot upgrade/refill")
    elif expected:
        ledger.state["budget_profile"] = expected
    if expected:
        total = budgets(expected)[2]
        ledger.limits = {k: v for k, v in total.items() if k != "seconds"}
        ledger.seconds = total["seconds"]


def validate_disposition(host, feedback, previous):
    """Require all findings dispositioned; model judgments never grant authority."""
    from general_prepare import sha

    diagnostic = host.config.get("experimental_strata_continuation") == DIAGNOSTIC_VERSION
    task_return = host.config.get("experimental_strata_continuation") == TASK_VERSION
    if task_return and previous.get("status") == "ready_for_primary":
        review = previous.get("review") or {}
        if (
            feedback["kind"] != "confirmed_defect"
            or feedback.get("review_disposition") is not None
            or review.get("status") != "ready_for_primary"
            or (review.get("report") or {}).get("status") != "pass_to_primary"
            or (review.get("report") or {}).get("findings") != []
        ):
            raise StateError(
                "Primary reserve requires one settled clean fresh review and bound defect"
            )
        path = Path(review["archive"]) / "readonly-report.json"
        if not path.resolve().is_relative_to((host.repo_root / ".agent/reviews").resolve()):
            raise StateError("Canonical Reviewer archive outside this task project")
        if read(path)["report"] != review["report"]:
            raise StateError("Canonical Reviewer report differs from settled result")
        # feedback_shape and record_primary_return still verify the prior result,
        # contract IDs, current source/check/quote, assistance, one-return state.
        # No fresh review is permitted until a real edit and full current check.
        return
    if diagnostic:
        from failed_draft_diagnostic import validate_feedback

        review = validate_feedback(host, feedback, previous)
        if review is None:
            return
    elif feedback["kind"] != "confirmed_defect" or previous.get("status") != "rework":
        raise StateError("Review reserve only follows a settled Reviewer rework")
    else:
        review = previous.get("review", {})
    if (
        review.get("status") != "ready_for_primary"
        or review.get("report", {}).get("status") != "rework"
    ):
        raise StateError("Valid fresh Reviewer rework required")
    disposition = feedback.get("review_disposition")
    if not isinstance(disposition, dict) or set(disposition) != {
        "report_sha256",
        "identity",
        "findings",
    }:
        raise StateError("Canonical report hash,identity and all finding dispositions required")
    path = Path(review["archive"]) / "readonly-report.json"
    if not path.resolve().is_relative_to((host.repo_root / ".agent/reviews").resolve()):
        raise StateError("Canonical Reviewer archive outside this task project")
    report = read(path)
    if (
        disposition["report_sha256"] != sha(path)
        or disposition["identity"] != report["identity"]
        or report["report"] != review["report"]
    ):
        raise StateError("Canonical Reviewer report/identity mismatch")
    rows = disposition["findings"]
    findings = report["report"]["findings"]
    if not isinstance(rows, list) or len(rows) != len(findings) or not rows:
        raise StateError("Every Reviewer finding needs one Primary disposition")
    confirmed = set()
    for i, row in enumerate(rows):
        if (
            not isinstance(row, dict)
            or set(row) != {"index", "decision", "reason"}
            or type(row["index"]) is not int
            or row["index"] != i
            or row["decision"] not in {"confirmed_defect", "optional_nonblocking", "rejected"}
            or not isinstance(row["reason"], str)
            or not 1 <= len(row["reason"]) <= 2000
        ):
            raise StateError("Ordered complete bounded Primary dispositions required")
        if row["decision"] == "confirmed_defect":
            confirmed.add(disposition["report_sha256"][:16] + "-" + str(i))
    defects = feedback.get("defect", {}).get("findings", [])
    if not confirmed or {d.get("id") for d in defects} != confirmed:
        raise StateError("Return only the exact confirmed canonical findings")
    for defect in defects:
        i = int(defect["id"].rsplit("-", 1)[1])
        if defect.get("contract_id") != findings[i]["contract_id"]:
            raise StateError("Confirmed finding contract differs from canonical review")
