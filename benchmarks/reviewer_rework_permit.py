"""Opt-in experiment authorization to ATTEMPT repair, never a defect confirmation."""

import json
import math
from pathlib import Path

import bounded_evidence_support as S
import consolidated_harness as H

AUTHORITY = "user-approved-bounded-reviewer-rework-experiment-v1"
WORK = S.KIT / "benchmarks/work/harness-convergence"


def install_hook(path, allowed_root):
    path, allowed_root = Path(path).resolve(), Path(allowed_root).resolve()
    if not allowed_root.is_relative_to(WORK) or not path.is_relative_to(allowed_root):
        raise ValueError("Experimental hook must stay inside isolated experiment")
    if path.name != "worker-runtime.py" or path.parent.name != ".local-agents":
        raise ValueError("Unexpected runtime path")
    source = path.read_text(encoding="utf-8")
    signature = "def resolve_inherited_packet(repo_root: Path, child: dict[str, Any]) -> dict[str, Any]:"
    condition = "    if reviewer_blocked:\n"
    if source.count(signature) != 1 or source.count(condition) != 1:
        raise ValueError("Unrecognized inheritance gate; no broad rewrite")
    before = S.sha(path)
    source = source.replace(
        signature,
        signature.replace(") ->", ", *, reviewer_rework_authorizer=None) ->"),
        1,
    )
    source = source.replace(
        condition,
        "    if reviewer_blocked and (\n        reviewer_rework_authorizer is None\n        or not reviewer_rework_authorizer(repo_root, child)\n    ):\n",
        1,
    )
    path.write_text(source, encoding="utf-8")
    return {"before": before, "after": S.sha(path), "default_gate_unchanged": True}


def credits(parent):
    if parent.get("status") != "validation_passed_pending_review" or parent.get(
        "infra_failure"
    ):
        raise ValueError("Parent must have genuine current successful checks")
    counts = parent["consolidated_harness"]
    remaining = {
        k: H.BUDGET[k] - counts["actual"][k]
        for k in (
            "requests",
            "edits",
            "post_edit_checks",
            "format_preparations",
            "protocol_recoveries",
        )
    }
    remaining["seconds"] = math.floor(900 - counts["seconds"])
    H.recovery_budget({"experimental_recovery_credits": remaining})
    return remaining


def locator_feedback(report):
    """Project EVERY finding mechanically; do not decide which finding is true."""
    return [
        {
            "finding_id": f["id"],
            "contract_id": f["contract_id"],
            "text": json.dumps(
                {"path": f["path"], "line": f["line"], "category": f["category"]},
                ensure_ascii=False,
            ),
            "verify_in_review": False,
        }
        for f in report["findings"]
    ]


