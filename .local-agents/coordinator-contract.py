"""Offline v2.1 Phase 1 feature-plan checks; never dispatches workers."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid
from pathlib import Path
from pathlib import PurePosixPath

RISK = {"small": 0, "medium": 1, "high": 2}
IDENTIFIER = re.compile(r"[a-z][a-z0-9-]*\Z")
DECISIONS = {"CONTINUE", "REWORK_LOCAL", "ESCALATE_PRIMARY", "FEATURE_READY"}


def authority_fingerprint(plan: dict) -> str:
    """Hash immutable Primary authority, excluding mutable display status."""
    frozen = copy.deepcopy(plan)
    for unit in frozen.get("units", []):
        unit.pop("status", None)
    payload = json.dumps(frozen, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase hyphenated identifier")
    return value


def risk(value: object, field: str) -> str:
    if not isinstance(value, str) or value not in RISK:
        raise ValueError(f"{field} must be small, medium, or high")
    return value


def relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError(f"{field} must be a repository-relative slash path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or any(part in {".", ".."} for part in value.split("/"))
    ):
        raise ValueError(f"{field} must be a normalized repository-relative path")
    return value


def path_inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def scope_authority(value: object, field: str) -> dict[str, list[str]]:
    if not isinstance(value, dict) or set(value) != {
        "read_roots",
        "modify",
        "create",
        "readonly",
        "forbidden",
    }:
        raise ValueError(f"{field} needs read_roots, modify, create, readonly, forbidden")
    result: dict[str, list[str]] = {}
    for key, paths in value.items():
        if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
            raise ValueError(f"{field}.{key} must be a path array")
        normalized = [relative_path(path, f"{field}.{key}") for path in paths]
        if len(set(normalized)) != len(normalized):
            raise ValueError(f"{field}.{key} contains duplicate paths")
        result[key] = normalized
    if not result["read_roots"]:
        raise ValueError(f"{field}.read_roots cannot be empty")
    for key in ("modify", "create", "readonly"):
        for path in result[key]:
            if not any(path_inside(path, root) for root in result["read_roots"]):
                raise ValueError(f"{field}.{key} is outside read_roots: {path}")
    if set(result["modify"]) & set(result["create"]):
        raise ValueError(f"{field} cannot both modify and create one path")
    for path in result["modify"] + result["create"]:
        if any(path_inside(path, root) or path_inside(root, path) for root in result["forbidden"]):
            raise ValueError(f"{field} writes a forbidden path: {path}")
        if any(path_inside(path, root) or path_inside(root, path) for root in result["readonly"]):
            raise ValueError(f"{field} writes a protected path: {path}")
    return result


def packet_contract(value: object, field: str, authority: dict[str, list[str]]) -> dict:
    keys = {
        "acceptance_criteria",
        "acceptance_scenarios",
        "required_order",
        "forbidden_orderings",
        "validation_profile",
        "required_focused_tests",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{field} must declare all Primary packet obligations")
    for key in ("acceptance_criteria", "acceptance_scenarios"):
        items = value[key]
        if not isinstance(items, list) or not items:
            raise ValueError(f"{field}.{key} must be a non-empty array")
        ids: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{field}.{key} entries must be objects")
            item_id = identifier(item.get("id"), f"{field}.{key}.id")
            if item_id in ids or not isinstance(item.get("text"), str) or not item["text"].strip():
                raise ValueError(f"{field}.{key} has duplicate IDs or empty text")
            ids.add(item_id)
            if key == "acceptance_scenarios" and (
                not isinstance(item.get("observables"), dict) or not item["observables"]
            ):
                raise ValueError(f"{field}.{key} needs observable assertions")
    for key in ("required_order", "forbidden_orderings"):
        if not isinstance(value[key], list) or any(
            not isinstance(item, str) or not item.strip() for item in value[key]
        ):
            raise ValueError(f"{field}.{key} must be a text array")
    if not isinstance(value["validation_profile"], str) or not value["validation_profile"].strip():
        raise ValueError(f"{field}.validation_profile must be non-empty")
    tests = value["required_focused_tests"]
    if (
        not isinstance(tests, list)
        or not tests
        or any(not isinstance(test, str) or not test.strip() for test in tests)
        or len(tests) != len(set(tests))
    ):
        raise ValueError(f"{field}.required_focused_tests must be distinct and non-empty")
    for test in tests:
        path = relative_path(test.split("::", 1)[0], f"{field}.required_focused_tests")
        if not any(path_inside(path, root) for root in authority["read_roots"]):
            raise ValueError(f"{field} requires a test outside Primary read scope: {path}")
        if path not in authority["readonly"]:
            raise ValueError(f"{field} must protect its required test as read-only: {path}")
    return value


def validate_feature_plan(plan: dict) -> dict:
    """Validate Primary-owned contracts and compute effective unit risk."""
    if (
        not isinstance(plan, dict)
        or type(plan.get("schema_version")) is not int
        or plan["schema_version"] != 1
    ):
        raise ValueError("feature plan must use schema version 1")
    identifier(plan.get("feature_id"), "feature_id")
    identifier(plan.get("task_id"), "task_id")
    if type(plan.get("plan_revision")) is not int or plan["plan_revision"] < 1:
        raise ValueError("plan_revision must be a positive integer")
    risk(plan.get("feature_risk"), "feature_risk")
    risk(plan.get("integration_risk"), "integration_risk")
    contracts = plan.get("contracts")
    units = plan.get("units")
    if not isinstance(contracts, list) or not contracts:
        raise ValueError("contracts must be a non-empty array")
    if not isinstance(units, list) or not units:
        raise ValueError("units must be a non-empty array")
    floors: dict[str, str] = {}
    for item in contracts:
        if not isinstance(item, dict):
            raise ValueError("contract must be an object")
        key = identifier(item.get("id"), "contract.id")
        if key in floors:
            raise ValueError(f"duplicate contract id: {key}")
        if not isinstance(item.get("text"), str) or not item["text"].strip():
            raise ValueError(f"contracts.{key}.text must be non-empty")
        floors[key] = risk(item.get("risk_floor"), f"contracts.{key}.risk_floor")

    unit_ids: set[str] = set()
    owned: dict[str, str] = {}
    graph: dict[str, list[str]] = {}
    effective: dict[str, str] = {}
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError("unit must be an object")
        unit_id = identifier(unit.get("unit_id"), "unit.unit_id")
        if unit_id in unit_ids:
            raise ValueError(f"duplicate unit id: {unit_id}")
        unit_ids.add(unit_id)
        proposed = risk(unit.get("risk"), f"units.{unit_id}.risk")
        authority = scope_authority(unit.get("scope_authority"), f"units.{unit_id}.scope_authority")
        owner = unit.get("owner")
        if owner not in {"primary", "local-coder"}:
            raise ValueError(f"units.{unit_id}.owner must be primary or local-coder")
        if owner == "local-coder":
            packet_contract(
                unit.get("packet_contract"), f"units.{unit_id}.packet_contract", authority
            )
        contract_ids = unit.get("owned_contract_ids")
        deps = unit.get("dependencies")
        if not isinstance(contract_ids, list) or not contract_ids:
            raise ValueError(f"units.{unit_id}.owned_contract_ids must be non-empty")
        if not isinstance(deps, list):
            raise ValueError(f"units.{unit_id}.dependencies must be an array")
        if any(not isinstance(item, str) for item in contract_ids + deps):
            raise ValueError(f"units.{unit_id} contract and dependency ids must be strings")
        if len(contract_ids) != len(set(contract_ids)) or len(deps) != len(set(deps)):
            raise ValueError(f"units.{unit_id} has duplicate contract or dependency ids")
        graph[unit_id] = [identifier(dep, "dependency") for dep in deps]
        level = RISK[proposed]
        for raw_id in contract_ids:
            contract_id = identifier(raw_id, "owned_contract_id")
            if contract_id not in floors:
                raise ValueError(f"unknown contract id: {contract_id}")
            if contract_id in owned:
                raise ValueError(f"contract {contract_id} already owned by {owned[contract_id]}")
            owned[contract_id] = unit_id
            level = max(level, RISK[floors[contract_id]])
        effective[unit_id] = next(name for name, rank in RISK.items() if rank == level)
    missing = sorted(floors.keys() - owned.keys())
    if missing:
        raise ValueError("unowned contract ids: " + ", ".join(missing))

    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(unit_id: str) -> None:
        if unit_id in visiting:
            raise ValueError(f"dependency cycle at {unit_id}")
        if unit_id in visited:
            return
        visiting.add(unit_id)
        for dep in graph[unit_id]:
            if dep not in graph:
                raise ValueError(f"unknown dependency: {dep}")
            visit(dep)
        visiting.remove(unit_id)
        visited.add(unit_id)

    for unit_id in graph:
        visit(unit_id)
    return {"feature_id": plan["feature_id"], "effective_unit_risk": effective}


def validate_unit_packet(plan: dict, candidate: dict) -> dict:
    """Check a proposed packet against Primary's plan and Coder schema v2."""
    validated = validate_feature_plan(plan)
    if not isinstance(candidate, dict) or candidate.get("schema_version") != 2:
        raise ValueError("Coordinator packet must use schema version 2")
    unit_id = candidate.get("unit_id")
    units = {unit["unit_id"]: unit for unit in plan["units"]}
    if unit_id not in units:
        raise ValueError(f"packet references unknown unit: {unit_id}")
    unit = units[unit_id]
    if unit["owner"] != "local-coder":
        raise ValueError(f"Primary-owned unit cannot receive a Coder packet: {unit_id}")
    if candidate.get("feature_id") != plan["feature_id"]:
        raise ValueError("packet feature_id differs from Primary plan")
    if candidate.get("task_id") != plan["task_id"]:
        raise ValueError("packet task_id differs from Primary plan")
    if candidate.get("plan_revision") != plan["plan_revision"]:
        raise ValueError("packet plan_revision differs from Primary plan")
    if candidate.get("primary_plan_sha256") != authority_fingerprint(plan):
        raise ValueError("packet Primary plan fingerprint is missing or stale")
    if candidate.get("dependencies") != unit["dependencies"]:
        raise ValueError("packet dependencies differ from Primary plan")
    if candidate.get("owned_contract_ids") != unit["owned_contract_ids"]:
        raise ValueError("packet owned contracts differ from Primary plan")
    contracts = {item["id"]: item for item in plan["contracts"]}
    behaviors = candidate.get("required_behavior")
    if not isinstance(behaviors, list) or any(not isinstance(item, dict) for item in behaviors):
        raise ValueError("packet required_behavior must be an array of contracts")
    for item in behaviors:
        contract_id = identifier(item.get("id"), "packet required_behavior.id")
        if contract_id not in contracts:
            raise ValueError(
                f"packet required_behavior references undeclared contract id: {contract_id}"
            )
    if {item["id"] for item in behaviors} != set(unit["owned_contract_ids"]) or len(
        behaviors
    ) != len(unit["owned_contract_ids"]):
        raise ValueError("packet required_behavior differs from owned Primary contracts")
    for item in behaviors:
        if item.get("text") != contracts[item["id"]]["text"]:
            raise ValueError(f"packet changed Primary contract text: {item['id']}")
    packet = copy.deepcopy(candidate)
    for item in packet["required_behavior"]:
        item["risk_floor"] = contracts[item["id"]]["risk_floor"]
    proposed_risk = packet.get("risk")
    if not isinstance(proposed_risk, dict):
        raise ValueError("packet risk must be an object")
    if (
        proposed_risk.get("feature") != plan["feature_risk"]
        or proposed_risk.get("integration") != plan["integration_risk"]
    ):
        raise ValueError("packet feature/integration risk differs from Primary plan")
    declared = risk(proposed_risk.get("unit"), "packet risk.unit")
    effective = validated["effective_unit_risk"][unit_id]
    proposed_risk["unit"] = max((declared, effective), key=RISK.get)

    path = Path(__file__).with_name("worker-runtime.py")
    spec = importlib.util.spec_from_file_location("coordinator_worker_schema", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    normalized = module.validate_packet(packet)
    authority = scope_authority(unit["scope_authority"], "unit.scope_authority")
    scope = normalized["scope"]
    for path in scope["read"]:
        if not any(path_inside(path, root) for root in authority["read_roots"]):
            raise ValueError(f"packet read path exceeds Primary authority: {path}")
    for key in ("modify", "create"):
        for path in scope[key]:
            if path not in authority[key]:
                raise ValueError(f"packet {key} path exceeds Primary authority: {path}")
    if not set(authority["readonly"]) <= set(scope["readonly"]):
        raise ValueError("packet omitted Primary protected read-only paths")
    if not set(authority["forbidden"]) <= set(scope["forbidden"]):
        raise ValueError("packet omitted Primary forbidden paths")
    obligations = packet_contract(
        unit["packet_contract"], f"units.{unit_id}.packet_contract", authority
    )
    for key in (
        "acceptance_criteria",
        "acceptance_scenarios",
        "required_order",
        "forbidden_orderings",
        "validation_profile",
    ):
        if normalized[key] != obligations[key]:
            raise ValueError(f"packet changed Primary {key}")
    if not set(obligations["required_focused_tests"]) <= set(normalized["focused_tests"]):
        raise ValueError("packet omitted Primary required focused tests")
    return normalized


def materialize_bounded_packet(plan: dict, proposal: dict) -> dict:
    """Fill immutable obligations from Primary's plan; proposal grants no authority."""
    validated = validate_feature_plan(plan)
    fields = {
        "unit_id",
        "run_id",
        "attempt",
        "packet_revision",
        "goal",
        "scope",
        "edit_targets",
        "focused_tests",
        "supplemental_tests",
        "implementation_guidance",
    }
    if not isinstance(proposal, dict) or set(proposal) != fields:
        raise ValueError("bounded packet proposal has missing or authority-bearing fields")
    unit_id = identifier(proposal["unit_id"], "proposal.unit_id")
    unit = next((item for item in plan["units"] if item["unit_id"] == unit_id), None)
    if unit is None or unit["owner"] != "local-coder":
        raise ValueError("proposal must name a local-coder unit in the Primary plan")
    scope = proposal["scope"]
    if not isinstance(scope, dict) or set(scope) != {"read", "modify", "create"}:
        raise ValueError("proposal scope must explicitly choose read, modify, and create")
    if not scope["modify"] and not scope["create"]:
        raise ValueError("proposal needs at least one writable file")
    authority = scope_authority(unit["scope_authority"], "unit.scope_authority")
    contract = packet_contract(unit["packet_contract"], "unit.packet_contract", authority)
    registry = {item["id"]: item for item in plan["contracts"]}
    packet = {
        "schema_version": 2,
        "task_id": plan["task_id"],
        "feature_id": plan["feature_id"],
        "unit_id": unit_id,
        "run_id": proposal["run_id"],
        "attempt": proposal["attempt"],
        "plan_revision": plan["plan_revision"],
        "packet_revision": proposal["packet_revision"],
        "primary_plan_sha256": authority_fingerprint(plan),
        "goal": proposal["goal"],
        "risk": {
            "feature": plan["feature_risk"],
            "unit": validated["effective_unit_risk"][unit_id],
            "integration": plan["integration_risk"],
            "reasons": ["Primary-owned contract and scoped implementation unit."],
        },
        "dependencies": copy.deepcopy(unit["dependencies"]),
        "owned_contract_ids": copy.deepcopy(unit["owned_contract_ids"]),
        "scope": {
            "read": copy.deepcopy(scope["read"]),
            "modify": copy.deepcopy(scope["modify"]),
            "create": copy.deepcopy(scope["create"]),
            "readonly": copy.deepcopy(authority["readonly"]),
            "forbidden": copy.deepcopy(authority["forbidden"]),
        },
        "edit_targets": copy.deepcopy(proposal["edit_targets"]),
        "focused_tests": copy.deepcopy(proposal["focused_tests"]),
        "supplemental_tests": copy.deepcopy(proposal["supplemental_tests"]),
        "implementation_guidance": copy.deepcopy(proposal["implementation_guidance"]),
        "required_behavior": [
            {
                "id": contract_id,
                "text": registry[contract_id]["text"],
                "risk_floor": registry[contract_id]["risk_floor"],
            }
            for contract_id in unit["owned_contract_ids"]
        ],
        "required_order": copy.deepcopy(contract["required_order"]),
        "forbidden_orderings": copy.deepcopy(contract["forbidden_orderings"]),
        "contract_check_required": True,
        "acceptance_criteria": copy.deepcopy(contract["acceptance_criteria"]),
        "acceptance_scenarios": copy.deepcopy(contract["acceptance_scenarios"]),
        "validation_profile": contract["validation_profile"],
    }
    return validate_unit_packet(plan, packet)


def validate_localization_dispatch(
    plan: dict, packet: dict, request: dict, report: dict, *, repo_root: Path
) -> dict:
    """Fail closed before dispatch; locate evidence is never a semantic verdict."""
    normalized = validate_unit_packet(plan, packet)
    if not isinstance(request, dict) or set(request) != {
        "capability",
        "task_id",
        "unit_id",
        "question",
    }:
        raise ValueError("localization dispatch requires explicit capability and identity")
    if request["capability"] != "localization_only":
        raise ValueError("unsupported exploration capability; escalate to Primary")
    if request["task_id"] != normalized["task_id"] or request["unit_id"] != normalized["unit_id"]:
        raise ValueError("localization request differs from packet identity")
    if not isinstance(request["question"], str) or not request["question"].strip():
        raise ValueError("localization question must be nonempty")
    if (
        not isinstance(report, dict)
        or report.get("status") != "success"
        or report.get("explorer_mode") != "locate"
        or report.get("semantic_verdict") != "not_evaluated"
        or report.get("task_id") != normalized["task_id"]
        or report.get("task") != request["question"]
    ):
        raise ValueError("Explorer localization evidence is missing or not qualified")
    if report.get("uncertainties"):
        raise ValueError("Explorer localization is uncertain; escalate to Primary")
    refs = report.get("source_refs")
    if not isinstance(refs, list) or not 1 <= len(refs) <= 6:
        raise ValueError("Explorer localization needs bounded source_refs")
    root = repo_root.resolve()
    writable = set(normalized["scope"]["modify"])
    readable = normalized["scope"]["read"] + normalized["scope"]["readonly"]
    forbidden = normalized["scope"]["forbidden"]
    found_target = False
    total_lines = 0
    for ref in refs:
        if not isinstance(ref, dict):
            raise ValueError("Explorer source_ref must be an object")
        relative = relative_path(ref.get("path"), "Explorer source_ref.path")
        if not any(path_inside(relative, allowed) for allowed in readable):
            raise ValueError(f"Explorer source_ref exceeds packet read scope: {relative}")
        if any(path_inside(relative, denied) for denied in forbidden):
            raise ValueError(f"Explorer source_ref is forbidden: {relative}")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Explorer source_ref is unavailable: {relative}")
        start, end = ref.get("start_line"), ref.get("end_line")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise ValueError("Explorer source_ref line range is invalid")
        total_lines += end - start + 1
        if total_lines > 80:
            raise ValueError("Explorer source_refs exceed bounded lines")
        if ref.get("kind") not in {"implementation", "definition", "caller", "test"}:
            raise ValueError("Explorer source_ref kind is invalid")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref.get("source_hash"):
            raise ValueError(f"Explorer source_ref is stale: {relative}")
        try:
            lines = raw.decode("utf-8-sig").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError(f"Explorer source_ref is not UTF-8: {relative}") from exc
        if end > len(lines):
            raise ValueError(f"Explorer source_ref exceeds file lines: {relative}")
        if ref.get("quote") != "\n".join(lines[start - 1 : end]):
            raise ValueError(f"Explorer source_ref quote differs from current file: {relative}")
        if len(ref["quote"]) > 8000:
            raise ValueError("Explorer source_ref quote is oversized")
        if ref.get("kind") in {"implementation", "definition"} and relative in writable:
            found_target = True
    if not found_target:
        raise ValueError("Explorer did not locate an authorized implementation target")
    return {
        "capability": "localization_only",
        "unit_id": normalized["unit_id"],
        "source_refs": refs,
    }


def validate_decision(plan: dict, candidate: dict) -> dict:
    """Parse only the closed Coordinator status shape; not a state transition."""
    validate_feature_plan(plan)
    if not isinstance(candidate, dict) or set(candidate) - {
        "decision",
        "unit_id",
        "reason_code",
    }:
        raise ValueError("Coordinator decision has unknown fields")
    choice = candidate.get("decision")
    if not isinstance(choice, str) or choice not in DECISIONS:
        raise ValueError("Coordinator decision is not a legal enum value")
    unit_id = identifier(candidate.get("unit_id"), "decision.unit_id")
    if unit_id not in {unit["unit_id"] for unit in plan["units"]}:
        raise ValueError(f"Coordinator decision references unknown unit: {unit_id}")
    if choice in {"REWORK_LOCAL", "ESCALATE_PRIMARY"}:
        identifier(candidate.get("reason_code"), "decision.reason_code")
    elif "reason_code" in candidate:
        raise ValueError(f"{choice} must not include reason_code")
    return dict(candidate)


def _validate_decision_transition(
    plan: dict,
    candidate: dict,
    *,
    primary_accepted_units: set[str],
    integration_verified: bool = False,
) -> dict:
    """Gate offline decisions using acceptance identities supplied by Primary."""
    decision = validate_decision(plan, candidate)
    units = {unit["unit_id"]: unit for unit in plan["units"]}
    unknown = primary_accepted_units - units.keys()
    if unknown:
        raise ValueError("accepted set contains unknown units: " + ", ".join(sorted(unknown)))
    choice = decision["decision"]
    unit_id = decision["unit_id"]
    if choice == "FEATURE_READY":
        missing = units.keys() - primary_accepted_units
        if missing:
            raise ValueError(
                "feature is not ready; unaccepted units: " + ", ".join(sorted(missing))
            )
        if integration_verified is not True:
            raise ValueError("feature is not ready; integration evidence is unverified")
    elif choice == "CONTINUE":
        if unit_id in primary_accepted_units:
            raise ValueError(f"unit already accepted: {unit_id}")
        missing = set(units[unit_id]["dependencies"]) - primary_accepted_units
        if missing:
            raise ValueError("unit dependencies are not accepted: " + ", ".join(sorted(missing)))
    elif choice == "REWORK_LOCAL" and unit_id in primary_accepted_units:
        raise ValueError(f"cannot locally rework accepted unit: {unit_id}")
    return decision


def accepted_units_from_archives(
    plan: dict, repo_root: Path, run_refs: dict[str, dict[str, str]]
) -> set[str]:
    """Derive accepted units from archived Primary and Reviewer decisions."""
    validate_feature_plan(plan)
    root = repo_root.resolve()
    task_root = root / ".agent" / "tasks"
    known_units = {unit["unit_id"]: unit for unit in plan["units"]}
    accepted: set[str] = set()
    for unit_id, ref in run_refs.items():
        if unit_id not in known_units or not isinstance(ref, dict):
            raise ValueError(f"unknown unit archive reference: {unit_id}")

        def read(path: Path) -> dict:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError(f"archive record is not an object: {path}")
            return value

        if known_units[unit_id]["owner"] == "primary":
            if ref:
                raise ValueError(f"Primary unit must use its fixed review path: {unit_id}")
            review_path = (
                root / ".agent" / "primary-reviews" / plan["feature_id"] / f"{unit_id}.json"
            )
            primary_review = read(review_path)
            if (
                primary_review.get("schema_version") != 1
                or primary_review.get("feature_id") != plan["feature_id"]
                or primary_review.get("unit_id") != unit_id
                or primary_review.get("plan_revision") != plan["plan_revision"]
                or primary_review.get("primary_plan_sha256") != authority_fingerprint(plan)
                or primary_review.get("decision") != "accept"
                or not isinstance(primary_review.get("evidence"), list)
                or not primary_review["evidence"]
            ):
                raise ValueError(f"Primary unit acceptance evidence is missing or stale: {unit_id}")
            authority = scope_authority(
                known_units[unit_id]["scope_authority"], f"units.{unit_id}.scope_authority"
            )
            changed_files = primary_review.get("changed_files", [])
            if not isinstance(changed_files, list):
                raise ValueError(f"Primary changed_files must be an array: {unit_id}")
            for item in changed_files:
                path = relative_path(item, "Primary changed path")
                if path not in authority["modify"] + authority["create"]:
                    raise ValueError(f"Primary unit changed path exceeds plan: {path}")
            accepted.add(unit_id)
            continue
        task_id = identifier(ref.get("task_id"), "archive.task_id")
        run_id = identifier(ref.get("run_id"), "archive.run_id")
        archive = (task_root / task_id / "runs" / run_id).resolve()
        if not archive.is_relative_to(task_root):
            raise ValueError(f"archive escapes task root: {unit_id}")

        review = read(archive / "review.json")
        handoff = read(archive / "handoff.json")
        completed = read(archive / "completed.json")
        archived_packet = read(archive / "packet.json")
        identity = handoff.get("identity", {})
        expected = {"task_id": task_id, "unit_id": unit_id, "run_id": run_id}
        if any(
            review.get(key) != value or identity.get(key) != value
            for key, value in expected.items()
        ):
            raise ValueError(f"Primary/Coder archive identity mismatch: {unit_id}")
        if identity.get("feature_id") != plan["feature_id"]:
            raise ValueError(f"archive feature identity mismatch: {unit_id}")
        if (
            identity.get("plan_revision") != plan["plan_revision"]
            or archived_packet.get("plan_revision") != plan["plan_revision"]
            or archived_packet.get("primary_plan_sha256") != authority_fingerprint(plan)
        ):
            raise ValueError(f"archive Primary plan evidence is stale: {unit_id}")
        if archived_packet.get("task_id") != task_id or archived_packet.get("run_id") != run_id:
            raise ValueError(f"archive packet identity mismatch: {unit_id}")
        normalized_packet = validate_unit_packet(plan, archived_packet)
        changed_files = handoff.get("changed_files", [])
        if not isinstance(changed_files, list):
            raise ValueError(f"archive changed_files must be an array: {unit_id}")
        for change in changed_files:
            if not isinstance(change, dict):
                raise ValueError(f"archive change must be an object: {unit_id}")
            path = relative_path(change.get("path"), "archive changed path")
            if (
                path
                not in normalized_packet["scope"]["modify"] + normalized_packet["scope"]["create"]
            ):
                raise ValueError(f"archive changed path exceeds Primary authority: {path}")
        if (
            review.get("decision") != "accept"
            or review.get("worker_status") != "ready_for_review"
            or handoff.get("status") != "ready_for_review"
            or completed.get("status") != "ready_for_review"
        ):
            raise ValueError(f"unit lacks accepted Coder evidence: {unit_id}")
        review_id = identifier(review.get("local_review_id"), "review.local_review_id")
        review_root = task_root / task_id / "reviews" / review_id
        local_handoff = read(review_root / "handoff.json")
        local_completed = read(review_root / "completed.json")
        local_identity = local_handoff.get("identity", {})
        if any(local_identity.get(key) != value for key, value in expected.items()) or (
            local_identity.get("review_id") != review_id
            or local_handoff.get("decision") != "pass_to_primary"
            or local_completed.get("decision") != "pass_to_primary"
        ):
            raise ValueError(f"unit lacks matching Reviewer pass: {unit_id}")
        accepted.add(unit_id)
    return accepted


def verify_integration_archive(
    plan: dict, repo_root: Path, run_refs: dict[str, dict[str, str]]
) -> None:
    """Check trusted integration evidence against accepted changes and current files."""
    root = repo_root.resolve()
    changed_paths: set[str] = set()
    units = {unit["unit_id"]: unit for unit in plan["units"]}
    for unit_id, ref in run_refs.items():
        if units[unit_id]["owner"] == "primary":
            record = root / ".agent" / "primary-reviews" / plan["feature_id"] / f"{unit_id}.json"
            source = json.loads(record.read_text(encoding="utf-8"))
        else:
            archive = root / ".agent" / "tasks" / ref["task_id"] / "runs" / ref["run_id"]
            source = json.loads((archive / "handoff.json").read_text(encoding="utf-8"))
        for item in source.get("changed_files", []):
            path = item.get("path") if isinstance(item, dict) else item
            changed_paths.add(relative_path(path, "accepted changed path"))

    path = root / ".agent" / "integration" / plan["feature_id"] / "validation.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict) or any(
        evidence.get(key) != expected
        for key, expected in {
            "schema_version": 1,
            "feature_id": plan["feature_id"],
            "plan_revision": plan["plan_revision"],
            "primary_plan_sha256": authority_fingerprint(plan),
            "integration_risk": plan["integration_risk"],
            "status": "passed",
        }.items()
    ):
        raise ValueError("integration evidence is missing, failed, or stale")
    checks = evidence.get("checks")
    if (
        not isinstance(checks, list)
        or not checks
        or any(
            not isinstance(item, dict)
            or item.get("status") != "passed"
            or item.get("exit_code") != 0
            or not isinstance(item.get("id"), str)
            for item in checks
        )
    ):
        raise ValueError("integration checks need executed passing evidence")
    files = evidence.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("integration evidence needs file hashes")
    witnessed: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("integration file record must be an object")
        relative = relative_path(item.get("path"), "integration file")
        candidate = (root / relative).resolve()
        if relative in witnessed or not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError(f"integration file is missing or duplicated: {relative}")
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != item.get("sha256"):
            raise ValueError(f"integration file changed after validation: {relative}")
        witnessed.add(relative)
    missing = changed_paths - witnessed
    if missing:
        raise ValueError(
            "integration evidence omits accepted changes: " + ", ".join(sorted(missing))
        )


