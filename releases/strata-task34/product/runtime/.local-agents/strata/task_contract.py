"""Compile a small trusted task contract into the existing qualified hosts."""

import copy

from general_state import StateError, identifier

COMMON = {
    "schema_version",
    "task_id",
    "kind",
    "goal",
    "deliverable",
    "scope",
    "risk",
    "required_behavior",
    "acceptance_criteria",
    "capabilities",
    "implementation",
    "feature_id",
    "dependencies",
    "owned_contract_ids",
    "approved_skills",
}
IMPLEMENTATION = {
    "edit_targets",
    "focused_tests",
    "supplemental_tests",
    "validation_profile",
    "acceptance_scenarios",
    "required_order",
    "forbidden_orderings",
}
FORBIDDEN = [".agent", ".local-agents", ".git", "acceptance_private"]


def compile_contract(contract, config):
    contract, config = copy.deepcopy(contract), copy.deepcopy(config)
    if config.get("experimental_strata_task") is not True:
        raise StateError("Explicit experimental_strata_task opt-in required")
    if (
        not isinstance(contract, dict)
        or set(contract) - COMMON
        or type(contract.get("schema_version")) is not int
        or contract.get("schema_version") != 1
    ):
        raise StateError("Unknown task contract fields/version")
    identifier(contract.get("task_id"))
    kind = contract.get("kind")
    if kind not in {"investigate", "implement"}:
        raise StateError("Task kind must be investigate or implement")
    for field in ("goal", "deliverable"):
        if not isinstance(contract.get(field), str) or not 1 <= len(contract[field]) <= 6000:
            raise StateError("Bounded goal and deliverable required")
    for field in ("required_behavior", "acceptance_criteria"):
        if not isinstance(contract.get(field), list) or not contract[field]:
            raise StateError("Explicit behavior and acceptance criteria required")
        from review_impl_binding import FLAG, VERSION

        optional = set()
        if config.get(FLAG) == VERSION:
            optional.add("risk_floor")
            if field == "required_behavior":
                optional.add("implementation_ref")
        if any(
            not isinstance(c, dict)
            or not {"id", "text"} <= set(c)
            or bool(set(c) - {"id", "text"} - optional)
            or not isinstance(c.get("id"), str)
            or not c.get("id")
            or not isinstance(c.get("text"), str)
            or not c.get("text")
            for c in contract[field]
        ):
            raise StateError("Behavior/criteria entries require id and text")
    scope = contract.get("scope")
    if not isinstance(scope, dict) or set(scope) - {
        "read",
        "readonly",
        "modify",
        "create",
        "forbidden",
    }:
        raise StateError("Explicit source scope required")
    if not isinstance(scope.get("read"), list) or not scope["read"]:
        raise StateError("Approved readable sources required")
    for value in scope.values():
        if not isinstance(value, list) or any(not isinstance(p, str) or not p for p in value):
            raise StateError("Scope fields must be path arrays")
    risk = contract.get("risk")
    if not isinstance(risk, dict) or any(
        risk.get(k) not in {"small", "medium", "high"} for k in ("feature", "unit", "integration")
    ):
        raise StateError("Primary feature/unit/integration risk required")
    scope = {k: scope.get(k, []) for k in ("read", "readonly", "modify", "create", "forbidden")}
    scope["forbidden"] = list(dict.fromkeys([*scope["forbidden"], *FORBIDDEN]))
    payload = {k: contract[k] for k in ("task_id", "required_behavior", "risk")}
    payload["goal"] = contract["goal"] + "\nRequested deliverable: " + contract["deliverable"]
    for key in ("feature_id", "dependencies", "owned_contract_ids", "capabilities"):
        if key in contract:
            payload[key] = contract[key]
    if kind == "investigate":
        if "approved_skills" in contract:
            payload["approved_skills"] = contract["approved_skills"]
        if contract.get("implementation") or scope["modify"] or scope["create"]:
            raise StateError("Investigation cannot grant writes/implementation")
        # ReadonlyHost otherwise synthesizes its own source-evidence criteria.
        # Preserve every task-specific criterion as an explicit model obligation.
        payload["required_behavior"] = [
            *payload["required_behavior"],
            *[
                {"id": "accept-" + item["id"], "text": item["text"]}
                for item in contract["acceptance_criteria"]
            ],
        ]
        payload.update(mode="investigate", read=scope["read"], scope=scope)
        config["experimental_strata_readonly"] = True
    else:
        if contract.get("approved_skills"):
            raise StateError("Approved skills currently qualified only for readonly tasks")
        implementation = contract.get("implementation")
        if not isinstance(implementation, dict) or set(implementation) - IMPLEMENTATION:
            raise StateError("Explicit bounded implementation details required")
        if "web" in contract.get("capabilities", {}):
            raise StateError("Web with writable implementation is not qualified")
        if config.get("experimental_native_tools_trial"):
            raise StateError("Task facade uses qualified core editor, not native edit trial")
        config.pop("experimental_strata_readonly", None)
        payload.update(implementation)
        payload.update(scope=scope, acceptance_criteria=contract["acceptance_criteria"])
    return kind, payload, config
