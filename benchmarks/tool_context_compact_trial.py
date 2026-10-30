"""Counterbalanced proposal-only baseline log compaction, not agent credit."""

import argparse
import xml.etree.ElementTree as ET

import tool_context_proposal as context
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "tool-context-compact-1"
ARMS = ("control-1", "candidate-1", "candidate-2", "control-2")
DRIVERS = (
    "tool_context_compact_trial.py",
    "tool_context_proposal.py",
    "tool_module_proposal.py",
    "tool_context_qualification.py",
)


def compact(baseline, root):
    cases = list(ET.parse(root / ".agent/baseline.xml").getroot().iter("testcase"))
    failures = []
    for case in cases:
        for kind in ("failure", "error", "skipped"):
            element = case.find(kind)
            if element is not None:
                failures.append(
                    {
                        "test": case.get("classname", "") + "::" + case.get("name", ""),
                        "kind": kind,
                        "message": element.get("message", ""),
                    }
                )
    # No failure or error message is truncated; repeated traceback bodies alone
    # are omitted. Original full command output stays immutable on disk.
    return {
        "argv": baseline["argv"],
        "exit": baseline["exit"],
        "seconds": baseline.get("seconds"),
        "tests": len(cases),
        "executed": sum(case.find("skipped") is None for case in cases),
        "observed_nonpasses": failures,
        "full_evidence_sha256": {
            name: digest(root / ".agent" / name)
            for name in ("baseline.json", "baseline.xml")
        },
        "note": "Exact JUnit failure messages; no inferred cause or fix. Full tracebacks archived, not repeated in prompt.",
    }


def configure(arm=None):
    context.BASE, context.ARMS = BASE, ARMS
    context.configure()
    context.proposal.BASELINE_COMPACTOR = (
        compact if arm and arm.startswith("candidate-") else None
    )


def register():
    write(BASE / "preflight.json", read(WORK / "tool-context-scope-1/preflight.json"))
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "weekly_ceiling": 23,
            "axis": "Only original baseline raw traceback repetition vs exact compact JUnit messages/counts/command facts",
            "constants": "Same v10 original source, all 18 protected test sources, hard contracts, model/context/sampling/output budget, no solution example",
            "credit": "Diagnostic proposal only; no agent, Reviewer, Coordinator, acceptance or causal efficiency credit",
            "drivers": {name: digest(KIT / "benchmarks" / name) for name in DRIVERS},
        },
    )


def run(arm):
    configure(arm)
    verify_hashes(KIT / "benchmarks", read(BASE / "registration.json")["drivers"])
    context.proposal.propose(arm)


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
            "prepare": context.prepare,
            "propose": run,
            "apply-reviewed": context.proposal.apply_reviewed,
        }[args.action](args.arm)
