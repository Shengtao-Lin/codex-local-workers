"""Conditional real-package chain: model decomposition, exact host-owned routing."""

import argparse
import time
from pathlib import Path

import coordinator_host_route as H
import coordinator_host_route_trial as TRIAL
import project_identity_chain as J

S, D, R = J.S, J.D, H.R
BATCH = D.I.BASE / "project-identity-chain-20261022-3"


def prepare(used):
    assert (
        S.read(TRIAL.BATCH / "decision.json")["status"]
        == "PASS_NARROW_HOST_ROUTED_DECOMPOSITION"
    )
    catalog = S.read(R.SOURCE / "catalog.json")
    original_save = S.save

    def delivered(path, value):
        path = Path(path)
        if path == BATCH / "input.json":
            assert value == S.read(R.SOURCE / "input.json"), "unrelated task drift"
            value["context"]["primary_qualified_routes"] = catalog
            original_save(
                BATCH / "routing-binding.json", H.bind_catalog(value["brief"], catalog)
            )
        elif path == BATCH / "catalog.json":
            assert value == catalog
        elif path == BATCH / "registration.json":
            value["candidate"] = (
                "Decomposition-only Coordinator omits owner; host matches exact Primary catalog bound to full brief. Same installed Coder/Reviewer, contracts, scope, risk, checks and budgets. Default-off benchmark adapter only. Raw decomposition, matched proposal and routing reasons archived separately."
            )
            value["prior"] = (
                "coordinator-host-route-20261022-1 two reviewed proposals permit this ONE new chain; project-identity-chain-20261022-1/-2 HOLD/NOT_RUN unchanged"
            )
            value["pins"].update(
                {
                    str(p): S.sha(p)
                    for p in (
                        Path(__file__),
                        Path(H.__file__),
                        Path(R.__file__),
                        TRIAL.BATCH / "decision.json",
                        BATCH / "routing-binding.json",
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
        result = H.probe(
            data["brief"],
            data["context"],
            R.CaptureClient(client, BATCH / "coordinator"),
            S.read(BATCH / "routing-binding.json"),
        )
    S.save(BATCH / "proposal.json", result)
    print(
        result["status"],
        "Primary review of raw decomposition and routing required",
        flush=True,
    )


def close(used, reason):
    original_save = S.save

    def current_history(path, value):
        if Path(path) == BATCH / "handoff.json":
            value["histories"] = (
                "Prior two real-package chain HOLDs/four NOT_RUN preserved; qualification-information A/B and decomposition-only gate separate. New conditional chain only; no replacement credit."
            )
            value["routing"] = (
                "Model proposes boundaries/dependencies; host suggests owner via exact Primary-bound catalog. Primary separately approves plan and units; no autonomous dispatch/acceptance."
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
