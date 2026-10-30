"""Portable no-model controls for explicit Primary-owned routing."""

import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


H = load("routing_test_module", Path(__file__).resolve().parents[1] / "coordinator-routing.py")
BASE = load("routing_test_brief_example", Path(__file__).with_name("test_coordinator_brief.py"))


@pytest.fixture
def data():
    brief, raw = BASE.example()
    previous = brief["acceptance_catalog"]
    brief["acceptance_catalog"] = {"encode": previous["producer"], "append": previous["consumer"]}
    brief["feature_risk"] = brief["integration_risk"] = "high"
    brief["contract_edges"] = [["encode", "append"]]
    catalog = {}
    for index, key in enumerate(("encode", "append")):
        unit = raw["units"][index]
        unit.pop("owner")
        unit.update(
            id=key, contracts=[key], risk="high", dependencies=["encode"] if key == "append" else []
        )
        path = unit["modify"][0]
        ref = {"path": path, "symbol": key + "_value"}
        brief["contracts"][index].update(id=key, risk_floor="high", implementation_ref=ref)
        brief["source_hashes"][path] = "a" * 64
        catalog[key] = {"family": H.FAMILY, **ref, "qualification_evidence": "Offline control only"}
    return brief, {}, catalog, raw


def test_exact_qualification_routes_without_altering_contract_or_risk(data):
    brief, _, catalog, raw = data
    original = copy.deepcopy((brief, raw, catalog))
    proposal, plan, routes = H.materialize(brief, raw, H.bind_catalog(brief, catalog))
    assert all(u["owner"] == "local-coder" and u["risk"] == "high" for u in proposal["units"])
    assert plan["contracts"] == brief["contracts"]
    assert all(r["dispatch_allowed"] is False for r in routes)
    assert (brief, raw, catalog) == original


@pytest.mark.parametrize("mutation", ["contract", "risk", "scope", "tests", "source"])
def test_stale_primary_binding_fails_closed(data, mutation):
    brief, _, catalog, raw = data
    binding = H.bind_catalog(brief, catalog)
    if mutation == "contract":
        brief["contracts"][0]["text"] += " changed"
    elif mutation == "risk":
        brief["integration_risk"] = "medium"
    elif mutation == "scope":
        brief["authority"]["modify"].append("src/extra.py")
    elif mutation == "tests":
        brief["acceptance_catalog"]["encode"]["acceptance_criteria"][0]["text"] += " changed"
    else:
        path = next(iter(brief["source_hashes"]))
        assert brief["source_hashes"][path] != "b" * 64
        brief["source_hashes"][path] = "b" * 64
    with pytest.raises(ValueError, match="stale"):
        H.materialize(brief, raw, binding)


@pytest.mark.parametrize(
    "field,value",
    [
        ("family", "unqualified"),
        ("path", "src/else.py"),
        ("symbol", "elsewhere"),
        ("qualification_evidence", ""),
    ],
)
def test_bad_catalog_cannot_supply_permission(data, field, value):
    brief, _, catalog, _ = data
    catalog["encode"][field] = value
    with pytest.raises(ValueError, match="Unbound"):
        H.bind_catalog(brief, catalog)


def test_missing_route_keeps_unit_primary(data):
    brief, _, catalog, raw = data
    del catalog["append"]
    proposal, _, _ = H.materialize(brief, raw, H.bind_catalog(brief, catalog))
    assert [u["owner"] for u in proposal["units"]] == ["local-coder", "primary"]


def test_ordering_unit_not_qualified(data):
    brief, _, catalog, raw = data
    brief["acceptance_catalog"]["encode"]["required_order"] = ["observe before mutation"]
    proposal, _, _ = H.materialize(brief, raw, H.bind_catalog(brief, catalog))
    assert proposal["units"][0]["owner"] == "primary"


@pytest.mark.parametrize("kind", ["owner", "risk", "scope", "edge", "contract", "create"])
def test_invalid_or_model_authored_authority_not_repaired_silently(data, kind):
    brief, _, catalog, raw = data
    binding = H.bind_catalog(brief, catalog)
    if kind == "owner":
        raw["units"][0]["owner"] = "local-coder"
    elif kind == "risk":
        raw["units"][0]["risk"] = "small"
    elif kind == "scope":
        raw["units"][0]["modify"] = ["tests/test_encode.py"]
    elif kind == "edge":
        raw["units"][1]["dependencies"] = []
    elif kind == "contract":
        raw["units"][0]["contracts"] = ["unknown"]
    else:
        raw["units"][0]["create"] = ["src/new.py"]
    with pytest.raises(ValueError):
        H.materialize(brief, raw, binding)


def test_unresolved_never_becomes_executable(data):
    brief, _, catalog, _ = data
    raw = {
        "status": "unresolved",
        "units": [],
        "questions": ["Which caller contract?"],
        "rationale": "Missing evidence",
    }
    proposal, plan, routes = H.materialize(brief, raw, H.bind_catalog(brief, catalog))
    assert proposal == raw and plan is None and routes == []


def test_real_wire_no_owner_and_bounded_protocol_recovery(data):
    brief, context, catalog, raw = data

    class Client:
        def __init__(self):
            self.last_request_stats = {}
            self.calls = []

        def complete(self, messages):
            self.calls.append(copy.deepcopy(messages))
            return "invalid" if len(self.calls) == 1 else json.dumps(raw)

    client = Client()
    result = H.probe(brief, context, client, H.bind_catalog(brief, catalog))
    assert len(result["attempts"]) == 2 and result["dispatch_allowed"] is False
    assert result["semantic_primary_review_required"] is True
    assert "owner (primary/local-coder)" not in client.calls[0][0]["content"]
    assert json.loads(client.calls[0][1]["content"])["read_only_context"] == context
    assert "packet_contract" not in result["decomposition"]["units"][0]


def test_multiple_functions_are_not_granted_single_function_qualification(data):
    brief, _, catalog, raw = data
    combined = copy.deepcopy(raw["units"][0])
    combined["contracts"] = ["encode", "append"]
    combined["modify"] += raw["units"][1]["modify"]
    brief["contract_edges"] = []
    raw["units"] = [combined]
    proposal, _, routes = H.materialize(brief, raw, H.bind_catalog(brief, catalog))
    assert proposal["units"][0]["owner"] == "primary"
    assert routes[0]["reason"] == "unsupported_or_unqualified_unit"


def test_model_context_cannot_replace_trusted_primary_binding(data):
    brief, context, catalog, raw = data
    context["primary_qualified_routes"] = catalog

    class Client:
        def __init__(self):
            self.last_request_stats = {}

        def complete(self, messages):
            return json.dumps(raw)

    result = H.probe(brief, context, Client(), H.bind_catalog(brief, {}))
    assert all(u["owner"] == "primary" for u in result["proposal"]["units"])


def test_protocol_recovery_stops_after_two_requests(data):
    brief, context, catalog, _ = data

    class Client:
        def __init__(self):
            self.last_request_stats = {}
            self.calls = 0

        def complete(self, messages):
            self.calls += 1
            return "not-json"

    client = Client()
    result = H.probe(brief, context, client, H.bind_catalog(brief, catalog))
    assert client.calls == 2 and result["status"] == "proposal_failed"
    assert result["dispatch_allowed"] is False
