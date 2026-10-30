"""Mechanical preview of a validated full report, never a semantic summary."""

from pathlib import Path

from general_prepare import sha
from general_state import StateError, read
from strata_artifacts import save


def receipt(root, worker, destination):
    if worker["status"] != "ready_for_primary" or not worker.get("report"):
        raise StateError("Only a completed validated report can have a delivery receipt")
    canonical = (Path(worker["archive"]) / "readonly-report.json").resolve(strict=True)
    if not canonical.is_relative_to(Path(root).resolve() / ".agent/tasks"):
        raise StateError("Report outside task archive")
    full = read(canonical)
    if full["status"] != worker["status"] or full["report"] != worker["report"]:
        raise StateError("Canonical report mismatch")
    summary = full["report"]["summary"]
    marker = "[Mechanical excerpt, NOT a semantic summary. Read full report before acceptance.]\n"
    suffix = "\n[More in complete report.]"
    truncated = len(marker + summary) > 2000
    preview = marker + (
        summary[: 2000 - len(marker) - len(suffix)] + suffix if truncated else summary
    )
    value = {
        "schema_version": 1,
        "full_report": str(canonical),
        "full_report_sha256": sha(canonical),
        "source_hashes": full["source_hashes"],
        "contract_sha256": full["contract_sha256"],
        "report_status": full["report"]["status"],
        "summary_characters": len(summary),
        "preview": preview,
        "preview_truncated": truncated,
        "unknowns_count": len(full["report"]["unknowns"]),
        "evidence_count": len(full["report"]["evidence"]),
        "acceptance": False,
        **({"citation_binding": full["citation_binding"]} if "citation_binding" in full else {}),
        **({"wire_profile": full["wire_profile"]} if "wire_profile" in full else {}),
        "required_review": "Read complete summary,unknowns,findings and source evidence;excerpt may omit critical caveats. Source citations do not prove all semantic claims.",
    }
    save(destination, value)
    return value


def public_output(value):
    """Keep full result immutable; optional stdout omits its duplicate report body."""
    if "delivery" not in value:
        return value
    worker = value["worker"]
    return {
        "task_id": value["task_id"],
        "kind": value["kind"],
        "status": value["status"],
        "acceptance": False,
        "delivery": {k: v for k, v in value["delivery"].items() if k != "source_hashes"},
        "worker": {
            "archive": worker["archive"],
            "ledger": worker["ledger"],
            "reason": worker.get("reason"),
        },
        "review": value["review"],
        "total_seconds": value["total_seconds"],
    }
