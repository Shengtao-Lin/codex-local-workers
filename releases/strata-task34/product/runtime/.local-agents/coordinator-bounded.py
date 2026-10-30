"""Explicit Primary-side bridge for bounded-v1 evidence; no dispatch or acceptance."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load(filename, name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CONTRACT = _load("coordinator-contract.py", "bounded_bridge_contract")
GATE = _load("local-unit.py", "bounded_bridge_handoff")
DISPOSITION = _load("review-disposition.py", "bounded_bridge_disposition")
PROFILE = "bounded-v1"
FAMILY = "local-single-function-transform"


def _object(root, relative):
    path = GATE.HOST.bounded(root, relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Bridge evidence must be an object: " + str(relative))
    return path, value


def _opt_in(profile):
    if profile != PROFILE:
        raise ValueError("Explicit bounded-v1 bridge profile required")


def eligible_packet(plan, packet, config, catalog, *, bridge_profile=None):
    """Caller supplies trusted classification/catalog, never model family claims."""
    _opt_in(bridge_profile)
    normalized = CONTRACT.validate_unit_packet(plan, packet)
    if (
        config.get("bounded_execution_profile") != PROFILE
        or config.get("experimental_consolidated_harness") is not True
        or config.get("host_proposal_enabled") is not True
        or config.get("coordinator_enabled") is not False
        or config.get("single_model_residency") is not True
    ):
        raise ValueError(
            "Bounded unit opt-in/single residency required; unit Coordinator remains disabled"
        )
    spec = config.get("coder_single_function")
    if not isinstance(spec, dict) or not spec.get("symbol"):
        raise ValueError("One bound existing function required")
    scope = normalized["scope"]
    if scope["modify"] != [spec.get("path")] or scope["create"]:
        raise ValueError("Qualified route requires one existing function file")
    if normalized["required_order"] or normalized["forbidden_orderings"]:
        raise ValueError("Ordering-sensitive task family not qualified by this bridge")
    if not isinstance(catalog, dict):
        raise ValueError("Trusted Primary capability catalog required")
    for behavior in normalized["required_behavior"]:
        entry = catalog.get(behavior["id"])
        if (
            not isinstance(entry, dict)
            or entry.get("family") != FAMILY
            or entry.get("path") != spec["path"]
            or entry.get("symbol") != spec["symbol"]
            or not isinstance(entry.get("qualification_evidence"), str)
            or not entry["qualification_evidence"].strip()
            or behavior.get("implementation_ref")
            != {"path": spec["path"], "symbol": spec["symbol"]}
        ):
            raise ValueError(
                "Missing qualified Primary route or exact contract implementation binding"
            )
    return normalized


def verify_accepted_unit(plan, root, unit_id, ref, config, catalog, *, bridge_profile=None):
    """Revalidate current full host facts plus exact Reviewer and Primary disposition.

    Source snapshots must still match *all* original validation inputs. This first
    bridge deliberately does not infer legitimate downstream edits or roll old
    validation forward. Use a new immutable snapshot/receipt or stop on drift.
    """
    _opt_in(bridge_profile)
    root = Path(root).resolve()
    task = CONTRACT.identifier(ref.get("task_id"), "archive.task_id")
    run = CONTRACT.identifier(ref.get("run_id"), "archive.run_id")
    base = f".agent/tasks/{task}/runs/{run}"
    _, packet = _object(root, base + "/packet.json")
    eligible_packet(plan, packet, config, catalog, bridge_profile=bridge_profile)
    _, handoff = _object(root, base + "/handoff.json")
    expected = {"task_id": task, "unit_id": unit_id, "run_id": run}
    if (
        packet.get("unit_id") != unit_id
        or packet.get("task_id") != task
        or packet.get("run_id") != run
        or handoff.get("identity", {}).get("feature_id") != plan["feature_id"]
        or handoff.get("identity", {}).get("plan_revision") != plan["plan_revision"]
        or handoff.get("status") != GATE.HOST.PENDING
        or handoff.get("execution_protocol") != GATE.HOST.PROTOCOL
    ):
        raise ValueError("Bounded archive identity/protocol differs from approved plan")
    if GATE.verify_handoff(root, handoff, config=config) != expected:
        raise ValueError("Bounded archive verified a different unit")
    actual = handoff.get("consolidated_harness", {}).get("actual", {})
    if (
        type(actual.get("model_requests")) is not int
        or actual["model_requests"] < 1
        or actual.get("scripted_requests") != 0
        or type(actual.get("edits")) is not int
        or actual["edits"] < 1
        or type(actual.get("post_edit_checks")) is not int
        or actual["post_edit_checks"] < actual["edits"]
    ):
        raise ValueError("Live Coder provenance and checks for every effective edit required")
    primary_path, primary = _object(root, base + "/review.json")
    if (
        any(primary.get(k) != v for k, v in expected.items())
        or primary.get("decision") != "accept"
        or primary.get("worker_status") != GATE.HOST.PENDING
    ):
        raise ValueError("Matching Primary acceptance required")
    review_id = CONTRACT.identifier(primary.get("local_review_id"), "review_id")
    review_base = f".agent/tasks/{task}/reviews/{review_id}"
    review_path, report = _object(root, review_base + "/handoff.json")
    _, completed = _object(root, review_base + "/completed.json")
    if (
        report.get("identity") != {**expected, "review_id": review_id}
        or report.get("decision") != "pass_to_primary"
        or completed.get("decision") != "pass_to_primary"
    ):
        raise ValueError("Exact completed fresh Reviewer pass required")
    facts = report.get("runtime_facts", {})
    hashes = facts.get("observed_read_hashes")
    required_reads = {
        config["coder_single_function"]["path"],
        *(test.split("::", 1)[0] for test in packet["focused_tests"]),
    }
    if (
        facts.get("read_only") is not True
        or facts.get("inputs_unchanged") is not True
        or not isinstance(hashes, dict)
        or not hashes
        or not required_reads <= set(hashes)
        or type(report.get("reviewer_model_calls")) is not int
        or report["reviewer_model_calls"] < 1
        or not set(packet["owned_contract_ids"]) <= set(report.get("verified_contract_ids", []))
    ):
        raise ValueError("Reviewer observed source evidence required")
    for relative, expected_hash in hashes.items():
        if GATE.HOST.digest(GATE.HOST.bounded(root, relative)) != expected_hash:
            raise ValueError("Reviewer observed source changed: " + relative)
    disposition = primary.get("review_disposition")
    if not isinstance(disposition, dict):
        raise ValueError("Canonical report-bound Primary disposition required")
    adjudicated = DISPOSITION.adjudicate(report, GATE.HOST.digest(review_path), disposition)
    if adjudicated != disposition or adjudicated["primary_decision"] != "accept":
        raise ValueError("Primary disposition does not clear exact Reviewer evidence")
    return {
        "unit_id": unit_id,
        "identity": expected,
        "protocol": GATE.HOST.PROTOCOL,
        "worker_status": GATE.HOST.PENDING,
        "primary_sha256": GATE.HOST.digest(primary_path),
        "reviewer_sha256": GATE.HOST.digest(review_path),
        "host_manifest_sha256": GATE.HOST.digest(root / base / "host-validation-facts.json"),
        "dispatch_allowed": False,
        "automatic_acceptance": False,
    }


def dependency_readiness(
    plan,
    root,
    packet,
    config,
    catalog,
    accepted_refs,
    configs,
    *,
    bridge_profile=None,
    dependency_roots=None,
    transfer_paths=None,
    evidence_root=None,
):
    """Read-only pre-dispatch gate, not a Coordinator decision or execution API."""
    normalized = eligible_packet(plan, packet, config, catalog, bridge_profile=bridge_profile)
    units = {u["unit_id"]: u for u in plan["units"]}
    if normalized["unit_id"] in accepted_refs:
        raise ValueError("Already accepted unit cannot be dispatched again")
    receipts = {}

    def require(unit_id):
        if unit_id in receipts:
            return
        if unit_id not in accepted_refs or unit_id not in configs:
            raise ValueError("Dependency lacks current Primary-accepted evidence: " + unit_id)
        for parent in units[unit_id]["dependencies"]:
            require(parent)
        source_root = Path((dependency_roots or {}).get(unit_id, root)).resolve()
        consumer_root = Path(root).resolve()
        if source_root != consumer_root:
            if evidence_root is None:
                raise ValueError("Cross-snapshot evidence requires explicit trusted evidence root")
            boundary = Path(evidence_root).resolve()
            if not source_root.is_relative_to(boundary) or not consumer_root.is_relative_to(
                boundary
            ):
                raise ValueError("Dependency snapshot escapes trusted evidence root")
        receipts[unit_id] = verify_accepted_unit(
            plan,
            source_root,
            unit_id,
            accepted_refs[unit_id],
            configs[unit_id],
            catalog,
            bridge_profile=bridge_profile,
        )
        if source_root != consumer_root:
            transfer = (transfer_paths or {}).get(unit_id)
            spec = configs[unit_id]["coder_single_function"]
            if not isinstance(transfer, dict) or set(transfer) != {"source", "destination"}:
                raise ValueError("Explicit immutable dependency transfer required")
            target = transfer["destination"]
            scope = normalized["scope"]
            if (
                transfer["source"] != spec["path"]
                or target not in scope["readonly"]
                or target in scope["modify"] + scope["create"]
                or not any(CONTRACT.path_inside(target, p) for p in scope["read"])
                or any(CONTRACT.path_inside(target, p) for p in scope["forbidden"])
            ):
                raise ValueError("Transferred dependency exceeds approved read-only scope")
            producer = GATE.HOST.bounded(source_root, transfer["source"])
            consumer = GATE.HOST.bounded(consumer_root, target)
            sha = GATE.HOST.digest(producer)
            if GATE.HOST.digest(consumer) != sha:
                raise ValueError("Transferred dependency differs from accepted producer")
            receipts[unit_id]["transfer"] = {
                **transfer,
                "sha256": sha,
                "source_root": str(source_root),
            }

    for unit_id in normalized["dependencies"]:
        require(unit_id)
    return {
        "unit_id": normalized["unit_id"],
        "dependencies_verified": receipts,
        "eligible_for_primary_dispatch": True,
        "dispatch_allowed": False,
        "automatic_acceptance": False,
    }
