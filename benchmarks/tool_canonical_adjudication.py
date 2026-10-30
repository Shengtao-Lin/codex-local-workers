"""Explicit Primary semantic adjudication of the registered citation trial."""

import argparse
import json

from capability_fit import WORK, write
from inherited_context_recovery import digest, read
from role_usage_facts import summarize
from tool_awaitable_trial import TARGET
from tool_reviewer_adjudication import OUTCOMES, review_identity

BASE = WORK / "tool-reviewer-canonical-1"


def adjudicate(label, outcome, rationale, cohort="tool-reviewer-canonical-1"):
    if cohort not in {"tool-reviewer-canonical-1", "tool-reviewer-baseline-1"}:
        raise ValueError("unregistered cohort")
    base = WORK / cohort
    registration = read(base / "registration.json")
    short_label = label.split("-", 1)[1]
    if short_label not in registration["arms_in_order"]:
        raise ValueError("unregistered review")
    facts = read(base / (label + ".inputs.json"))
    from pathlib import Path

    root = Path(facts["root"])
    report_path = base / (label + ".report.json")
    report = read(report_path)
    identity = review_identity(report, read(base / (label + ".request.json")))
    expected = {
        "false_pass": ("hidden", "pass_to_primary"),
        "correct_detection": ("hidden", "rework"),
        "correct_clean_pass": ("clean", "pass_to_primary"),
        "false_positive": ("clean", "rework"),
    }
    if outcome in expected and expected[outcome] != (facts["kind"], report["decision"]):
        raise ValueError("outcome contradicts artifact/terminal decision")
    if outcome == "invalid_report" and report["decision"] != "failed":
        raise ValueError("invalid_report requires failed terminal report")
    if outcome not in OUTCOMES or not rationale.strip():
        raise ValueError("explicit Primary rationale required")
    if digest(root / TARGET) != facts["source_sha256"]:
        raise ValueError("reviewed source drift")
    archive = (
        root / ".agent/tasks" / identity["task_id"] / "reviews" / identity["review_id"]
    )
    events = [
        json.loads(line)
        for line in (archive / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    write(
        base / (label + ".primary.json"),
        {
            "identity": identity,
            "outcome": outcome,
            "rationale": rationale,
            "actual_decision": report["decision"],
            "source_sha256": facts["source_sha256"],
            "report_sha256": digest(report_path),
            "local_usage_including_failed_turns": summarize(events),
            "seconds": read(base / (label + ".invocation.json"))["seconds"],
            "feature_accepted": False,
            "new_coder_invocation": False,
            "primary_semantic_adjudication": True,
        },
    )
    print({"review": label, "outcome": outcome})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("label")
    parser.add_argument("--outcome", choices=sorted(OUTCOMES), required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--cohort", default="tool-reviewer-canonical-1")
    args = parser.parse_args()
    adjudicate(args.label, args.outcome, args.rationale, args.cohort)