def validate_decision_transition(
    plan: dict,
    candidate: dict,
    *,
    repo_root: Path,
    run_refs: dict[str, dict[str, str]],
) -> dict:
    """Public offline gate: never trust Coordinator-authored acceptance sets."""
    decision = validate_decision(plan, candidate)
    accepted = accepted_units_from_archives(plan, repo_root, run_refs)
    integration_verified = False
    if decision["decision"] == "FEATURE_READY":
        verify_integration_archive(plan, repo_root, run_refs)
        integration_verified = True
    return _validate_decision_transition(
        plan,
        decision,
        primary_accepted_units=accepted,
        integration_verified=integration_verified,
    )


def new_coordinator_state(plan: dict) -> dict:
    """Create offline execution memory; acceptance remains in Primary archives."""
    validate_feature_plan(plan)
    return {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "task_id": plan["task_id"],
        "plan_revision": plan["plan_revision"],
        "primary_plan_sha256": authority_fingerprint(plan),
        "sequence": 0,
        "feature_phase": "open",
        "units": {
            unit["unit_id"]: {
                "phase": "pending",
                "rework_count": 0,
                "last_failure_signature": None,
            }
            for unit in plan["units"]
        },
        "policy_violation_blocked_count": 0,
        "infra_failure_count": 0,
        "recent_events": [],
    }


