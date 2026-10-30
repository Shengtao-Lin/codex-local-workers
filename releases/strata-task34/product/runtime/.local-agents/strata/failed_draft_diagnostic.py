"""Default-off non-accepting review of a settled failed draft; no new authority."""

import copy
from pathlib import Path

from general_prepare import sha
from general_state import StateError, fingerprint, read
from strata_artifacts import save

VERSION = "review-rework-diagnostic-v1"
FLAG = "experimental_strata_failed_draft_diagnostic"
PURPOSE = "failed-draft-v1"


def enabled(config):
    return config.get("experimental_strata_continuation") == VERSION


def validate_profile(config, role):
    value = config.get(FLAG)
    if value is not None and (
        value != PURPOSE
        or role != "review"
        or config.get("experimental_strata_review_delivery") != "observed-line-v1"
        or config.get("experimental_strata_capabilities")
        or config.get("experimental_native_tools_trial")
    ):
        raise StateError("Failed-draft diagnosis requires ordinary readonly Reviewer")


def failed_binding(host):
    """Current completed failed checks, not infrastructure/safety/contract failures."""
    host.assert_bound()
    state = host.ledger.state
    latest = state.get("latest_check")
    if (
        not enabled(host.config)
        or state["status"] not in {"failed", "budget_exhausted"}
        or state["active"]
        or state["pending_model"]
        or state.get("task_followup")
        or len(state["attempts"]) != 1
        or host.ledger.cancelled()
        or not latest
    ):
        raise StateError("Diagnosis requires one settled, safe failed draft")
    if (
        sha(host.repo_root / latest["path"]) != latest["sha256"]
        or latest["inputs"] != host.current_hashes()
    ):
        raise StateError("Failed check stale/unbound")
    check = read(host.repo_root / latest["path"])
    validation = check["validation"]
    focused = validation.get("focused_tests", {})
    junit = focused.get("junit", {})
    # A test/assertion or ordinary configured-check failure is diagnosable;
    # launch errors, timeouts, missing tests and policy conflicts are not.
    configured = validation.get("configured_checks", [])
    if (
        check.get("contract_sha256") != host.contract_digest
        or check.get("inputs") != host.current_hashes()
        or check.get("identity")
        != {
            "task_id": host.packet["task_id"],
            "unit_id": host.packet["unit_id"],
            "run_id": state["attempts"][0],
        }
        or validation.get("status") != "failed"
        or not junit.get("executed", 0)
        or junit.get("errors", 0)
        or focused.get("inputs_unchanged") is not True
        or focused.get("exit_code") not in {0, 1}
        or {c.get("id") for c in configured} != set(host.config["required_check_ids"])
        or any(c.get("exit_code") not in {0, 1} for c in configured)
    ):
        raise StateError("Completed ordinary failed checks required; no infra bypass")
    junit_path = host.repo_root / junit["path"]
    if not junit_path.is_file() or sha(junit_path) != check.get("junit_sha256"):
        raise StateError("Failed check JUnit evidence changed")
    return {
        "inputs": host.current_hashes(),
        "check": copy.deepcopy(latest),
        "contract_sha256": host.contract_digest,
        "identity": {"task_id": host.packet["task_id"], "attempt": state["attempts"][0]},
    }


