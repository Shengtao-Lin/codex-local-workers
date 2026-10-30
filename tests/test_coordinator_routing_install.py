"""Installed routing wire/decisions match the frozen experiment, no live calls."""

import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
import coordinator_host_route as FROZEN
from test_installable_bounded import INSTALL, F


@pytest.mark.parametrize(
    "case", ["valid", "correction", "unresolved", "invalid-owner", "unqualified"]
)
def test_installed_wire_and_results_match_frozen_candidate(case):
    data = FROZEN.R.S.read(FROZEN.R.BATCH / "inputs-B.json")
    catalog = FROZEN.R.S.read(FROZEN.R.SOURCE / "catalog.json")
    raw = FROZEN.R.S.read(FROZEN.R.SOURCE / "proposal.json")["proposal"]
    for unit in raw["units"]:
        unit.pop("owner")
    if case == "unresolved":
        raw = {
            "status": "unresolved",
            "units": [],
            "questions": ["Missing contract?"],
            "rationale": "Missing evidence",
        }
    elif case == "invalid-owner":
        raw["units"][0]["owner"] = "local-coder"
    elif case == "unqualified":
        catalog = {}

    class Client:
        def __init__(self):
            self.calls = []
            self.last_request_stats = {}

        def complete(self, messages):
            self.calls.append(copy.deepcopy(messages))
            return (
                "invalid"
                if case == "correction" and len(self.calls) == 1
                else json.dumps(raw)
            )

    with tempfile.TemporaryDirectory(prefix="installed-routing-control-") as directory:
        root = Path(directory)
        INSTALL.install(KIT, root, apply=True)
        assert not (root / "benchmarks").exists()
        module = F.load(
            root / ".local-agents/coordinator-routing.py", "installed_routing_candidate"
        )
        clients, results = [], []
        for selected in (FROZEN, module):
            client = Client()
            binding = selected.bind_catalog(data["brief"], catalog)
            results.append(
                selected.probe(data["brief"], data["context"], client, binding)
            )
            clients.append(client.calls)
        assert results[0] == results[1]
        assert clients[0] == clients[1]
        assert results[1]["dispatch_allowed"] is False