def validate_coordinator_state(plan: dict, state: dict) -> None:
    """Reject stale or authority-claiming Coordinator memory."""
    validate_feature_plan(plan)
    expected = new_coordinator_state(plan)
    if not isinstance(state, dict) or set(state) != set(expected):
        raise ValueError("Coordinator state has missing or unknown fields")
    for key in (
        "schema_version",
        "feature_id",
        "task_id",
        "plan_revision",
        "primary_plan_sha256",
    ):
        if state[key] != expected[key]:
            raise ValueError(f"Coordinator state {key} differs from Primary plan")
    if type(state["schema_version"]) is not int or type(state["plan_revision"]) is not int:
        raise ValueError("Coordinator state schema and plan revisions must be integers")
    if not isinstance(state["feature_phase"], str) or state["feature_phase"] not in {
        "open",
        "ready",
    }:
        raise ValueError("Coordinator feature_phase is not legal")
    for key in ("sequence", "policy_violation_blocked_count", "infra_failure_count"):
        if type(state[key]) is not int or state[key] < 0:
            raise ValueError(f"Coordinator state {key} must be a non-negative integer")
    units = state["units"]
    if not isinstance(units, dict) or set(units) != set(expected["units"]):
        raise ValueError("Coordinator state unit identities differ from Primary plan")
    for unit_id, memory in units.items():
        if not isinstance(memory, dict) or set(memory) != {
            "phase",
            "rework_count",
            "last_failure_signature",
        }:
            raise ValueError(f"Coordinator state unit memory is malformed: {unit_id}")
        if not isinstance(memory["phase"], str) or memory["phase"] not in {
            "pending",
            "running",
            "rework",
            "escalated",
        }:
            raise ValueError(f"Coordinator state unit phase is not legal: {unit_id}")
        if type(memory["rework_count"]) is not int or memory["rework_count"] < 0:
            raise ValueError(f"Coordinator state rework_count is invalid: {unit_id}")
        signature = memory["last_failure_signature"]
        if signature is not None:
            identifier(signature, f"units.{unit_id}.last_failure_signature")
    events = state["recent_events"]
    if not isinstance(events, list) or len(events) > 50:
        raise ValueError("Coordinator recent_events must be a bounded array")
    if state["sequence"] > 0 and not events:
        raise ValueError("Coordinator state sequence lacks recent events")
    previous = max(0, state["sequence"] - len(events))
    for event in events:
        if not isinstance(event, dict) or set(event) != {
            "sequence",
            "unit_id",
            "decision",
            "outcome",
            "reason_code",
        }:
            raise ValueError("Coordinator event is malformed")
        previous += 1
        if (
            type(event["sequence"]) is not int
            or event["sequence"] != previous
            or not isinstance(event["unit_id"], str)
            or event["unit_id"] not in units
        ):
            raise ValueError("Coordinator event sequence or unit identity is invalid")
        if (
            not isinstance(event["decision"], str)
            or not isinstance(event["outcome"], str)
            or event["decision"] not in DECISIONS
            or event["outcome"]
            not in {
                "allowed",
                "blocked",
                "infra_failure",
            }
        ):
            raise ValueError("Coordinator event decision or outcome is invalid")
        if event["reason_code"] is not None:
            identifier(event["reason_code"], "event.reason_code")
        if event["outcome"] in {"blocked", "infra_failure"} and event["reason_code"] is None:
            raise ValueError("blocked or infra Coordinator event needs a reason_code")
    if events and previous != state["sequence"]:
        raise ValueError("Coordinator event sequence is stale")
    if state["policy_violation_blocked_count"] < sum(
        event["outcome"] == "blocked" for event in events
    ):
        raise ValueError("Coordinator policy counter is below recorded blocks")
    if state["infra_failure_count"] < sum(event["outcome"] == "infra_failure" for event in events):
        raise ValueError("Coordinator infra counter is below recorded failures")


