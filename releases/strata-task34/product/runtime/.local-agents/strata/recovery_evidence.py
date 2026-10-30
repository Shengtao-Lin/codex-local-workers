"""Default-off small-file recovery: reserve evidence for current post-write source."""

from pathlib import Path

from general_memory import observe
from general_state import BudgetExhausted, StateError

FLAG = "experimental_strata_recovery_evidence"
VERSION = "reserved-refresh-v1"
MAX_LINES = 120
MAX_BYTES = 16_000


def selected(config):
    return config.get(FLAG) == VERSION


def validate(config, role, packet=None, root=None):
    value = config.get(FLAG)
    if value is None:
        return
    if (
        value != VERSION
        or role != "implement"
        or config.get("experimental_strata_continuation") != "review-rework-diagnostic-v1"
        or config.get("experimental_strata_edit_profile") != "observed-lines-v1"
        or config.get("strata_version_references") != "observed-v1"
        or config.get("experimental_native_tools_trial")
        or config.get("experimental_strata_capabilities")
    ):
        raise StateError("Reserved refresh requires controlled observed-line implementation")
    if packet is not None:
        scope = packet["scope"]
        if len(scope["modify"]) != 1 or scope["create"]:
            raise StateError("Reserved refresh supports one existing small writable file only")
        bounded((Path(root) / scope["modify"][0]).read_bytes())


def bounded(raw):
    if len(raw) > MAX_BYTES or not 1 <= len(raw.decode("utf-8-sig").splitlines()) <= MAX_LINES:
        raise ValueError("Reserved refresh postimage must stay within120lines/16000bytes")


def active(host):
    return (
        selected(host.config)
        and bool(host.ledger.state.get("controlled_failed_prefix"))
        and bool(host.ledger.state.get("review_rework_start"))
    )


def account(host):
    return host.ledger.state.setdefault("reserved_refresh", {}).setdefault(
        host.packet["run_id"], {"denials": 0, "consecutive_denials": 0, "refreshes": 0}
    )


def admission(host, action, args):
    """Only channel refusal; no read, new credit, protocol charge or terminal PASS."""
    if not active(host):
        return None
    path = args.get("path")
    if not isinstance(path, str):
        raise TypeError("Evidence path required")
    relative, _ = host.editor.resolve(path)
    approved = set(host.policy["initial_hashes"]) | set(host.policy["create"])
    if not any(
        p == relative or (action == "search" and p.startswith(relative + "/")) for p in approved
    ):
        raise StateError("Evidence outside approved exact source manifest")
    budget = host.ledger.current()
    available = budget["limits"]["evidence_actions"] - budget["used"]["evidence_actions"]
    reserved = budget["limits"]["edits"] - budget["used"]["edits"]
    if available > reserved:
        account(host)["consecutive_denials"] = 0
        return None
    state = account(host)
    state["denials"] += 1
    state["consecutive_denials"] += 1
    host.ledger.record(
        "ordinary_evidence_refused", {"available": available, "reserved_for_writes": reserved}
    )
    if state["consecutive_denials"] >= 2:
        raise BudgetExhausted("Repeated read/search after ordinary evidence exhausted;no progress")
    return {
        "status": "evidence_limit_reached",
        "source_delivered": False,
        "ordinary_reads_remaining": 0,
        "postwrite_refreshes_reserved": reserved,
        "available_actions": ["propose", "submit", "blocked"],
        "reason": "Ordinary evidence exhausted;remaining evidence is reserved for host post-write source refresh. Existing edit/check and total request/time limits still apply.",
    }


def before_write(host, output):
    if not active(host):
        return
    if len(output) != 1:
        raise StateError("Reserved refresh transaction supports one writable file")
    for raw in output.values():
        bounded(raw)
    budget = host.ledger.current()
    if budget["used"]["evidence_actions"] >= budget["limits"]["evidence_actions"]:
        raise BudgetExhausted("No current-source refresh opportunity before write")


def refresh(host, paths):
    """One charged source observation per committed small-file edit, even after failed check."""
    if not active(host):
        return None
    host.guard()
    host.assert_bound()
    if len(paths) != 1:
        raise StateError("Unexpected multi-file refresh")
    path = next(iter(paths))
    if path not in host.packet["scope"]["modify"]:
        raise StateError("Refresh cannot expose a nonowned file")
    raw, digest = host.editor.read_bytes(path)
    bounded(raw)
    host.ledger.spend("evidence_actions")
    lines = raw.decode("utf-8-sig").splitlines()
    observe(
        host.ledger.state.setdefault("evidence_coverage", {}),
        path,
        digest,
        range(1, len(lines) + 1),
    )
    if host.context_coverage is not None:
        observe(host.context_coverage, path, digest, range(1, len(lines) + 1))
    observation = {
        "path": path,
        "sha256": digest,
        "start_line": 1,
        "end_line": len(lines),
        "content": "\n".join(f"{i}: {line}" for i, line in enumerate(lines, 1)),
        "version_ref": host.versions.issue(path, digest),
        "purpose": "host_postwrite_current_source",
        "charged_evidence_actions": 1,
    }
    host.observations.append({"observation": observation, "hashes": {path: digest}})
    state = account(host)
    state["refreshes"] += 1
    state["consecutive_denials"] = 0
    host.ledger.record(
        "postwrite_current_source_refreshed", {"path": path, "sha256": digest, "lines": len(lines)}
    )
    return observation


def context(host):
    if not active(host):
        return None
    budget = host.ledger.current()
    reserved = budget["limits"]["edits"] - budget["used"]["edits"]
    return {
        "profile": VERSION,
        "ordinary_evidence_remaining": max(
            0, budget["limits"]["evidence_actions"] - budget["used"]["evidence_actions"] - reserved
        ),
        "postwrite_source_observations_reserved": reserved,
        "refresh_line_limit": MAX_LINES,
        "refresh_byte_limit": MAX_BYTES,
        "rule": "Each effective write/check returns current owned source and a fresh version_ref;charged within the same evidence pool,not a free read or extra request.",
    }
