"""Primary packet preparation errors must not consume model correction turns."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "preflight_routing_fixture", KIT / ".local-agents/tests/test_coordinator_routing.py"
)
FIXTURE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FIXTURE
SPEC.loader.exec_module(FIXTURE)
H = FIXTURE.H


@pytest.mark.parametrize(
    "corruption",
    [
        "missing-catalog",
        "extra-contract",
        "empty-criteria",
        "bad-observables",
        "missing-tests",
        "missing-profile",
        "unprotected-tests",
        "bad-order-type",
    ],
)
def test_invalid_primary_recipe_stops_before_model(corruption):
    brief, context, catalog, raw = FIXTURE.data.__wrapped__()
    entry = brief["acceptance_catalog"]["encode"]
    if corruption == "missing-catalog":
        del brief["acceptance_catalog"]
    elif corruption == "extra-contract":
        brief["acceptance_catalog"]["unknown"] = entry
    elif corruption == "empty-criteria":
        entry["acceptance_criteria"] = []
    elif corruption == "bad-observables":
        entry["acceptance_scenarios"][0]["observables"] = {}
    elif corruption == "missing-tests":
        del entry["required_focused_tests"]
    elif corruption == "missing-profile":
        del brief["validation_profile"]
    elif corruption == "unprotected-tests":
        entry["required_focused_tests"] = ["tests/unprotected.py"]
    else:
        entry["required_order"] = "not-an-array"

    class Client:
        def __init__(self):
            self.calls = 0
            self.last_request_stats = {}

        def complete(self, messages):
            self.calls += 1
            return json.dumps(raw)

    client = Client()
    blocked = False
    try:
        binding = H.bind_catalog(brief, catalog)
        H.probe(brief, context, client, binding)
    except (ValueError, TypeError, KeyError):
        blocked = True
    assert client.calls == 0, "Primary input defect was sent to model protocol recovery"
    assert blocked, "Malformed Primary obligations were not rejected"
