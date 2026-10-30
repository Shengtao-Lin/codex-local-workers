"""Default-off experiment: untrusted decomposition, Primary-bound executor routing.

No runtime defaults, dispatch or approval. Reuse the installed brief validator and
wire template; only executor choice leaves the model's output schema.
"""

import copy
import json

import coordinator_route_evidence as R

C = R.C
FAMILY = R.D.BRIDGE.FAMILY
FIELDS = {"id", "goal", "risk", "contracts", "dependencies", "modify", "create"}
OWNER_WIRE = "owner (primary/local-coder), "


def bind_catalog(brief, catalog):
    """Trusted Primary preparation only; never accept a model-authored catalog."""
    C.validate_brief(brief)
    if not isinstance(catalog, dict):
        raise TypeError("Primary catalog must be an object")
    contracts = {c["id"]: c for c in brief["contracts"]}
    for key, entry in catalog.items():
        contract = contracts.get(key)
        if (
            not isinstance(entry, dict)
            or set(entry) != {"family", "path", "symbol", "qualification_evidence"}
            or contract is None
            or entry.get("family") != FAMILY
            or contract.get("implementation_ref")
            != {"path": entry.get("path"), "symbol": entry.get("symbol")}
            or not isinstance(entry.get("symbol"), str)
            or not entry["symbol"].isidentifier()
            or entry.get("path") not in brief["authority"]["modify"]
            or entry.get("path") not in brief["source_hashes"]
            or not isinstance(entry.get("qualification_evidence"), str)
            or not entry["qualification_evidence"].strip()
        ):
            raise ValueError("Unbound or unqualified catalog entry")
    return {"brief_sha256": C.digest(brief), "routes": copy.deepcopy(catalog)}


def materialize(brief, raw, binding):
    if (
        not isinstance(binding, dict)
        or set(binding) != {"brief_sha256", "routes"}
        or binding["brief_sha256"] != C.digest(brief)
        or bind_catalog(brief, binding["routes"]) != binding
    ):
        raise ValueError("Primary routing binding stale")
    proposal = copy.deepcopy(raw)
    if not isinstance(proposal, dict) or not isinstance(proposal.get("units"), list):
        raise TypeError("Proposal object with units array required")
    for unit in proposal["units"]:
        if not isinstance(unit, dict) or set(unit) != FIELDS:
            raise ValueError("Decomposition fields: " + ", ".join(sorted(FIELDS)))
        unit["owner"] = "primary"
    # Reject unsafe/malformed decompositions before any route is suggested.
    C.proposal_plan(brief, proposal)
    rows = []
    for unit in proposal["units"]:
        entries = [binding["routes"].get(k) for k in unit["contracts"]]
        supported = (
            len(unit["modify"]) == 1
            and not unit["create"]
            and all(entry is not None for entry in entries)
            and len({(e["path"], e["symbol"]) for e in entries if e}) == 1
            and all(e["path"] == unit["modify"][0] for e in entries if e)
            and all(
                not brief["acceptance_catalog"][k][field]
                for k in unit["contracts"]
                for field in ("required_order", "forbidden_orderings")
            )
        )
        unit["owner"] = "local-coder" if supported else "primary"
        rows.append(
            {
                "proposal_id": unit["id"],
                "owner": unit["owner"],
                "reason": "exact_primary_qualified_route"
                if supported
                else "unsupported_or_unqualified_unit",
                "dispatch_allowed": False,
            }
        )
    plan = C.proposal_plan(brief, proposal)
    return proposal, plan, rows


def messages_for(brief, context, reasoning_strength):
    class Template:
        def __init__(self):
            self.last_request_stats = {}

        def complete(self, messages):
            self.messages = copy.deepcopy(messages)
            return json.dumps(
                {
                    "status": "unresolved",
                    "units": [],
                    "questions": ["Template extraction only"],
                    "rationale": "Offline; not a model result",
                }
            )

    template = Template()
    C.probe(brief, context, template, reasoning_strength=reasoning_strength)
    messages = template.messages
    assert messages[0]["content"].count(OWNER_WIRE) == 1
    messages[0]["content"] = messages[0]["content"].replace(OWNER_WIRE, "")
    messages[0]["content"] += (
        "\nDo not choose an executor or emit owner. The host suggests execution routing "
        "from the Primary-approved capability catalog after validating your decomposition."
    )
    return messages


def probe(brief, context, client, binding, *, reasoning_strength="low"):
    # Validate authority before sending any model request.
    materialize(
        brief,
        {
            "status": "unresolved",
            "units": [],
            "questions": ["Preflight only"],
            "rationale": "No dispatch",
        },
        binding,
    )
    messages = messages_for(brief, context, reasoning_strength)
    attempts = []
    for index in range(2):
        raw = client.complete(messages)
        try:
            decomposition = json.loads(raw)
            proposal, plan, routes = materialize(brief, decomposition, binding)
        except (ValueError, TypeError, KeyError) as exc:
            attempts.append(
                {
                    "raw_response": raw,
                    "error": str(exc),
                    "protocol_valid": False,
                    "request": copy.deepcopy(client.last_request_stats),
                }
            )
            if index == 0:
                messages.extend(
                    [
                        {"role": "assistant", "content": raw},
                        {
                            "role": "user",
                            "content": "One bounded protocol correction: " + str(exc),
                        },
                    ]
                )
            continue
        attempts.append(
            {
                "response": decomposition,
                "protocol_valid": True,
                "request": copy.deepcopy(client.last_request_stats),
            }
        )
        return {
            "status": "proposal_valid",
            "decomposition": decomposition,
            "proposal": proposal,
            "untrusted_plan": plan,
            "routing": routes,
            "routing_binding_sha256": C.digest(binding),
            "attempts": attempts,
            "dispatch_allowed": False,
            "semantic_primary_review_required": True,
        }
    return {
        "status": "proposal_failed",
        "attempts": attempts,
        "dispatch_allowed": False,
    }
