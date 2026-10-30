"""Same new contract in a non-executing whole-module diagnostic, not agent credit."""

import argparse

import tool_context_qualification as qualification
import tool_module_proposal as proposal
from capability_fit import WORK, write
from inherited_context_recovery import read

BASE = WORK / "tool-context-proposal-1"
ARMS = ("proposal-1", "proposal-2")


def configure():
    qualification.BASE = BASE
    qualification.configure()
    qualification.scope.ARMS = ARMS
    qualification.scope.configure()
    proposal.BASE, proposal.SNAPSHOT, proposal.ARMS = (
        BASE,
        qualification.scope.SNAPSHOT,
        ARMS,
    )
    proposal.trial.FROZEN = qualification.FROZEN


def register():
    write(BASE / "preflight.json", read(WORK / "tool-context-scope-1/preflight.json"))
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "weekly_ceiling": 23,
            "model": "Same Qwen/context/sampling/output budget; single residency",
            "contract": "Same 18 protected tests and context/loop/invocation requirements as fresh agent cohort",
            "diagnostic": "One complete-module proposal with source/tests presented together, no editing tool loop",
            "credit": "No Coder agent, Reviewer, Explorer, Coordinator, stable-release or savings credit",
            "safety": "No execution during proposal. Exact hash-bound Primary source/diff review before isolated application and independent checks",
        },
    )


def prepare(arm):
    configure()
    qualification.prepare(arm)
    root = BASE / arm
    # The one-shot diagnostic reads these original names; keep actual packet/config
    # separately before replacing unused preparation convenience pointers.
    import shutil

    shutil.copyfile(root / ".agent/context-packet.json", root / ".agent/packet.json")
    shutil.copyfile(root / ".agent/context-config.json", root / ".agent/config.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action", choices=("register", "prepare", "propose", "apply-reviewed")
    )
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        {
            "prepare": prepare,
            "propose": proposal.propose,
            "apply-reviewed": proposal.apply_reviewed,
        }[args.action](args.arm)
