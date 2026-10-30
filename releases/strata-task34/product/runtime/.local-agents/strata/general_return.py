"""One explicit Primary defect return against the unchanged approved contract."""

from general_state import StateError, fingerprint


def record_primary_return(host, feedback, *, record=True):
    from failed_draft_diagnostic import enabled as diagnostic_enabled, failed_binding

    diagnostic = diagnostic_enabled(host.config)
    state = host.ledger.state
    if (
        not host.resume_requested
        or state["status"]
        not in ({"failed", "budget_exhausted"} if diagnostic else {"ready_for_primary"})
        or state.get("primary_return")
        or state["active"]
        or state["pending_model"]
    ):
        raise StateError("Primary return requires one settled ready draft and explicit resume")
    if not isinstance(feedback, dict) or set(feedback) != {"check_sha256", "assisted", "findings"}:
        raise StateError("Primary return fields: check_sha256, assisted, findings")
    if type(feedback["assisted"]) is not bool:
        raise StateError("Primary must explicitly classify semantic assistance")
    latest = state.get("latest_check") or {}
    if feedback["check_sha256"] != latest.get("sha256"):
        raise StateError("Primary return is not bound to the current check")
    if diagnostic:
        failed_binding(host)
    elif host.submission_state()["status"] != "submission_available":
        raise StateError("Returned draft is no longer mechanically current")
    owned = {b["id"] for b in host.packet["required_behavior"]}
    findings = feedback["findings"]
    if not isinstance(findings, list) or not 1 <= len(findings) <= 8:
        raise StateError("Use1..8 confirmed in-contract defects, not a new task")
    ids = set()
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {"id", "contract_id", "text", "source"}:
            raise StateError("Finding fields: id, contract_id, text, source")
        if (
            not isinstance(finding["id"], str)
            or not finding["id"]
            or finding["id"] in ids
            or not isinstance(finding["contract_id"], str)
            or finding["contract_id"] not in owned
            or not isinstance(finding["text"], str)
            or not 1 <= len(finding["text"]) <= 2000
        ):
            raise StateError("Confirmed finding needs unique id and existing contract id")
        ids.add(finding["id"])
        source = finding["source"]
        if not isinstance(source, dict) or set(source) != {"path", "sha256", "line", "quote"}:
            raise StateError("Current source citation required")
        path, line = source["path"], source["line"]
        readable = host.policy["initial_hashes"] | dict.fromkeys(host.policy["create"])
        if (
            not isinstance(path, str)
            or path not in readable
            or not isinstance(source["sha256"], str)
            or source["sha256"] != host.current_hashes().get(path)
        ):
            raise StateError("Primary source citation outside current approved evidence")
        raw, _ = host.editor.read_bytes(path)
        lines = raw.decode("utf-8-sig").splitlines()
        if (
            type(line) is not int
            or not 1 <= line <= len(lines)
            or source["quote"] != lines[line - 1]
        ):
            raise StateError("Primary finding quote does not match current source")
    value = {
        **feedback,
        "source_inputs": host.current_hashes(),
        "edit_count": state["used"]["edits"],
        "acceptance": False,
    }
    if not record:
        return value
    # Host holds the existing project write lock. The record does not alter
    # packet, scope, checks or credits, and is never model-authored memory.
    state["primary_return"] = value
    host.ledger.record("primary_confirmed_defect_return", {"sha256": fingerprint(value)})
