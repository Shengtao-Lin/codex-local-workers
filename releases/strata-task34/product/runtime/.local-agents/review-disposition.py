"""Primary-authored adjudication; model reports never authorize rework."""

from typing import Any


def adjudicate(report: dict[str, Any], sha256: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1 or payload.get("authority") != "primary":
        raise ValueError("disposition must be schema 1 and Primary-authored")
    if payload.get("report_sha256") != sha256 or payload.get("identity") != report.get("identity"):
        raise ValueError("disposition report hash/identity mismatch")
    if report.get("decision") not in {"pass_to_primary", "rework", "escalate"}:
        raise ValueError("cannot adjudicate an incomplete Reviewer report")
    resolution = payload.get("resolution")
    if resolution not in {"cleared", "contract_revision", "unresolved"}:
        raise ValueError("invalid Primary resolution")
    evidence = payload.get("evidence")
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(not isinstance(e, str) or not e.strip() for e in evidence)
    ):
        raise ValueError("Primary resolution requires substantive evidence")
    findings = report.get("findings", [])
    ids = [f["id"] for f in findings]
    entries = payload.get("findings")
    if not isinstance(entries, list):
        raise ValueError("Primary findings must be an array")
    observed = []
    blockers = []
    questions = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid Primary finding entry")
        finding_id = entry.get("finding_id")
        if not isinstance(finding_id, str) or not finding_id:
            raise ValueError("finding_id must be a nonempty string")
        observed.append(finding_id)
        kind = entry.get("disposition")
        if kind not in {
            "confirmed_defect",
            "required_test_gap",
            "nonblocking",
            "contract_revision",
            "unresolved",
        }:
            raise ValueError("invalid finding disposition")
        if not isinstance(entry.get("evidence"), str) or not entry["evidence"].strip():
            raise ValueError("each finding needs Primary evidence")
        if kind in {"confirmed_defect", "required_test_gap"}:
            blockers.append(finding_id)
        elif kind in {"contract_revision", "unresolved"}:
            questions.append(finding_id)
    if len(observed) != len(set(observed)) or set(observed) != set(ids):
        raise ValueError("Primary must adjudicate every finding exactly once")
    if questions or resolution != "cleared":
        decision, action = "replan", "primary_contract_or_evidence_resolution"
    elif blockers:
        decision, action = "rework", "primary_prepare_confirmed_rework_packet"
    else:
        decision, action = "accept", "primary_review_by_risk_route"
    return {
        "schema_version": 1,
        "authority": "primary",
        "identity": report["identity"],
        "report_sha256": sha256,
        "reviewer_recommendation": report["decision"],
        "findings": entries,
        "resolution": resolution,
        "evidence": evidence,
        "primary_decision": decision,
        "next_action_required": action,
        "confirmed_rework_finding_ids": blockers if decision == "rework" else [],
        "automatic_coder_rework_authorized": False,
        "automatic_acceptance": False,
    }
