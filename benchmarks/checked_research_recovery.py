"""Experiment-only remaining-credit policy for a checked, stalled Coder draft."""

import math
import sys
from pathlib import Path

import explorer_recovery_controller as ORIGINAL

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local-agents"))
from bounded import consolidated_harness as H


def remaining(parent):
    facts = parent["consolidated_harness"]
    actual = facts["actual"]
    if (
        parent["status"] != "failed"
        or parent.get("infra_failure")
        or parent["failure_reason"] != "Two unchanged prepared proposals"
        or facts["budget"] != H.BUDGET
        or actual["noops"] != 2
        or actual["scripted_requests"] != 0
        or actual["model_requests"] != actual["requests"]
        or actual["initial_checks"] != 1
        or actual["edits"] != actual["post_edit_checks"]
        or not 0 < actual["edits"] < H.BUDGET["edits"]
    ):
        raise ValueError("Not an ordinary checked post-edit no-progress parent")
    keys = (
        "requests",
        "edits",
        "post_edit_checks",
        "format_preparations",
        "protocol_recoveries",
    )
    if any(
        type(actual[k]) is not int or not 0 <= actual[k] <= H.BUDGET[k] for k in keys
    ):
        raise ValueError("Invalid parent accounting")
    seconds = facts["seconds"]
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Invalid parent time")
    credits = {key: H.BUDGET[key] - actual[key] for key in keys}
    credits["seconds"] = math.floor(H.BUDGET["seconds"] - seconds)
    H.recovery_budget({"experimental_recovery_credits": credits})
    return credits


def feedback(report, root, required):
    if not set(required) <= set(report.get("observed_hashes", {})):
        raise ValueError("Required evidence was not observed")
    # Existing helper checks success, findings, exact approved paths and hashes.
    return ORIGINAL.research_feedback(report, root, set(required))
