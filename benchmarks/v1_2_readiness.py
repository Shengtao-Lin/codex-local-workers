"""Read-only v1.2 pipeline assessment over one frozen two-round batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import explorer_semantic_audit as SEMANTIC

KIT = Path(__file__).resolve().parents[1]
WORK = KIT / "benchmarks" / "work" / "stability-v1"


def primary_decision(result: dict) -> str | None:
    workspace = Path(result["workspace"]).resolve()
    packet = json.loads(
        (workspace / ".agent" / "packet.json").read_text(encoding="utf-8")
    )
    task_id, run_id = packet["task_id"], packet["run_id"]
    path = (
        workspace / ".agent" / "tasks" / task_id / "runs" / run_id / "review.json"
    ).resolve()
    if not path.is_relative_to(workspace) or not path.is_file():
        return None
    review = json.loads(path.read_text(encoding="utf-8"))
    if any(
        review.get(key) != value
        for key, value in {
            "task_id": task_id,
            "run_id": run_id,
            "unit_id": packet["unit_id"],
        }.items()
    ):
        raise ValueError(f"Primary review identity mismatch: {workspace}")
    return review.get("decision")


def first_repair_immediate_edit(result: dict) -> bool | None:
    """Recover the first model action after the first failed validation from its run archive."""
    workspace = Path(result["workspace"]).resolve()
    packet = json.loads(
        (workspace / ".agent" / "packet.json").read_text(encoding="utf-8")
    )
    path = (
        workspace
        / ".agent"
        / "tasks"
        / packet["task_id"]
        / "runs"
        / packet["run_id"]
        / "events.jsonl"
    ).resolve()
    if not path.is_relative_to(workspace):
        raise ValueError(f"Coder event archive escapes workspace: {workspace}")
    events = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]
    if not any(event.get("event") == "repair_focus_issued" for event in events):
        return None
    for position, event in enumerate(events):
        if (
            event.get("event") != "tool_action"
            or event.get("facts", {}).get("action") != "VALIDATE"
            or event.get("facts", {}).get("status") != "failed"
        ):
            continue
        for next_event in events[position + 1 :]:
            if next_event.get("event") == "tool_action":
                return next_event.get("facts", {}).get("action") in {
                    "SAFE_CREATE",
                    "SAFE_REPLACE",
                    "SAFE_REPLACE_LINE",
                }
    return False


def assess_pipeline(
    audit: dict, summary: dict, *, gate_version: str = "original"
) -> dict:
    if gate_version not in {"original", "role-aligned-v1"}:
        raise ValueError(f"unknown pipeline gate version: {gate_version}")
    explorer = SEMANTIC.assess_release(audit, summary, gate_version=gate_version)
    return assess_worker_pipeline(explorer, summary, gate_version=gate_version)


def assess_worker_pipeline(explorer: dict, summary: dict, *, gate_version: str) -> dict:
    """Shared Coder/Reviewer/Primary thresholds; caller owns its explicit Explorer gate."""
    results = summary["results"]
    reasons = list(explorer["reasons"])
    focused = [
        result
        for result in results
        if result.get("metrics", {}).get("repair_focus_issued", 0) > 0
    ]
    immediate = sum(
        bool(
            item["metrics"].get(
                "first_repair_next_action_is_edit",
                item["metrics"].get("next_action_is_edit"),
            )
        )
        for item in focused
    )
    validated = sum(item.get("coder_status") == "ready_for_review" for item in focused)
    if len(focused) < 10:
        reasons.append(f"Coder repair_focus denominator {len(focused)} is below 10")
    else:
        if gate_version == "original" and immediate < math.ceil(0.7 * len(focused)):
            reasons.append(
                f"Coder immediate repair edits {immediate}/{len(focused)} are below 70%"
            )
        if validated < math.ceil(0.9 * len(focused)):
            reasons.append(
                f"Coder eventual focused validation {validated}/{len(focused)} is below 90%"
            )
    reached = [
        item for item in results if item.get("coder_status") == "ready_for_review"
    ]
    reviewer_pass = sum(
        item.get("reviewer_decision") == "pass_to_primary" for item in reached
    )
    citation_required = [
        item for item in reached if item.get("metrics", {}).get("citation_required")
    ]
    citation_pass = sum(
        item["metrics"].get("citation_converged") is True for item in citation_required
    )
    if (
        not reached
        or reviewer_pass != len(reached)
        or citation_pass != len(citation_required)
    ):
        reasons.append(
            "Reviewer pass/source citation did not converge for every reached unit"
        )
    infra = sum(bool(item.get("infra_failure")) for item in results)
    if infra:
        reasons.append(f"{infra} infrastructure failures occurred in the frozen batch")
    protocol = sum(bool(item.get("qualified_pass")) for item in results)
    primary = sum(item.get("primary_decision") == "accept" for item in results)
    minimum = math.ceil(0.9 * len(results))
    if protocol < minimum or primary < minimum:
        reasons.append(
            f"protocol/Primary acceptance {protocol}/{len(results)}, {primary}/{len(results)} "
            f"is below {minimum}/{len(results)}"
        )
    critical = [item for item in results if item.get("case") == "sample-identity"]
    if len(critical) != 2 or any(
        item.get("coder_status") != "ready_for_review"
        or item.get("primary_decision") != "accept"
        for item in critical
    ):
        reasons.append(
            "known two-file sample-identity Coder contract did not pass both rounds"
        )
    return {
        "gate_version": gate_version,
        "pipeline_decision": "GO" if not reasons else "NO-GO",
        "reasons": reasons,
        "cells": len(results),
        "explorer": explorer,
        "coder": {
            "repair_focus_units": len(focused),
            "immediate_edit": immediate,
            "eventual_validation": validated,
        },
        "reviewer": {
            "reached": len(reached),
            "pass_to_primary": reviewer_pass,
            "citation_required": len(citation_required),
            "citation_converged": citation_pass,
        },
        "infrastructure_failures": infra,
        "protocol_e2e": protocol,
        "primary_accepted": primary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audit",
        type=Path,
        default=KIT / "benchmarks" / "V1.2-EXPLORER-SEMANTIC-AUDIT.json",
    )
    parser.add_argument(
        "--gate-version",
        choices=("original", "role-aligned-v1"),
        default="original",
        help="Keep the original frozen decision or apply the preregistered role-aligned gate.",
    )
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    batch = (KIT / audit["batch"]).resolve()
    if batch.parent != WORK.resolve():
        raise ValueError("audit batch must be a direct frozen stability work directory")
    summary = json.loads((batch / "summary.json").read_text(encoding="utf-8"))
    SEMANTIC.verify_full_reports(summary)
    SEMANTIC.verify_repeat_inputs(summary)
    enriched = {
        **summary,
        "results": [
            {
                **result,
                "primary_decision": primary_decision(result),
                "metrics": {
                    **result["metrics"],
                    "first_repair_next_action_is_edit": first_repair_immediate_edit(
                        result
                    ),
                },
            }
            for result in summary["results"]
        ],
    }
    assessment = assess_pipeline(audit, enriched, gate_version=args.gate_version)
    runner_hash = hashlib.sha256(
        (KIT / "benchmarks/stability_e2e.py").read_bytes()
    ).hexdigest()
    if audit.get("runner_sha256", "").lower() != runner_hash:
        assessment["reasons"].append(
            "frozen audit runner hash differs from current runner"
        )
        assessment["pipeline_decision"] = "NO-GO"
    assessment["remaining_release_checks"] = [
        "current three-role protocol compatibility archive",
        "capability matrix behavioral suite",
        "Primary integration review of the cumulative diff",
    ]
    print(json.dumps(assessment, ensure_ascii=False, indent=2))
    return int(assessment["pipeline_decision"] != "GO")


if __name__ == "__main__":
    raise SystemExit(main())
