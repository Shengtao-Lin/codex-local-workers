"""Task routing and fresh review transport; host gates remain authoritative."""

import copy
import importlib.util
import time
from pathlib import Path

from general_cli import execute as implement
from general_host import GeneralHost
from general_prepare import RUNTIME, load_contract, sha
from general_prepare import prepare as prepare_implementation
from general_state import StateError, TaskLedger, fingerprint, identifier, read
from readonly_host import prepare as prepare_readonly
from readonly_host import validate_review_delivery
from report_delivery import receipt
from strata_artifacts import save
from task_continuation import FLAG, enabled, feedback_shape, validate_config
from task_contract import compile_contract


def readonly_execute(root, task_id, attempt_id, *, mode="live", actions=None, **kwargs):
    spec = importlib.util.spec_from_file_location(
        "task_readonly_entry", RUNTIME / "strata-readonly.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute(root, task_id, attempt_id, mode=mode, actions=actions, **kwargs)


def home(root, task_id):
    return Path(root) / ".agent/tasks" / identifier(task_id) / "workflow"


def prepare(root, contract, config, *, apply=False):
    root = Path(root).resolve(strict=True)
    kind, payload, config = compile_contract(contract, config)
    validate_config(config, kind)
    if config.get("experimental_strata_unit_kind") is not None and kind != "implement":
        raise StateError("Test-repair unit kind is implementation-only")
    validate_review_delivery(config, kind)
    from investigation_delivery import validate as validate_delivery

    validate_delivery(config, kind)
    binding = config.get("experimental_strata_report_binding")
    if binding is not None and (
        binding != "observed-line-v1"
        or kind != "investigate"
        or config.get("experimental_strata_report_receipt") is not True
        or config.get("experimental_strata_capabilities") is True
    ):
        raise StateError(
            "Observed-line binding requires explicit ordinary readonly receipt profile"
        )
    if config.get("experimental_strata_report_receipt") is True and (
        kind != "investigate" or config.get("experimental_strata_capabilities") is True
    ):
        raise StateError("Report receipt trial requires ordinary readonly investigation")
    location = home(root, contract["task_id"])
    if location.exists():
        raise StateError("Workflow identity already exists")
    prepare_host = prepare_readonly if kind == "investigate" else prepare_implementation
    result = prepare_host(root, payload, config, apply=apply)
    if apply:
        _, material = load_contract(root, contract["task_id"])
        value = {
            "contract": contract,
            "kind": kind,
            "material_sha256": fingerprint(material),
            "review_required": kind == "implement",
            "acceptance": False,
        }
        if config.get("experimental_strata_unit_kind"):
            value["unit_kind"] = config["experimental_strata_unit_kind"]
        save(location / "contract.json", {"value": value, "sha256": fingerprint(value)})
    return {**result, "kind": kind, "review_required": kind == "implement", "acceptance": False}


def load(root, task_id):
    value = read(home(root, task_id) / "contract.json")
    ledger, material = load_contract(root, task_id)
    meta = value["value"]
    if fingerprint(meta) != value["sha256"] or fingerprint(material) != meta["material_sha256"]:
        raise StateError("Workflow contract/material drift")
    kind, _, _ = compile_contract(meta["contract"], material["config"])
    if kind != meta["kind"] or meta["review_required"] != (kind == "implement"):
        raise StateError("Workflow route changed")
    if meta.get("unit_kind") != material["config"].get("experimental_strata_unit_kind"):
        raise StateError("Workflow unit kind changed")
    return meta, ledger, material


def review_snapshot(root, task_id, destination):
    """Copy exactly approved current sources, actual preimages and check evidence."""
    host = GeneralHost(root, task_id, "review-gate")
    host.write_lock.acquire()
    try:
        host.assert_bound()
        if host.ledger.state["status"] != "ready_for_primary" or host.ledger.state["active"]:
            raise StateError("Worker must finish before fresh review")
        if host.submission_state()["status"] != "submission_available":
            raise StateError("No current full-check handoff")
        if destination.exists():
            raise StateError("Fresh review snapshot already exists; no reroll")
        sources = host.policy["initial_hashes"].keys() | set(host.policy["create"])
        hashes = {}
        preimages = {}
        destination.mkdir(parents=True)
        for relative in sorted(sources):
            source = Path(root) / relative
            if not source.is_file():
                raise StateError("Approved review input missing: " + relative)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(source.read_bytes())
            hashes[relative] = sha(target)
            if relative in host.material["packet"]["scope"]["modify"]:
                preimages[relative] = (host.ledger.path / "preimages" / relative).read_text(
                    encoding="utf-8-sig"
                )
            elif relative in host.policy["create"]:
                preimages[relative] = ""
        preimages = {
            p: old
            for p, old in preimages.items()
            if old != (destination / p).read_text(encoding="utf-8-sig")
        }
        if not preimages:
            raise StateError("No actual cumulative change")
        latest = host.ledger.state["latest_check"]
        check = read(Path(root) / latest["path"])
        receipt = {
            "source_hashes": hashes,
            "commands": check["validation"],
            "canonical_path": latest["path"],
            "canonical_sha256": latest["sha256"],
            "contract_sha256": host.contract_digest,
            "canonical_task": host.material["packet"],
            "limits": "Actual host checks;fresh Reviewer does not execute;Primary independently accepts",
        }
        evidence_path = "workflow-evidence/checks.json"
        if evidence_path in sources:
            raise StateError("Reserved review evidence path collision")
        save(destination / evidence_path, receipt)
        packet = host.material["packet"]
        request = {
            "task_id": "review-" + fingerprint({"task": task_id, "check": latest})[:20],
            "mode": "review",
            "read": [*sorted(hashes), evidence_path],
            "goal": "Independently review actual cumulative changes and full task contract. "
            "Report concrete defects or pass_to_primary;do not infer acceptance from green checks.\n"
            + packet["goal"],
            "required_behavior": packet["required_behavior"],
            "risk": packet["risk"],
            "preimages": preimages,
            "checks_path": evidence_path,
        }
        # Preserve all implementation acceptance obligations in independent review.
        request["required_behavior"] = [
            *request["required_behavior"],
            *[
                {"id": "accept-" + c["id"], "text": c["text"]}
                for c in packet["acceptance_criteria"]
            ],
        ]
        config = copy.deepcopy(host.config)
        for key in (
            "experimental_strata_capabilities",
            "experimental_native_tools_trial",
            "strata_capability_child",
            FLAG,
            "experimental_strata_unit_kind",
            "experimental_strata_failed_draft_diagnostic",
            "experimental_strata_recovery_evidence",
        ):
            config.pop(key, None)
        config["experimental_strata_readonly"] = True
        host.assert_bound()
        return (
            request,
            config,
            {
                "inputs": host.current_hashes(),
                "check": latest,
                "contract_sha256": host.contract_digest,
            },
        )
    finally:
        host.close()


def assert_current(root, task_id, binding):
    host = GeneralHost(root, task_id, "review-return-gate")
    host.write_lock.acquire()
    try:
        host.assert_bound()
        if (
            host.current_hashes() != binding["inputs"]
            or host.contract_digest != binding["contract_sha256"]
        ):
            raise StateError("Original inputs changed while reviewing")
        if (
            host.ledger.state.get("latest_check") != binding["check"]
            or host.submission_state()["status"] != "submission_available"
        ):
            raise StateError("Original check changed while reviewing")
    finally:
        host.close()


def run(
    root,
    task_id,
    attempt_id,
    *,
    mode="live",
    actions=None,
    review_actions=None,
    _resume=False,
    _feedback=None,
):
    root = Path(root).resolve(strict=True)
    meta, ledger, material = load(root, task_id)
    if not _resume and (ledger.state["status"] != "prepared" or ledger.state["attempts"]):
        raise StateError(
            "Task already dispatched;use original host recovery, never a fresh budget/review draw"
        )
    if (home(root, task_id) / "cancel.json").exists():
        raise StateError("Workflow cancelled before dispatch")
    attempt = home(root, task_id) / "runs" / identifier(attempt_id)
    save(
        attempt / "dispatch.json",
        {"started": time.time(), "kind": meta["kind"], "acceptance": False},
    )
    started = time.monotonic()
    execute = readonly_execute if meta["kind"] == "investigate" else implement
    kwargs = {}
    if _resume:
        kwargs = {
            "resume": True,
            "feedback" if meta["kind"] == "investigate" else "continuation_feedback": _feedback,
        }
    worker = execute(root, task_id, attempt_id, mode=mode, actions=actions, **kwargs)
    worker_seconds = round(time.monotonic() - started, 3)
    save(attempt / "worker.json", worker)
    outcome = {
        "task_id": task_id,
        "status": worker["status"],
        "kind": meta["kind"],
        "acceptance": False,
        "worker": worker,
        "worker_seconds": worker_seconds,
        "review": {"status": "NOT_RUN"},
        "primary_required": True,
    }
    if meta.get("unit_kind"):
        outcome["unit_kind"] = meta["unit_kind"]
    if (home(root, task_id) / "cancel.json").exists():
        outcome["status"] = "cancelled"
        save(attempt / "result.json", outcome)
        return outcome
    if (
        meta["kind"] == "investigate"
        and (worker.get("report") or {}).get("status") == "insufficient_evidence"
    ):
        outcome["status"] = "insufficient_evidence"
    if worker["status"] == "ready_for_primary" and meta["review_required"]:
        # Atomic create-only claim survives interruption; never rerun identical review.
        save(attempt / "review-dispatch.json", {"started": time.time(), "acceptance": False})
        try:
            reused = None
            if _resume:
                prior = home(root, task_id) / "runs" / _feedback["previous_attempt"]
                binding_path = prior / "review-binding.json"
                if binding_path.exists():
                    previous_binding = read(binding_path)["binding"]
                    try:
                        assert_current(root, task_id, previous_binding)
                    except StateError:
                        pass
                    else:
                        reused = read(prior / "result.json")["review"]
                        save(
                            attempt / "review-reuse.json",
                            {
                                "prior_result": str(prior / "result.json"),
                                "sha256": sha(prior / "result.json"),
                                "reason": "Identical source,contract and current-check inputs;no new review draw",
                            },
                        )
                        save(
                            attempt / "review-binding.json",
                            {"binding": previous_binding, "reused": True},
                        )
            if reused is not None:
                outcome["review"] = reused
                judgment = (reused.get("report") or {}).get("status")
                outcome["status"] = (
                    "ready_for_primary"
                    if reused["status"] == "ready_for_primary" and judgment == "pass_to_primary"
                    else "rework"
                    if judgment == "rework"
                    else "review_incomplete"
                )
                outcome["review_reused"] = True
                outcome["total_seconds"] = round(time.monotonic() - started, 3)
                save(attempt / "result.json", outcome)
                return outcome
            destination = (
                root / ".agent/reviews" / fingerprint({"task": task_id, "attempt": attempt_id})[:16]
            )
            request, config, binding = review_snapshot(root, task_id, destination)
            save(attempt / "review-binding.json", {"binding": binding, "project": str(destination)})
            prepare_readonly(destination, request, config, apply=True)
            if (home(root, task_id) / "cancel.json").exists():
                raise StateError("Workflow cancelled before review")
            start_review = time.monotonic()
            review = readonly_execute(
                destination, request["task_id"], "fresh", mode=mode, actions=review_actions
            )
            outcome["review_seconds"] = round(time.monotonic() - start_review, 3)
            save(attempt / "review.json", review)
            outcome["review"] = review
            assert_current(root, task_id, binding)
            if (home(root, task_id) / "cancel.json").exists():
                raise StateError("Workflow cancelled during review")
            judgment = (review.get("report") or {}).get("status")
            outcome["status"] = (
                "ready_for_primary"
                if review["status"] == "ready_for_primary" and judgment == "pass_to_primary"
                else "rework"
                if review["status"] == "ready_for_primary" and judgment == "rework"
                else "review_incomplete"
            )
        except (ValueError, OSError) as exc:
            outcome.update(status="review_incomplete", reason=str(exc))
    outcome["total_seconds"] = round(time.monotonic() - started, 3)
    if (
        meta["kind"] == "investigate"
        and outcome["status"] == "ready_for_primary"
        and material["config"].get("experimental_strata_report_receipt") is True
    ):
        outcome["delivery"] = receipt(root, worker, attempt / "delivery.json")
    save(attempt / "result.json", outcome)
    return outcome


def status(root, task_id):
    meta, ledger, material = load(root, task_id)
    if meta["kind"] == "investigate":
        from investigation_delivery import repair_enabled
        from readonly_host import ReadonlyLedger

        ledger = ReadonlyLedger(
            root, task_id, "investigate", report_repair=repair_enabled(material["config"])
        )
    attempts = ledger.state["attempts"]
    latest = home(root, task_id) / "runs" / attempts[-1] / "result.json" if attempts else None
    return {
        "kind": meta["kind"],
        "worker_ledger": ledger.current(),
        "result": read(latest) if latest and latest.is_file() else None,
        "acceptance": False,
        "note": "Recorded outcome;current sources/checks require revalidation at Primary acceptance",
    }


def resume(root, task_id, attempt_id, feedback, *, mode="live", actions=None, review_actions=None):
    """Preflight a single unchanged-contract follow-up before dispatch/provider work."""
    meta, _, material = load(root, task_id)
    if not enabled(material["config"]):
        raise StateError("Explicit continuation task opt-in required")
    if (home(root, task_id) / "cancel.json").exists():
        raise StateError("Cancelled workflow cannot automatically resume")
    if meta["kind"] == "investigate":
        from readonly_host import ReadonlyHost

        host = ReadonlyHost(root, task_id, attempt_id, resume=True)
    else:
        host = GeneralHost(root, task_id, attempt_id, resume=True)
    host.write_lock.acquire()
    try:
        host.assert_bound()
        host.ledger.check_begin(attempt_id, resume=True)
        feedback_shape(host, feedback)
        if host.ledger.state.get("budget_profile") and feedback["kind"] == "confirmed_defect":
            from general_return import record_primary_return

            record_primary_return(host, feedback["defect"], record=False)
    finally:
        host.close()
    return run(
        root,
        task_id,
        attempt_id,
        mode=mode,
        actions=actions,
        review_actions=review_actions,
        _resume=True,
        _feedback=feedback,
    )


def cancel(root, task_id):
    load(root, task_id)
    marker = home(root, task_id) / "cancel.json"
    if not marker.exists():
        save(marker, {"task_id": task_id, "cancelled_at": time.time()})
    worker = TaskLedger(root, task_id)
    if worker.state["active"]:
        worker.cancel()
    for item in (home(root, task_id) / "runs").glob("*/review-binding.json"):
        info = read(item)
        target = Path(info["project"])
        for contract in (target / ".agent/tasks").glob("*/general/contract.json"):
            ledger = TaskLedger(target, contract.parent.parent.name)
            if ledger.state["active"]:
                ledger.cancel()
    return {"status": "cancel_requested", "acceptance": False}