def apply_coordinator_decision(
    plan: dict,
    state: dict,
    candidate: dict,
    *,
    expected_sequence: int,
    repo_root: Path,
    run_refs: dict[str, dict[str, str]],
) -> dict:
    """Advance memory only after archive-backed transition validation."""
    validate_coordinator_state(plan, state)
    if state["sequence"] != expected_sequence:
        raise ValueError("Coordinator state sequence is stale")
    if state["feature_phase"] == "ready":
        raise ValueError("Coordinator feature is already ready")
    decision = validate_decision_transition(plan, candidate, repo_root=repo_root, run_refs=run_refs)
    updated = copy.deepcopy(state)
    unit_id = decision["unit_id"]
    choice = decision["decision"]
    memory = updated["units"][unit_id]
    if memory["phase"] == "escalated" and choice in {"CONTINUE", "REWORK_LOCAL"}:
        raise ValueError("escalated unit needs a new Primary plan or review")
    if choice == "CONTINUE":
        memory["phase"] = "running"
    elif choice == "REWORK_LOCAL":
        memory["phase"] = "rework"
        memory["rework_count"] += 1
        memory["last_failure_signature"] = decision["reason_code"]
    elif choice == "ESCALATE_PRIMARY":
        memory["phase"] = "escalated"
        memory["last_failure_signature"] = decision["reason_code"]
    elif choice == "FEATURE_READY":
        updated["feature_phase"] = "ready"
    updated["sequence"] += 1
    updated["recent_events"].append(
        {
            "sequence": updated["sequence"],
            "unit_id": unit_id,
            "decision": choice,
            "outcome": "allowed",
            "reason_code": decision.get("reason_code"),
        }
    )
    updated["recent_events"] = updated["recent_events"][-50:]
    validate_coordinator_state(plan, updated)
    return updated


