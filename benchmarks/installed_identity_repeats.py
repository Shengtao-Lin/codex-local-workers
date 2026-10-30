"""Fixed two-chain repetition of installed host routing, not new-task credit."""

import argparse
import copy
import time
from pathlib import Path

import project_identity_chain_complete as Q

S, D = Q.S, Q.D
PARENT = D.I.BASE / "installed-identity-repeats-20261022-1"


def register(used):
    assert not PARENT.exists()
    install = D.I.BASE / "coordinator-routing-install-20261022-2/decision.json"
    assert S.read(install)["status"] == "PASS_EXPLICIT_ROUTING_INSTALL"
    S.save(
        PARENT / "registration.json",
        {
            "registered": {"chains": 2, "units": 4},
            "order": [1, 2],
            "candidate": "Exact installed coordinator-routing API; same known real-package contracts and bounded-v1/flat-v1 Coder/fresh Reviewer. Complete project parity/copier fix. Unique per-invocation archive identities; no model/default/scope/budget/semantic changes.",
            "gate": "2/2 full chains: reviewed Coordinator decomposition and Primary-bound routes; both units independently accepted per chain; exact producer transfer;169 final non-DB project/private/roundtrip tests plus strict checks; no protected drift, assistance, rescue or resampling",
            "continue": "One ordinary proposal/worker/review failure makes final HOLD; dependent units NOT_RUN; still finish next independent registered chain. Infrastructure/drift/safety/time/user stop halts remaining cells. No extra repeats or favorable Reviewer selection.",
            "budget": "Per chain Coordinator max2protocol requests360s, Coder12requests/3edits/3postchecks900s per unit, fresh Reviewer16requests600s per unit, unit2220s, chain7200s, batch14400s; one resident; exact existing models/config",
            "exposure": "Exact already-exposed accepted contracts; replication and installation stability only, not holdout/new-family qualification",
            "Primary_cost": "Reuse frozen contracts, reference, tests, paths, classification/edge. Review every raw proposal and complete changed files plus current canonical facts. Active time/cloud tokens unknown, no savings inference.",
            "weekly_used_start": used,
            "weekly_limit": None,
            "pins": {
                str(p): S.sha(p)
                for p in (
                    Path(__file__),
                    install,
                    S.KIT / ".local-agents/coordinator-routing.py",
                    Path(Q.__file__),
                    Path(Q.SNAP.__file__),
                )
            },
        },
    )
    print("Two installed same-contract chains registered, no live calls", flush=True)


def configure(index, mode):
    reg = S.read(PARENT / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    if index == 2:
        previous = S.read(PARENT / "chain-1/decision.json")
        if previous.get("accepted_chains") != 1:
            disposition = S.read(PARENT / "chain-1/batch-continuation.json")
            assert disposition.get("classification") == "ordinary_model_outcome"
            assert disposition.get("continue_independent_chain") is True
    clock = PARENT / "start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    assert time.time() - S.read(clock)["epoch"] < 14400
    Q.BATCH = PARENT / ("chain-" + str(index))
    Q.configure()
    original_save = S.save

    def registered(path, value):
        if Path(path) == Q.BATCH / "registration.json":
            value["repetition"] = (
                "Fixed installed candidate repeat "
                + str(index)
                + "/2; known task; parent continuation/gate applies"
            )
            value["pins"][str(Path(__file__))] = S.sha(__file__)
            value["pins"][str(PARENT / "registration.json")] = S.sha(
                PARENT / "registration.json"
            )
        original_save(path, value)

    S.save = registered
    original_materialize = D.BRIDGE.CONTRACT.materialize_bounded_packet

    def identity(plan, proposal):
        proposal = copy.deepcopy(proposal)
        scope = "offline" if mode == "prepare" else "live"
        proposal["run_id"] = f"repeat-20261022-{index}-{scope}-" + proposal["run_id"]
        return original_materialize(plan, proposal)

    D.BRIDGE.CONTRACT.materialize_bounded_packet = identity
    if mode == "plan":
        installed = (
            Q.BATCH / "offline/encode/isolated/.local-agents/coordinator-routing.py"
        )
        assert S.sha(installed) == S.sha(S.KIT / ".local-agents/coordinator-routing.py")
        Q.H.H = D.F.load(installed, "repeat_installed_routing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=[
            "register",
            "prepare",
            "plan",
            "approve",
            "execute",
            "accept",
            "close",
        ],
    )
    parser.add_argument("--chain", type=int, choices=[1, 2], default=1)
    parser.add_argument("--topic", choices=["encode", "append"])
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.mode == "register":
        register(args.weekly_used)
    else:
        configure(args.chain, args.mode)
        if args.mode == "prepare":
            Q.H.prepare(args.weekly_used)
        elif args.mode == "plan":
            Q.H.plan(args.weekly_used)
        elif args.mode == "execute":
            D.execute(args.topic, args.weekly_used, time.time())
        else:
            Q.J.fresh(args.weekly_used, time.time())
            if args.mode == "approve":
                D.approve(args.reason)
            elif args.mode == "accept":
                D.accept(args.topic, args.reason)
            else:
                Q.H.close(args.weekly_used, args.reason)
