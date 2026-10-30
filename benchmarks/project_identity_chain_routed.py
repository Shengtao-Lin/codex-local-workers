"""Single explicit chain using the verified route-catalog delivery candidate."""

import argparse
import time
from pathlib import Path

import coordinator_route_evidence as R
import project_identity_chain as J

S, D = J.S, J.D
BATCH = D.I.BASE / "project-identity-chain-20261022-2"


def prepare(used):
    decision = S.read(R.BATCH / "decision.json")
    assert decision["status"] == "PASS_NARROW_ROUTING_EVIDENCE_DELIVERY"
    catalog = S.read(R.SOURCE / "catalog.json")
    original_save = S.save

    def delivered(path, value):
        path = Path(path)
        if path == BATCH / "input.json":
            assert value == S.read(R.SOURCE / "input.json"), "unrelated task drift"
            value["context"]["primary_qualified_routes"] = catalog
        elif path == BATCH / "catalog.json":
            assert value == catalog, "qualification drift"
        elif path == BATCH / "registration.json":
            value["candidate"] = (
                "Existing installed bounded-v1/flat-v1; only Coordinator input adds exact trusted route catalog, supported by the closed four-cell A/B. Same contracts and tests as prior chain. No favorable proposal reused."
            )
            value["prior"] = (
                "project-identity-chain-20261022-1 HOLD/two NOT_RUN unchanged"
            )
            value["pins"].update(
                {
                    str(p): S.sha(p)
                    for p in (
                        Path(__file__),
                        Path(R.__file__),
                        R.BATCH / "decision.json",
                        R.SOURCE / "input.json",
                        R.SOURCE / "catalog.json",
                    )
                }
            )
        original_save(path, value)

    S.save = delivered
    try:
        J.prepare(used)
    finally:
        S.save = original_save


def plan(used):
    J.fresh(used, time.time())
    data = S.read(BATCH / "input.json")
    config = S.read(D.L.SEED / ".agent/config.json")
    client = R.W.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        timeout=360,
        max_tokens=4096,
        temperature=0.1,
        structured_output=False,
        context_length=24576,
    )
    client.reasoning_effort = "low"
    S.save(BATCH / "plan-start.json", {"weekly_used": used, "epoch": time.time()})
    with R.W.MODEL_RESIDENCY.role_model_lease(client, config):
        client.preflight()
        result = R.C.probe(
            data["brief"],
            data["context"],
            R.CaptureClient(client, BATCH / "coordinator"),
            reasoning_strength="low",
        )
    S.save(BATCH / "proposal.json", result)
    print(result["status"], "Primary proposal review required", flush=True)


def close(used, reason):
    original_save = S.save

    def current_history(path, value):
        if Path(path) == BATCH / "handoff.json":
            value["histories"] = (
                "Prior real-package chain HOLD with two NOT_RUN preserved; catalog A/B separately closed. This is a new single conditional chain, not replacement credit."
            )
        original_save(path, value)

    S.save = current_history
    try:
        J.close(used, reason)
    finally:
        S.save = original_save


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=["prepare", "plan", "approve", "execute", "accept", "close"]
    )
    parser.add_argument("--topic", choices=["encode", "append"])
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--reason")
    args = parser.parse_args()
    J.BATCH = BATCH
    J.configure()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    elif args.mode == "plan":
        plan(args.weekly_used)
    elif args.mode == "execute":
        D.execute(args.topic, args.weekly_used, time.time())
    else:
        J.fresh(args.weekly_used, time.time())
        if args.mode == "approve":
            D.approve(args.reason)
        elif args.mode == "accept":
            D.accept(args.topic, args.reason)
        else:
            close(args.weekly_used, args.reason)
