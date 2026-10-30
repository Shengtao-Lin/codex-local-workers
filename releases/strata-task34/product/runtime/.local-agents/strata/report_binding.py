"""Bind only observed current source lines; aggregate errors without fixing claims."""

import copy


class ReportFeedbackError(ValueError):
    def __init__(self, errors):
        super().__init__(
            "Report rejected;correct all listed mechanical errors and resubmit complete report"
        )
        self.details = {
            "report_errors": errors[:32],
            "errors_truncated": len(errors) > 32,
            "acceptance": False,
            "rule": "No content accepted,trimmed or rewritten;unobserved sources are never filled",
        }


def bind_report(host, args, *, role="investigate"):
    errors = []

    def error(field, code, **facts):
        errors.append({"field": field, "code": code, **facts})

    if not isinstance(args, dict):
        raise ReportFeedbackError([{"field": "report", "code": "object_required"}])
    fields = {"status", "summary", "findings", "evidence", "unknowns"}
    if set(args) != fields:
        error("report", "exact_fields_required", required=sorted(fields))
    status, summary = args.get("status"), args.get("summary")
    legal = (
        ["pass_to_primary", "rework", "insufficient_evidence"]
        if role == "review"
        else ["answered", "insufficient_evidence"]
    )
    if not isinstance(status, str) or status not in legal:
        error("status", "legal_status_required", allowed=legal)
    if not isinstance(summary, str) or not 1 <= len(summary) <= 6000:
        error(
            "summary",
            "character_bound",
            minimum=1,
            maximum=6000,
            actual=len(summary) if isinstance(summary, str) else None,
        )
    arrays = {}
    for field in ("findings", "evidence", "unknowns"):
        value = args.get(field)
        if not isinstance(value, list):
            error(field, "array_required")
            arrays[field] = []
        else:
            arrays[field] = value
            if len(value) > 24:
                error(field, "item_bound", maximum=24, actual=len(value))
    for index, unknown in enumerate(arrays["unknowns"][:24]):
        if not isinstance(unknown, str) or not 1 <= len(unknown) <= 2000:
            error(f"unknowns[{index}]", "character_bound", minimum=1, maximum=2000)
    if status == "insufficient_evidence" and not arrays["unknowns"]:
        error("unknowns", "missing_evidence_must_be_explicit")
    if (
        isinstance(status, str)
        and status in {"answered", "pass_to_primary", "rework"}
        and not arrays["evidence"]
    ):
        error("evidence", "observed_evidence_required")
    from investigation_delivery import enabled as delivery_enabled

    if status == "answered" and arrays["findings"] and not delivery_enabled(host.config):
        error("findings", "answered_cannot_contain_defect_findings")

    memory = host.ledger.state.get("evidence_coverage", {})
    hashes, texts, canonical = host.current_hashes(), {}, []
    for index, citation in enumerate(arrays["evidence"][:24]):
        field = f"evidence[{index}]"
        if not isinstance(citation, dict) or set(citation) != {"path", "line"}:
            error(
                field,
                "wire_fields_required",
                required=["path", "line"],
                quote="Host binds quote;do not supply it",
            )
            continue
        path, line = citation["path"], citation["line"]
        if not isinstance(path, str) or path not in host.policy["initial_hashes"]:
            error(field, "unapproved_source")
            continue
        seen = memory.get(path, {})
        if type(line) is not int or line < 1:
            error(field, "positive_integer_line_required")
            continue
        if seen.get("sha256") != hashes[path] or line not in seen.get("lines", []):
            error(field, "line_not_observed_in_current_version")
            continue
        if path not in texts:
            raw, digest = host.editor.read_bytes(path)
            if digest != hashes[path]:
                error(field, "source_version_changed")
                continue
            texts[path] = raw.decode("utf-8-sig").splitlines()
        lines = texts[path]
        if line > len(lines) or not lines[line - 1].strip():
            error(field, "nonempty_observed_source_line_required")
            continue
        canonical.append({"path": path, "line": line, "quote": lines[line - 1].strip()})

    ids = {item["id"] for item in host.packet["required_behavior"]}
    for index, finding in enumerate(arrays["findings"][:24]):
        field = f"findings[{index}]"
        if not isinstance(finding, dict) or set(finding) != {
            "contract_id",
            "severity",
            "description",
            "evidence_index",
        }:
            error(field, "finding_fields_required")
            continue
        if not isinstance(finding["contract_id"], str) or finding["contract_id"] not in ids:
            error(field, "owned_contract_id_required")
        if not isinstance(finding["severity"], str) or finding["severity"] not in {
            "critical",
            "major",
            "info",
        }:
            error(field, "legal_severity_required")
        text, pointer = finding["description"], finding["evidence_index"]
        if not isinstance(text, str) or not 1 <= len(text) <= 3000:
            error(field, "description_bound", maximum=3000)
        if type(pointer) is not int or not 0 <= pointer < len(arrays["evidence"]):
            error(field, "zero_based_evidence_index_required")
    if errors:
        raise ReportFeedbackError(errors)
    result = copy.deepcopy(args)
    result["evidence"] = canonical
    return result