def record_policy_block(plan: dict, state: dict, unit_id: str, reason_code: str) -> dict:
    """Trusted guardrail counter; a blocked proposal grants no unit authority."""
    validate_coordinator_state(plan, state)
    identifier(unit_id, "unit_id")
    identifier(reason_code, "reason_code")
    if unit_id not in state["units"]:
        raise ValueError(f"unknown unit: {unit_id}")
    updated = copy.deepcopy(state)
    updated["sequence"] += 1
    updated["policy_violation_blocked_count"] += 1
    updated["recent_events"].append(
        {
            "sequence": updated["sequence"],
            "unit_id": unit_id,
            "decision": "ESCALATE_PRIMARY",
            "outcome": "blocked",
            "reason_code": reason_code,
        }
    )
    updated["recent_events"] = updated["recent_events"][-50:]
    validate_coordinator_state(plan, updated)
    return updated


def record_infra_failure(plan: dict, state: dict, unit_id: str, reason_code: str) -> dict:
    """Track transport/process failures without worker-quality or policy authority."""
    validate_coordinator_state(plan, state)
    identifier(unit_id, "unit_id")
    identifier(reason_code, "reason_code")
    if unit_id not in state["units"]:
        raise ValueError(f"unknown unit: {unit_id}")
    updated = copy.deepcopy(state)
    updated["sequence"] += 1
    updated["infra_failure_count"] += 1
    updated["recent_events"].append(
        {
            "sequence": updated["sequence"],
            "unit_id": unit_id,
            "decision": "ESCALATE_PRIMARY",
            "outcome": "infra_failure",
            "reason_code": reason_code,
        }
    )
    updated["recent_events"] = updated["recent_events"][-50:]
    validate_coordinator_state(plan, updated)
    return updated


