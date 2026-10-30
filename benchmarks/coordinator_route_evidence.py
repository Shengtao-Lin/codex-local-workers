"""Matched Coordinator-only experiment: deliver existing qualified route facts."""

import argparse
import copy
import json
import time
from pathlib import Path

import bounded_dependency_smoke as D

S, C, W = D.S, D.P.C, D.P.W
SOURCE = D.I.BASE / "project-identity-chain-20261022-1"
BATCH = D.I.BASE / "coordinator-route-evidence-20261022-1"
ORDER = ["B1", "A1", "A2", "B2"]


class CaptureClient:
    def __init__(self, client, root):
        self.client, self.root, self.calls = client, root, 0
        self.last_request_stats = None

    def complete(self, messages):
        self.calls += 1
        assert self.calls <= 2
        S.save(self.root / f"request-{self.calls}.json", messages)
        try:
            raw = self.client.complete(messages)
        except Exception as exc:
            S.save(
                self.root / f"error-{self.calls}.json",
                {"type": type(exc).__name__, "message": str(exc)},
            )
            raise
        self.last_request_stats = copy.deepcopy(self.client.last_request_stats)
        S.save(
            self.root / f"response-{self.calls}.json",
            {"raw": raw, "stats": self.last_request_stats},
        )
        return raw


def prepare(used):
    assert not BATCH.exists()
    original = S.read(SOURCE / "input.json")
    catalog = S.read(SOURCE / "catalog.json")
    old = S.read(SOURCE / "proposal.json")
    assert old["status"] == "proposal_valid"
    assert all(u["owner"] == "primary" for u in old["proposal"]["units"])
    # Qualify from exact completed evidence, never from model self-classification.
    first = S.read(D.I.BASE / "project-live-20261022-2/decision.json")
    second = S.read(D.I.BASE / "project-callers-20261022-2/metrics.json")
    assert first["accepted"] == 2 and all(
        second["cells"][f"hash-{i}"]["accepted"] for i in (1, 2)
    )
    augmented = copy.deepcopy(original)
    augmented["context"]["primary_qualified_routes"] = catalog
    assert {
        k: v for k, v in augmented["context"].items() if k != "primary_qualified_routes"
    } == original["context"]
    assert augmented["brief"] == original["brief"]
    S.save(BATCH / "inputs-A.json", original)
    S.save(BATCH / "inputs-B.json", augmented)
    for arm, value in (("A", original), ("B", augmented)):

        class Offline:
            def __init__(self):
                self.last_request_stats = {}

            def complete(self, messages):
                self.messages = copy.deepcopy(messages)
                return json.dumps(old["proposal"])

        client = Offline()
        result = C.probe(
            value["brief"], value["context"], client, reasoning_strength="low"
        )
        assert (
            result["status"] == "proposal_valid" and result["dispatch_allowed"] is False
        )
        delivered = json.loads(client.messages[1]["content"])
        assert delivered["read_only_context"] == value["context"]
        assert ("primary_qualified_routes" in delivered["read_only_context"]) == (
            arm == "B"
        )
        S.save(
            BATCH / ("offline-" + arm + ".json"),
            {"model_calls": 0, "delivered": client.messages, "result": result},
        )
    paths = [
        Path(__file__),
        SOURCE / "input.json",
        SOURCE / "catalog.json",
        SOURCE / "proposal.json",
        BATCH / "inputs-A.json",
        BATCH / "inputs-B.json",
        D.I.BASE / "project-live-20261022-2/decision.json",
        D.I.BASE / "project-callers-20261022-2/metrics.json",
        *list((S.KIT / ".local-agents").rglob("*.py")),
    ]
    S.save(
        BATCH / "registration.json",
        {
            "registered": 4,
            "order": ORDER,
            "weekly_used_start": used,
            "weekly_limit": None,
            "candidate": "B delivers the exact already-existing trusted Primary route catalog as read-only context. A identical old input. No instruction/policy/runtime/model/schema/risk/contract/test change.",
            "hypothesis": "Prior correct decomposition chose Primary because per-contract qualification facts were not delivered; causal status unproven until paired observation",
            "model": "Same meta/muse-glimmer Q4_K_M,24576,low,temperature0.1,4096 output,360s request; max2 requests for syntax correction only; one resident; fixed one known brief",
            "gate": "B2/2 scoped, correct dependency/risk/contracts with both owner=local-coder; primary review of each proposal still required. Show A outcomes separately. An owner=primary is conservative legal routing, not coding failure. No Coder/Reviewer calls or automatic dispatch in this experiment.",
            "continuation": "Complete ordinary outcomes, including Primary routing, unresolved or protocol failure, in fixed order. Infrastructure/safety/drift/batch3600s/user stop halts, no reroll or new cells.",
            "cost": "Primary catalog supplied from independently verified existing evidence; no algorithm/source fix. Active time/cloud tokens unknown. A/B measures routing only, not final implementation, broad planning or savings.",
            "pins": {str(p): S.sha(p) for p in paths if "__pycache__" not in p.parts},
        },
    )
    print("4 Coordinator-only matched cells frozen; no model calls", flush=True)


def run(cell, used):
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    for previous in ORDER[: ORDER.index(cell)]:
        assert (
            S.read(BATCH / previous / "result.json")["infrastructure_failure"] is False
        )
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    assert time.time() - S.read(clock)["epoch"] < 3600
    root = BATCH / cell
    S.save(root / "start.json", {"weekly_used_observed": used, "epoch": time.time()})
    data = S.read(BATCH / ("inputs-" + cell[0] + ".json"))
    config = S.read(D.L.SEED / ".agent/config.json")
    client = W.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        timeout=360,
        max_tokens=4096,
        temperature=0.1,
        structured_output=False,
        context_length=24576,
    )
    client.reasoning_effort = "low"
    started = time.monotonic()
    try:
        with W.MODEL_RESIDENCY.role_model_lease(client, config):
            client.preflight()
            result = C.probe(
                data["brief"],
                data["context"],
                CaptureClient(client, root),
                reasoning_strength="low",
            )
    except Exception as exc:
        S.save(
            root / "result.json",
            {
                "infrastructure_failure": True,
                "error": str(exc),
                "type": type(exc).__name__,
                "seconds": time.monotonic() - started,
            },
        )
        raise
    S.save(root / "proposal.json", result)
    units = (result.get("untrusted_plan") or {}).get("units", [])
    local = (
        bool(units)
        and len(units) == 2
        and all(u["owner"] == "local-coder" for u in units)
    )
    S.save(
        root / "result.json",
        {
            "infrastructure_failure": False,
            "status": result["status"],
            "unit_owners": [u["owner"] for u in units],
            "both_local": local,
            "requests": len(result["attempts"]),
            "seconds": time.monotonic() - started,
            "Primary_semantic_review": "PENDING",
            "dispatch_allowed": False,
        },
    )
    print(cell, result["status"], [u["owner"] for u in units], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        run(args.cell, args.weekly_used)
