"""Matched contract-position diagnostic with all content unchanged."""

import argparse

import tool_context_compact_trial as compact_trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "tool-context-salience-1"
ARMS = ("control-1", "candidate-1", "candidate-2", "control-2")
DRIVERS = (*compact_trial.DRIVERS, "tool_context_salience_trial.py")


def contract_last(payload):
    return {
        **{k: v for k, v in payload.items() if k != "packet"},
        "packet": payload["packet"],
    }


def configure(arm=None):
    compact_trial.BASE, compact_trial.ARMS = BASE, ARMS
    compact_trial.configure(arm)
    module = compact_trial.context.proposal
    module.BASELINE_COMPACTOR = compact_trial.compact
    module.PAYLOAD_TRANSFORM = (
        contract_last if arm and arm.startswith("candidate-") else None
    )


def register():
    write(BASE / "preflight.json", read(WORK / "tool-context-scope-1/preflight.json"))
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "weekly_ceiling": 23,
            "axis": "Only move unchanged packet to final payload section, after source/tests; all arms use same compact baseline",
            "constants": "All original v10 source/test/config/packet values, same model/context/sampling/output, no recipe or model answer",
            "credit": "Proposal diagnostic, not Coder agent, E/R/Coordinator, acceptance or savings",
            "drivers": {name: digest(KIT / "benchmarks" / name) for name in DRIVERS},
        },
    )


def run(arm):
    configure(arm)
    verify_hashes(KIT / "benchmarks", read(BASE / "registration.json")["drivers"])
    compact_trial.context.proposal.propose(arm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action", choices=("register", "prepare", "propose", "apply-reviewed")
    )
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    configure(args.arm)
    if args.action == "register":
        register()
    else:
        {
            "prepare": compact_trial.context.prepare,
            "propose": run,
            "apply-reviewed": compact_trial.context.proposal.apply_reviewed,
        }[args.action](args.arm)
