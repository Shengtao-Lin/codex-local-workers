"""Narrow experiment policy: one zero-edit failure to local research to rework.

No acceptance, Reviewer disposition, scope or contract authority is delegated.
"""

import math

import bounded_evidence_support as S
import consolidated_harness as H


def remaining_credits(parent):
    facts = parent["consolidated_harness"]
    actual = facts["actual"]
    if (
        parent["status"] != "failed"
        or parent.get("infra_failure")
        or parent["failure_reason"] != "Two unchanged prepared proposals"
        or actual["edits"] != 0
        or actual["noops"] != 2
    ):
        raise ValueError("Only an ordinary zero-edit no-progress parent is eligible")
    credits = {
        key: H.BUDGET[key] - actual[key]
        for key in (
            "requests",
            "edits",
            "post_edit_checks",
            "format_preparations",
            "protocol_recoveries",
        )
    }
    credits["seconds"] = math.floor(H.BUDGET["seconds"] - facts["seconds"])
    H.recovery_budget({"experimental_recovery_credits": credits})
    return credits


def research_feedback(report, coder_root, approved):
    if report.get("status") != "success" or not report.get("findings"):
        raise ValueError("No completed local research")
    observed = report.get("observed_hashes", {})
    if not observed or any(
        p not in approved or S.sha(coder_root / p) != digest
        for p, digest in observed.items()
    ):
        raise ValueError("Unapproved or stale research evidence")
    return [
        {
            "source": "local_explorer_untrusted",
            "text": str(note),
            "verify_in_review": False,
        }
        for note in report["findings"]
    ]