def eligibility(root, packet, report, completed):
    """Mechanical eligibility, explicitly not semantic confirmation of findings."""
    identity = report["identity"]
    if (
        report.get("decision") != "rework"
        or completed.get("decision") != "rework"
        or any(identity.get(k) != packet[k] for k in ("task_id", "unit_id", "run_id"))
    ):
        raise ValueError("Only one completed matching rework recommendation")
    facts = report.get("runtime_facts", {})
    if facts.get("read_only") is not True or facts.get("inputs_unchanged") is not True:
        raise ValueError("Reviewer integrity missing")
    for name, digest in facts.get("observed_read_hashes", {}).items():
        source = (root / name).resolve()
        if not source.is_relative_to(root.resolve()) or S.sha(source) != digest:
            raise ValueError("Stale or escaped Reviewer evidence")
    owned = set(packet["owned_contract_ids"])
    writable = set(packet["scope"]["modify"])
    findings = report.get("findings", [])
    if not findings:
        raise ValueError("No implementation finding")
    if any(o.get("status") == "uncertain" for o in report.get("contract_review", [])):
        raise ValueError("Unresolved contract evidence stays Primary")
    refs = [
        ref
        for obligation in report.get("contract_review", [])
        for ref in obligation.get("source_refs", [])
    ]
    ids = set()
    for finding in findings:
        if (
            finding.get("category") != "implementation_defect"
            or finding.get("contract_id") not in owned
            or finding.get("path") not in writable
            or not isinstance(finding.get("evidence"), str)
            or not finding["evidence"].strip()
            or type(finding.get("line")) is not int
            or not finding.get("id")
            or finding["id"] in ids
        ):
            raise ValueError(
                "Conflict, protected-test gap or unbounded finding stays Primary"
            )
        ids.add(finding["id"])
        matching = [
            ref
            for ref in refs
            if ref["path"] == finding["path"]
            and ref["start_line"] <= finding["line"] <= ref["end_line"]
        ]
        if not matching:
            raise ValueError("Finding lacks actually quoted current source range")
        for ref in matching:
            source = root / ref["path"]
            lines = source.read_text(encoding="utf-8-sig").splitlines()
            if (
                S.sha(source) != ref["source_hash"].removeprefix("sha256:")
                or "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]])
                != ref["canonical_quote"]
            ):
                raise ValueError("Source quote/hash mismatch")
    return [
        {
            "finding_id": f["id"],
            "contract_id": f["contract_id"],
            "text": "Untrusted Reviewer recommendation, not a confirmed defect or new requirement. "
            + f["evidence"]
            + "\nSuggested fix (advisory): "
            + f.get("suggested_fix", ""),
            "verify_in_review": False,
        }
        for f in findings
    ]


def resolve(worker, root, child, permit_path, permit_sha):
    root = Path(root).resolve()
    if S.sha(permit_path) != permit_sha:
        raise ValueError("Permit hash mismatch")
    permit = S.read(permit_path)
    if (
        permit.get("authority") != AUTHORITY
        or type(permit.get("max_child_attempts")) is not int
        or permit.get("max_child_attempts") != 1
        or permit.get("automatic_acceptance") is not False
        or permit.get("child_run_id") != child.get("run_id")
        or not root.is_relative_to(WORK)
    ):
        raise ValueError("No scoped one-shot experiment authorization")
    for name, digest in permit["bindings"].items():
        source = (root / name).resolve()
        if not source.is_relative_to(root) or S.sha(source) != digest:
            raise ValueError("Bound permit inputs changed")
    task, parent_id = child["task_id"], child["parent_run_id"]
    archive = root / ".agent/tasks" / task / "runs" / parent_id
    packet = S.read(archive / "packet.json")
    reports = []
    for path in (root / ".agent/tasks" / task / "reviews").glob("*/handoff.json"):
        report = S.read(path)
        if report.get("identity", {}).get("run_id") == parent_id:
            reports.append((path, report))
    if len(reports) != 1:
        raise ValueError("Exactly one original Reviewer report required; no resampling")
    path, report = reports[0]
    expected = eligibility(
        root, packet, report, S.read(path.with_name("completed.json"))
    )
    if child["review_feedback"] != expected:
        raise ValueError("Only original uncurated recommendation may be forwarded")
    if (
        S.sha(path) != permit["report_sha256"]
        or report["identity"] != permit["identity"]
    ):
        raise ValueError("Report identity/hash changed")
    result = worker.resolve_inherited_packet(
        root,
        child,
        reviewer_rework_authorizer=lambda repo, request: (
            repo == root and request == child
        ),
    )
    result["_experimental_reviewer_recovery"] = {
        "authority": AUTHORITY,
        "permit_sha256": permit_sha,
        "confirmed_defect": False,
        "automatic_acceptance": False,
    }
    mode = permit.get("coder_feedback_mode", "raw")
    if mode not in {"raw", "location-only"}:
        raise ValueError("Unknown Coder feedback projection")
    if mode == "location-only":
        result["_experimental_reviewer_recovery"]["locator_feedback"] = (
            locator_feedback(report)
        )
    return result