def snapshot(root, task_id, destination):
    """Reuse formal snapshot transport, but retain failed gate and forbid PASS."""
    from general_host import GeneralHost
    from task_workflow import home

    host = GeneralHost(root, task_id, "diagnostic-gate")
    host.write_lock.acquire()
    try:
        binding = failed_binding(host)
        if (home(root, task_id) / "cancel.json").exists():
            raise StateError("Cancelled workflow")
        destination = Path(destination)
        if destination.exists():
            raise StateError("Diagnostic snapshot exists; no reroll")
        sources = host.policy["initial_hashes"].keys() | set(host.policy["create"])
        hashes, preimages = {}, {}
        for relative in sorted(sources):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write((host.repo_root / relative).read_bytes())
            hashes[relative] = sha(target)
            if relative in host.material["packet"]["scope"]["modify"]:
                preimages[relative] = (host.ledger.path / "preimages" / relative).read_text(
                    encoding="utf-8-sig"
                )
        evidence = "workflow-evidence/checks.json"
        if evidence in sources:
            raise StateError("Reserved diagnostic evidence collision")
        receipt = {
            "source_hashes": hashes,
            "commands": read(host.repo_root / binding["check"]["path"])["validation"],
            "failed_draft_binding": binding,
            "purpose": PURPOSE,
            "canonical_path": binding["check"]["path"],
            "canonical_sha256": binding["check"]["sha256"],
        }
        save(destination / evidence, receipt)
        packet = host.material["packet"]
        request = {
            "task_id": "diagnose-" + fingerprint(binding)[:20],
            "mode": "review",
            "read": [*sorted(hashes), evidence],
            "risk": packet["risk"],
            "goal": "Diagnose the current failed draft against the original contract and actual failed checks. "
            "Return only concrete source-backed rework or insufficient_evidence. "
            "This diagnosis cannot pass or accept work.\n" + packet["goal"],
            "required_behavior": [
                *packet["required_behavior"],
                *[
                    {"id": "accept-" + c["id"], "text": c["text"]}
                    for c in packet["acceptance_criteria"]
                ],
            ],
            "preimages": preimages,
            "checks_path": evidence,
        }
        config = copy.deepcopy(host.config)
        for key in ("experimental_strata_continuation", "experimental_strata_unit_kind"):
            config.pop(key, None)
        config.pop("experimental_strata_recovery_evidence", None)
        config.update({"experimental_strata_readonly": True, FLAG: PURPOSE})
        return request, config, binding
    finally:
        host.close()


def dispatch(root, task_id, *, mode="live", actions=None):
    from general_host import GeneralHost
    from task_workflow import home, prepare_readonly, readonly_execute

    location = home(root, task_id) / "diagnostic"
    save(location / "dispatch.json", {"acceptance": False, "purpose": PURPOSE})
    destination = Path(root) / ".agent/reviews" / ("diagnostic-" + fingerprint(task_id)[:16])
    request, config, binding = snapshot(root, task_id, destination)
    save(location / "binding.json", {"binding": binding, "project": str(destination)})
    prepare_readonly(destination, request, config, apply=True)
    result = readonly_execute(
        destination, request["task_id"], "diagnostic", mode=mode, actions=actions
    )
    host = GeneralHost(root, task_id, "diagnostic-return-gate")
    host.write_lock.acquire()
    try:
        if failed_binding(host) != binding or (home(root, task_id) / "cancel.json").exists():
            raise StateError("Failed draft changed during diagnosis")
    finally:
        host.close()
    value = {"purpose": PURPOSE, "binding": binding, "review": result, "acceptance": False}
    save(location / "result.json", value)
    return value


def validate_feedback(host, feedback, previous):
    """Return a canonical review object after exact task/check/report binding."""
    from task_workflow import home

    binding = failed_binding(host)
    if (
        previous.get("status") not in {"failed", "budget_exhausted"}
        or feedback["previous_attempt"] != binding["identity"]["attempt"]
    ):
        raise StateError("Diagnostic return prior failed attempt mismatch")
    pointer = feedback.get("diagnostic")
    if feedback["kind"] == "failed_check_repair":
        # Only preregistered controlled comparator; no semantic feedback, no
        # production permission to bypass canonical finding disposition.
        if (
            not host.ledger.state.get("controlled_failed_prefix")
            or pointer is not None
            or feedback.get("defect") is not None
            or feedback.get("review_disposition") is not None
        ):
            raise StateError("Plain repair is controlled-comparator only")
        return None
    expected = home(host.repo_root, host.packet["task_id"]) / "diagnostic/result.json"
    if (
        not isinstance(pointer, dict)
        or set(pointer) != {"path", "sha256"}
        or Path(pointer["path"]) != expected.relative_to(host.repo_root)
        or pointer["sha256"] != sha(expected)
    ):
        raise StateError("Canonical diagnostic pointer mismatch")
    diagnostic = read(expected)
    if diagnostic.get("purpose") != PURPOSE or diagnostic.get("binding") != binding:
        raise StateError("Diagnostic task/check/current-source mismatch")
    review = diagnostic["review"]
    canonical = read(Path(review["archive"]) / "readonly-report.json")
    if canonical.get("purpose") != PURPOSE or canonical.get("acceptance") is not False:
        raise StateError("Non-accepting diagnostic report required")
    return review