def _state_path(repo_root: Path, path: Path) -> Path:
    """Keep durable Coordinator memory in the repository's private .agent tree."""
    root = repo_root.absolute()
    target = path.absolute()
    if ".." in path.parts:
        raise ValueError("Coordinator state path must not contain traversal")
    if not target.is_relative_to(root / ".agent") or target == root / ".agent":
        raise ValueError("Coordinator state path must be inside repository .agent")
    current = root
    for component in target.relative_to(root).parts:
        current = current / component
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError("Coordinator state path traverses a reparse point")
    return target


def load_coordinator_state(plan: dict, repo_root: Path, path: Path) -> dict:
    """Load durable memory, or initialize an absent state without writing it."""
    target = _state_path(repo_root, path)
    if not target.exists():
        return new_coordinator_state(plan)
    try:
        state = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Coordinator state is unreadable; Primary recovery required") from exc
    validate_coordinator_state(plan, state)
    return state


def persist_coordinator_transition(
    plan: dict,
    repo_root: Path,
    path: Path,
    *,
    expected_sequence: int,
    transition,
) -> dict:
    """Serialize one validated transition with a fail-closed sequence CAS."""
    target = _state_path(repo_root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target = _state_path(repo_root, target)
    lock = target.with_name(target.name + ".lock")
    temporary = target.with_name(target.name + ".tmp-" + uuid.uuid4().hex)
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError("Coordinator state writer lock exists; inspect before retry") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "state_path": str(target)}))
            stream.flush()
            os.fsync(stream.fileno())
        current = load_coordinator_state(plan, repo_root, target)
        if type(expected_sequence) is not int or current["sequence"] != expected_sequence:
            raise ValueError("Coordinator state sequence is stale")
        updated = transition(current)
        validate_coordinator_state(plan, updated)
        if updated["sequence"] != expected_sequence + 1:
            raise ValueError("Coordinator transition must advance exactly one sequence")
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(updated, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        return updated
    finally:
        if temporary.exists():
            temporary.unlink()
        lock.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            validate_feature_plan(json.loads(args.plan.read_text(encoding="utf-8"))), indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
